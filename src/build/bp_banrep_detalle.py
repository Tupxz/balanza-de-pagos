"""
ETL: Balanza de pagos de Colombia (BanRep) - máximo nivel de detalle.

Lee  data/raw/banrep/2_Balanza_de_pagos_Maximo_nivel_de_detalle.csv  y
reconstruye la jerarquía de partidas a partir de la sangría del nombre (la
columna "Cuentas" viene indentada con espacios / NBSP).

Salidas (data/interm/):
  - bp_banrep_arbol.csv : una fila por partida (Orden) con código, nombre,
    padre, cuenta, lado y marcas de memorando.
  - bp_banrep_long.csv  : datos en formato largo (Orden, periodo, valor).
  - bp_banrep_hojas.csv : partidas de máximo nivel de detalle (últimos 12
    trimestres), solo para inspección.

Cómo se lee el árbol
  * "Crédito / Débito" son los LADOS de una partida de cuenta corriente (no
    sub-partidas): neto = crédito - débito.
  * "Adquisición neta de activos / Pasivos netos incurridos" son los lados de
    una partida de cuenta financiera: neto = activos - pasivos.
  * Memorandos que se excluyen siempre (son subconjuntos, duplicarían):
    "De las cuales...", "Partida informativa" (códigos ...M), "Memorándum",
    "Autoridades monetarias (según corresponda)".
  * Desgloses alternativos: códigos con segmento ".0." (p. ej. viajes por
    producto, corto/largo plazo de "Otros sectores").
  * Desglose neto duplicado: si una partida se abre en activos/pasivos, sus
    sub-partidas directas sin lado (p. ej. 3.3 por sector) se descartan.

Selección de hojas (``seleccionar_hojas``), guiada por los datos
  Para cada partida se baja un nivel solo si sus componentes SUMAN el valor
  del padre en los periodos analizados; se prueba primero el desglose
  principal, luego principal + alternativo y luego solo el alternativo
  (BanRep a veces codifica el corto plazo como ".0.1"). Si nada cuadra (o
  BanRep solo publica el agregado), el padre es la hoja. Así las hojas
  siempre suman el total de la cuenta.

Uso:
    python src/build/bp_banrep_detalle.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "banrep" / "2_Balanza_de_pagos_Maximo_nivel_de_detalle.csv"
INTERM = ROOT / "data" / "interm"

CUENTAS = {"1": "Cuenta corriente", "2": "Cuenta de capital", "3": "Cuenta financiera"}

RE_CODIGO = re.compile(r"^(\d+(?:\.[0-9A-Za-z]+)*)\s+(.*)$")
LADOS = [
    ("credito", re.compile(r"^Cr[eé]dito", re.I)),
    ("debito", re.compile(r"^D[eé]bito", re.I)),
    ("activos", re.compile(r"^Adquisici[oó]n neta de activos", re.I)),
    ("pasivos", re.compile(r"^Pasivos netos incurridos", re.I)),
]
RE_MEMO = re.compile(
    r"de (las|los|la) cual|partida informativa|memor[aá]ndum|"
    r"autoridades monetarias \(seg[uú]n corresponda\)",
    re.I,
)


# ----------------------------------------------------------------------------
# Lectura
# ----------------------------------------------------------------------------
def _a_numero(s: pd.Series) -> pd.Series:
    """'1234,56' (coma decimal) -> float."""
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def leer_raw(ruta: Path = RAW) -> pd.DataFrame:
    return pd.read_csv(ruta, encoding="utf-8-sig", dtype={"Valor": str})


def cargar_largo(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"Fecha (Año)": "anio", "Trimestre": "trimestre",
                             "Estados de la informacion": "estado"}).copy()
    out["valor"] = _a_numero(out["Valor"])
    out["q"] = out["trimestre"].str[1].astype(int)
    out["periodo"] = out["anio"].astype(str) + "Q" + out["q"].astype(str)
    return out[["Orden", "anio", "q", "periodo", "estado", "valor"]]


def a_ancho(largo: pd.DataFrame) -> pd.DataFrame:
    """Orden x periodo."""
    return largo.pivot(index="Orden", columns="periodo", values="valor").sort_index(axis=1)


# ----------------------------------------------------------------------------
# Árbol
# ----------------------------------------------------------------------------
def _hijos(arbol: pd.DataFrame) -> dict[int, list[int]]:
    hijos: dict[int, list[int]] = {}
    for orden, padre in arbol["padre"].dropna().astype(int).items():
        hijos.setdefault(padre, []).append(orden)
    return hijos


def _lados_hijos(o: int, arbol: pd.DataFrame, hijos: dict[int, list[int]]) -> set[str]:
    return {arbol.at[h, "lado"] for h in hijos.get(o, []) if arbol.at[h, "tipo"] == "lado"}


def construir_arbol(df: pd.DataFrame) -> pd.DataFrame:
    filas = df.drop_duplicates("Orden").sort_values("Orden")[["Orden", "Cuentas"]]
    regs: list[dict] = []
    pila: list[tuple[int, int]] = []  # (sangría, posición en regs)
    for orden, texto in filas.itertuples(index=False):
        sangria = len(texto) - len(texto.lstrip())
        nombre = texto.strip()
        m = RE_CODIGO.match(nombre)
        codigo, desc = (m.group(1), m.group(2)) if m else (None, nombre)

        while pila and pila[-1][0] >= sangria:
            pila.pop()
        padre = regs[pila[-1][1]] if pila else None

        tipo, lado = "partida", (padre["lado"] if padre else None)
        for nom_lado, rx in LADOS:
            if rx.match(nombre):
                tipo, lado = "lado", nom_lado
                break

        if codigo:
            cuenta = codigo.split(".")[0]
        elif nombre.startswith("Errores"):
            cuenta = "EO"
        else:
            cuenta = padre["cuenta"] if padre else None

        regs.append(dict(
            Orden=int(orden), codigo=codigo, nombre=desc, sangria=sangria,
            padre=padre["Orden"] if padre else None, tipo=tipo, lado=lado,
            memo=bool(RE_MEMO.search(nombre)) or bool(codigo and codigo.split(".")[-1].endswith("M")),
            alternativo=bool(codigo and "0" in codigo.split(".")[1:]),
            cuenta=cuenta,
        ))
        # Crédito/Débito son atributos de su partida: nunca son padres.
        if lado not in ("credito", "debito") or tipo == "partida":
            pila.append((sangria, len(regs) - 1))

    arbol = pd.DataFrame(regs).set_index("Orden", drop=False)
    hijos = _hijos(arbol)
    movidos_de: set[int] = set()

    # 3.4: los instrumentos 3.4.x quedan sangrados bajo "Pasivos netos" del
    # total, pero cada uno tiene sus propios lados -> re-colgar del abuelo.
    for o in arbol.index:
        p = arbol.at[o, "padre"]
        if (arbol.at[o, "tipo"] == "partida" and pd.notna(p)
                and arbol.at[int(p), "tipo"] == "lado"
                and _lados_hijos(o, arbol, hijos) & {"activos", "pasivos"}):
            arbol.at[o, "padre"] = arbol.at[int(p), "padre"]
            arbol.at[o, "lado"] = None
            movidos_de.add(int(p))
    # Lo que quede bajo ese "Pasivos netos" (3.4.7 DEG) también se re-cuelga,
    # conservando su lado.
    for o in arbol.index:
        p = arbol.at[o, "padre"]
        if arbol.at[o, "tipo"] == "partida" and pd.notna(p) and int(p) in movidos_de:
            arbol.at[o, "padre"] = arbol.at[int(p), "padre"]
    hijos = _hijos(arbol)
    # Un lado sin hijos junto a sub-partidas que ya tienen sus propios lados es
    # solo el total de ese lado: desglose alternativo.
    for o in movidos_de:
        if not hijos.get(o):
            arbol.at[o, "alternativo"] = True
    for o in arbol.index:
        if arbol.at[o, "tipo"] == "lado" and arbol.at[o, "lado"] in ("activos", "pasivos") \
                and not hijos.get(o):
            hermanos = hijos.get(int(arbol.at[o, "padre"]), [])
            if any(_lados_hijos(h, arbol, hijos) & {"activos", "pasivos"} for h in hermanos):
                arbol.at[o, "alternativo"] = True

    # Desglose neto duplicado (p. ej. 3.3 por sector, además de activos/pasivos).
    arbol["duplicado"] = False
    for o in arbol.index:
        if _lados_hijos(o, arbol, hijos) & {"activos", "pasivos"}:
            for h in hijos.get(o, []):
                if arbol.at[h, "tipo"] == "partida" and not arbol.at[h, "lado"] and not (
                        _lados_hijos(h, arbol, hijos) & {"activos", "pasivos"}):
                    arbol.at[h, "duplicado"] = True

    # Activos de reserva = activos.
    reservas = arbol["codigo"].fillna("").str.match(r"^3\.5(\.|$)")
    arbol.loc[reservas, "lado"] = "activos"

    # Nivel según el padre corregido.
    nivel: dict[int, int] = {}
    for o in arbol.index:
        p = arbol.at[o, "padre"]
        nivel[o] = 0 if pd.isna(p) else nivel[int(p)] + 1
    arbol["nivel"] = pd.Series(nivel)
    arbol["cuenta_nombre"] = arbol["cuenta"].map(CUENTAS)
    return arbol


# ----------------------------------------------------------------------------
# Hojas (máximo nivel de detalle consistente)
# ----------------------------------------------------------------------------
def _cuadra(objetivo: pd.Series, suma: pd.Series, atol: float, rtol: float) -> bool:
    mask = objetivo.notna()
    if not mask.any():
        return True
    o, s = objetivo[mask].to_numpy(), suma[mask].fillna(0).to_numpy()
    return bool(np.all(np.abs(o - s) <= atol + rtol * np.abs(o)))


def seleccionar_hojas(arbol: pd.DataFrame, ancho: pd.DataFrame,
                      periodos: list[str] | None = None,
                      cuentas: tuple[str, ...] = ("1", "2", "3"),
                      atol: float = 1.0, rtol: float = 1e-3) -> pd.DataFrame:
    """Devuelve las partidas de máximo detalle cuyos valores suman su cuenta.

    Columnas: Orden, cuenta, lado, signo (para el neto: -1 si es pasivo),
    codigo, nombre, etiqueta, ruta.
    """
    periodos = periodos or list(ancho.columns)
    w = ancho.reindex(columns=periodos)
    hijos = _hijos(arbol)
    raices = arbol[(arbol.nivel == 0) & arbol.codigo.isin(cuentas)].index

    def componentes(o: int) -> list[tuple[int, int]]:
        out = []
        for h in hijos.get(o, []):
            fila = arbol.loc[h]
            if fila.memo or fila.duplicado:
                continue
            if fila.tipo == "lado" and fila.lado in ("credito", "debito"):
                continue
            signo = -1 if (fila.lado == "pasivos" and arbol.at[o, "lado"] != "pasivos") else 1
            out.append((h, signo))
        return out

    hojas: list[dict] = []

    def bajar(o: int, signo_acum: int, ruta: list[str], es_raiz: bool = False) -> None:
        comps = componentes(o)
        princ = [c for c in comps if not arbol.at[c[0], "alternativo"]]
        alt = [c for c in comps if arbol.at[c[0], "alternativo"]]
        objetivo = w.loc[o]
        elegido = None
        for cand in (princ, princ + alt, alt):
            if not cand:
                continue
            suma = sum(w.loc[h].fillna(0) * s for h, s in cand)
            if _cuadra(objetivo, suma, atol, rtol):
                elegido = cand
                break
        if elegido is None and es_raiz:
            elegido = princ
        if not elegido:
            hojas.append(dict(Orden=o, signo=signo_acum, ruta=" / ".join(ruta)))
            return
        for h, s in elegido:
            fila = arbol.loc[h]
            # La ruta usa nombres (los códigos de BanRep no siempre son
            # consistentes); los lados se indican al final de la etiqueta.
            paso = [] if fila.tipo == "lado" else [fila.nombre]
            bajar(h, signo_acum * s, ruta + paso)

    for r in raices:
        bajar(r, 1, [], es_raiz=True)

    out = pd.DataFrame(hojas).merge(
        arbol[["Orden", "codigo", "nombre", "tipo", "lado", "cuenta", "cuenta_nombre", "padre"]].reset_index(drop=True),
        on="Orden", how="left")

    def etiqueta(f) -> str:
        # p. ej. "Otra inversión / Préstamos / Gobierno general / Otros a largo plazo (pasivos)"
        es_reserva = str(f.codigo).startswith("3.5")
        if f.cuenta == "3" and f.lado and not es_reserva:
            return f"{f.ruta} ({f.lado})"
        return f.ruta

    out["codigo"] = [c if c else arbol.at[int(p), "codigo"] if t == "lado" else None
                     for c, p, t in zip(out.codigo, out.padre, out.tipo)]
    out["etiqueta"] = out.apply(etiqueta, axis=1)
    return out[["Orden", "cuenta", "cuenta_nombre", "lado", "signo", "codigo",
                "nombre", "etiqueta", "ruta"]]


def lados_cuenta_corriente(arbol: pd.DataFrame, ancho: pd.DataFrame,
                           hojas: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Valores de crédito y débito por hoja de cuenta corriente (Orden x periodo).
    Si la hoja no trae filas Crédito/Débito, se asigna según su nombre."""
    hijos = _hijos(arbol)
    cred, deb = {}, {}
    for o in hojas.loc[hojas.cuenta == "1", "Orden"]:
        lados = {arbol.at[h, "lado"]: h for h in hijos.get(o, []) if arbol.at[h, "tipo"] == "lado"}
        neto = ancho.loc[o]
        if "credito" in lados or "debito" in lados:
            cred[o] = ancho.loc[lados["credito"]] if "credito" in lados else neto * np.nan
            deb[o] = ancho.loc[lados["debito"]] if "debito" in lados else neto * np.nan
        elif re.search(r"d[eé]bito", arbol.at[o, "nombre"], re.I):
            cred[o], deb[o] = neto * 0, -neto
        else:
            cred[o], deb[o] = neto, neto * 0
    return {"credito": pd.DataFrame(cred).T, "debito": pd.DataFrame(deb).T}


def main() -> None:
    df = leer_raw()
    arbol = construir_arbol(df)
    largo = cargar_largo(df)
    ancho = a_ancho(largo)
    hojas = seleccionar_hojas(arbol, ancho, periodos=list(ancho.columns[-12:]))

    INTERM.mkdir(parents=True, exist_ok=True)
    arbol.reset_index(drop=True).to_csv(INTERM / "bp_banrep_arbol.csv", index=False, encoding="utf-8-sig")
    largo.to_csv(INTERM / "bp_banrep_long.csv", index=False, encoding="utf-8-sig")
    hojas.to_csv(INTERM / "bp_banrep_hojas.csv", index=False, encoding="utf-8-sig")
    print(f"Partidas: {len(arbol)} | hojas (últimos 12 trim.): {len(hojas)} "
          f"{hojas.groupby('cuenta').size().to_dict()} | periodos: "
          f"{largo.periodo.min()}-{largo.periodo.max()}")


if __name__ == "__main__":
    main()
