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

## Informes anteriores

La carpeta `informes_anteriores/` almacena los informes de semestres previos, tanto el documento Word (`.docx`) como el Excel (`.xlsx`), para usarlos como referencia de formato y contenido.

## Tecnologías

- Python (ETL, análisis y gráficos)
- Excel (datos y tablas)
- Word (documento del informe)
