"""Análisis comparativo de la imagen del destino proyectada por la DMO frente a la imagen percibida.

Uso con una tabla unificada (los 7 parámetros son obligatorios):
    python analizador.py --csv datos/cdmx_unificado.csv --columna_texto texto --columna_fuente fuente \
        --etiqueta_dmo sectur --idioma es --titulo "Imagen de la CDMX" --paleta viridis

Uso con un archivo por fuente (cualquier formato: csv, tsv, txt, xlsx, xls, json, jsonl, parquet); cada archivo
es una fuente con el nombre del archivo, y --etiqueta_dmo es el nombre del archivo de la DMO:
    python analizador.py --csv dmo.xlsx resenas.csv foro.json --columna_texto texto --columna_fuente fuente \
        --etiqueta_dmo dmo --idioma es --titulo "Mi destino" --paleta okabe_ito

Salida en salidas/<titulo>_<idioma>/: corpus_procesado.parquet, resultados.json (lo lee el tablero) y reporte.html.
Todo corre sin conexión; no se usa ninguna API externa.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from matplotlib import colormaps

from pipeline import config, lectura
from pipeline.analisis import ErrorDeDatos, ejecutar, guardar


def argumentos(argv=None):
    ap = argparse.ArgumentParser(description="Imagen del destino: DMO (proyectada) frente a fuentes percibidas.")
    ap.add_argument("--csv", required=True, nargs="+",
                    help="1. Archivo unificado, o un archivo por fuente (csv, tsv, txt, xlsx, xls, json, jsonl, parquet)")
    ap.add_argument("--columna_texto", required=True, help="2. Columna con los comentarios (con varios archivos se pueden "
                                                           "unir varias separadas por coma; si no existe, se detecta sola)")
    ap.add_argument("--columna_fuente", required=True, help="3. Columna que identifica la fuente (con varios archivos, "
                                                             "se crea con el nombre de cada archivo)")
    ap.add_argument("--etiqueta_dmo", required=True, help="4. Fuente que corresponde a la DMO")
    ap.add_argument("--idioma", required=True, help="5. Idioma objetivo (es, en, fr, pt, it, de...)")
    ap.add_argument("--titulo", required=True, help="6. Título del reporte")
    ap.add_argument("--paleta", required=True, help=f"7. Paleta de colores; aptas para daltonismo: {', '.join(config.PALETAS_ACCESIBLES)}")
    ap.add_argument("--salida", default="salidas", help="Carpeta de salida (opcional)")
    ap.add_argument("--umbral_topicos", type=int, default=config.UMBRAL_TOPICOS)
    ap.add_argument("--contaminacion", type=float, default=config.CONTAMINACION_OUTLIERS)
    ap.add_argument("--umbral_polaridad", type=float, default=0.0)
    ap.add_argument("--concepto", default=None, help="Texto del concepto (por defecto «precio valor costo» en el idioma)")
    ap.add_argument("--semilla", type=int, default=config.SEMILLA)
    ap.add_argument("--excluir", default="", help="Palabras a ignorar, separadas por coma (p. ej. el nombre del destino)")
    ap.add_argument("--k_topicos", type=int, default=None, help="Fija el número de tópicos (por defecto se elige solo)")
    return ap.parse_args(argv)


def leer_entrada(a):
    """Una tabla con columnas de texto y de fuente a partir de uno o varios archivos."""
    if len(a.csv) == 1:
        df = lectura.leer_archivo(a.csv[0])
        if a.columna_texto not in df.columns:
            sys.exit(f"La columna «{a.columna_texto}» no existe en {a.csv[0]}. Columnas: {', '.join(map(str, df.columns))}")
        if a.columna_fuente not in df.columns:
            sys.exit(f"La columna «{a.columna_fuente}» no existe en {a.csv[0]}. Columnas: {', '.join(map(str, df.columns))}. "
                     "Si cada archivo es una fuente, pasa dos o más archivos en --csv.")
        return df, a.columna_texto, a.columna_fuente
    partes = []
    for ruta in a.csv:
        t = lectura.leer_archivo(ruta)
        pedidas = [c.strip() for c in a.columna_texto.split(",") if c.strip() in t.columns]
        cols, lista = (pedidas, None) if pedidas else lectura.sugerir_columnas(t)
        if not cols and not lista:
            sys.exit(f"No encontré una columna de texto en {ruta}. Columnas: {', '.join(map(str, t.columns))}")
        if not pedidas:
            print(f"  {Path(ruta).name}: no tiene «{a.columna_texto}»; uso {', '.join(cols) or '—'}"
                  + (f" y separo los comentarios de «{lista}»" if lista else "") + ".")
        partes.append(lectura.armar_fuente(t, cols, lectura.nombre_de_archivo(ruta), columna_lista=lista))
    df = pd.concat(partes, ignore_index=True).rename(columns={"texto": a.columna_texto, "fuente": a.columna_fuente})
    print("Fuentes:", ", ".join(f"{f} ({n:,})" for f, n in df[a.columna_fuente].value_counts().items()))
    return df, a.columna_texto, a.columna_fuente


def main(argv=None):
    a = argumentos(argv)
    if a.paleta not in colormaps and a.paleta not in ("okabe_ito", "okabe-ito"):
        sys.exit(f"Paleta «{a.paleta}» no existe. Usa, por ejemplo: {', '.join(config.PALETAS_ACCESIBLES)}")
    for ruta in a.csv:
        if not Path(ruta).exists():
            sys.exit(f"No existe el archivo {ruta}")
    Path(a.salida).mkdir(parents=True, exist_ok=True)
    try:
        df, col_texto, col_fuente = leer_entrada(a)
        resultado = ejecutar(df, col_texto, col_fuente, a.etiqueta_dmo, a.idioma, a.titulo, a.paleta,
                             excluir=a.excluir.split(","), umbral_topicos=a.umbral_topicos, contaminacion=a.contaminacion,
                             umbral_polaridad=a.umbral_polaridad, texto_concepto=a.concepto, k_topicos=a.k_topicos,
                             semilla=a.semilla, cache_idioma=Path(a.salida) / ".cache_idioma.parquet", origen=" ".join(a.csv))
    except (ErrorDeDatos, ValueError) as e:
        sys.exit(str(e))
    salida = guardar(a.salida, resultado)
    res = resultado["res"]
    print(f"Listo. Resultados en {salida}/ (reporte.html, resultados.json, corpus_procesado.parquet)")
    print(f"Temas encontrados: {res['topicos']['conjunto'].get('k', '—')} en común, {res['topicos']['positivo'].get('k', '—')} "
          f"positivos y {res['topicos']['negativo'].get('k', '—')} negativos (número elegido automáticamente).")
    print("\nResumen de brechas:")
    for b in res["resumen_brechas"]:
        print("  -", b)
    for f, c in res["comparacion"].get("dmo_vs_cada_fuente", {}).items():
        print(f"\nDMO frente a {f}:")
        for b in c["resumen"]:
            print("  -", b)


if __name__ == "__main__":
    main()
