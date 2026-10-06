# Balanza de Pagos

Esto es un trabajo de coyuntura de EAFIT, un capítulo del informe semestral del semillero de coyuntura.

## Autores

- Miguel Espinal Valencia
- Santiago Tupaz Ramírez
- Jerónimo Salazar Aguirre
- Mariana Díaz Silva

## Descripción

El capítulo de balanza de pagos en donde abordamos cuenta corriente y cuenta financiera, un análisis semestral.

## Estructura del repositorio

```
balanza-de-pagos/
├── data/
│   ├── raw/                  # Datos crudos
│   │   ├── banrep/           # Banco de la República (balanza de pagos)
│   │   ├── DANE/             # DANE (exportaciones)
│   │   ├── chile/
│   │   ├── peru/
│   │   ├── brasil/
│   │   ├── mexico/
│   │   └── sudafrica/
│   └── interm/               # Datos intermedios procesados
├── src/
│   ├── build/                # ETL: extracción, transformación y carga
│   ├── analisis/             # Análisis de los datos
│   └── graph/                # Generación de gráficos
├── output/                   # Resultados generados (tablas, gráficos, etc.)
├── informes_anteriores/      # Informes previos (Word y Excel)
├── LICENSE
└── README.md
```

## Flujo de trabajo

1. **Datos crudos** (`data/raw/`): cada país/fuente tiene su carpeta; en las de países, un `referencia.txt` indica el origen de los datos.
2. **ETL** (`src/build/`): limpieza y transformación; los resultados se guardan en `data/interm/`.
3. **Análisis** (`src/analisis/`): cálculo de indicadores de cuenta corriente y cuenta financiera.
4. **Gráficos** (`src/graph/`): visualizaciones para el informe.
5. **Resultados** (`output/`): archivos finales listos para integrar en el documento.

## Scripts

| Script | Etapa | Qué hace |
|---|---|---|
| `src/build/bp_banrep_detalle.py` | ETL | Lee la balanza de pagos de BanRep a máximo nivel de detalle, reconstruye la jerarquía de partidas (por la sangría del nombre) y deja `bp_banrep_arbol.csv`, `bp_banrep_long.csv` y `bp_banrep_hojas.csv` en `data/interm/`. |
| `src/analisis/top_partidas_bp.py` | Análisis | Por cuenta (corriente y financiera) y lado (neto, crédito/débito, activos/pasivos): top 5 por participación (con su crecimiento), top 5 por crecimiento (con su participación) y top 5 por contribución (con participación y crecimiento). Genera `output/top_partidas_bp_<periodo>_vs_<base>.xlsx`. |

```bash
python src/build/bp_banrep_detalle.py                              # opcional: deja los intermedios para inspección
python src/analisis/top_partidas_bp.py                             # último semestre vs mismo semestre del año anterior
python src/analisis/top_partidas_bp.py --periodo 2026Q2 --base anterior --top 10 --umbral 0.5
```

## Informes anteriores

La carpeta `informes_anteriores/` almacena los informes de semestres previos, tanto el documento Word (`.docx`) como el Excel (`.xlsx`), para usarlos como referencia de formato y contenido.

## Tecnologías

- Python (ETL, análisis y gráficos)
- Excel (datos y tablas)
- Word (documento del informe)
