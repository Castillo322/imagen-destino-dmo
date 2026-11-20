"""Análisis comparativo de la imagen del destino proyectada por la DMO frente a la imagen percibida.

Es el script del proyecto: se corre desde la terminal con los 7 parámetros obligatorios, hace los 8 pasos del
análisis, guarda los resultados y, al terminar, abre el tablero de Streamlit con esos resultados (tablero.py).

1) Con la base unificada (un archivo con columna de texto y columna de fuente):
    python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente \
        --etiqueta_dmo sectur --idioma es --titulo "Imagen de la CDMX" --paleta okabe_ito

2) Con dos archivos: el de la DMO y el de los visitantes (la base unificada, una sola plataforma o el archivo
   que proponga el profesor). También se aceptan más de dos:
    python analizador.py --csv datos/originales/sectur.csv datos/originales/TripAdvisor.csv.gz \
        --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es \
        --titulo "Sectur vs TripAdvisor" --paleta okabe_ito

   Cómo se reparten las fuentes con varios archivos:
   - Si un archivo trae la columna de fuente (p. ej. la base unificada), cada fila conserva su etiqueta.
   - Si no la trae, todo el archivo es una fuente con el nombre del archivo (sectur.csv -> sectur,
     instaUGC.csv -> instagram, redditcdmx.csv -> reddit, TripAdvisor.csv.gz -> tripadvisor, mi_archivo.xlsx -> mi_archivo).
   - Si la DMO viene en su propio archivo y otro archivo también la trae, se usa la del archivo propio (no se duplica).
   - Si un archivo no tiene la columna de texto indicada, se detecta sola (y se separan los comentarios que vengan
     varios en una celda, como las respuestas de un hilo de Reddit).

Formatos: csv, tsv, txt, xlsx, xls, json, jsonl y parquet, también comprimidos con .gz.
Salida en salidas/<titulo>_<idioma>/: corpus_procesado.parquet, resultados.json y reporte.html.
Opcionales: --sin_tablero (sólo genera los archivos), --puerto (puerto del tablero, 8501 por defecto) y los
parámetros de análisis (--excluir, --k_topicos, --contaminacion, --umbral_topicos, --umbral_polaridad, --concepto,
--semilla, --salida). Todo corre sin conexión; no se usa ninguna API externa.
"""
import argparse
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import pandas as pd
from matplotlib import colormaps

from pipeline import config, lectura
from pipeline.analisis import ErrorDeDatos, ejecutar, guardar

RAIZ = Path(__file__).resolve().parent


def argumentos(argv=None):
    ap = argparse.ArgumentParser(
        description="Imagen del destino: DMO (proyectada) frente a fuentes percibidas. Al terminar abre el tablero.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos en README.md. Con dos archivos: --csv <archivo_dmo> <archivo_visitantes>.")
    ap.add_argument("--csv", required=True, nargs="+",
                    help="1. Base unificada (con columna de fuente), o el archivo de la DMO y el de los visitantes "
                         "(csv, tsv, txt, xlsx, xls, json, jsonl, parquet; también .gz)")
    ap.add_argument("--columna_texto", required=True, help="2. Columna con los comentarios (si un archivo no la tiene, "
                                                           "se detecta sola; se pueden unir varias separadas por coma)")
    ap.add_argument("--columna_fuente", required=True, help="3. Columna que identifica la fuente (en un archivo sin esa "
                                                             "columna, la fuente es el nombre del archivo)")
    ap.add_argument("--etiqueta_dmo", required=True, help="4. Fuente que corresponde a la DMO (p. ej. sectur o dmo)")
    ap.add_argument("--idioma", required=True, help="5. Idioma objetivo: es, en, fr, pt, it, de...")
    ap.add_argument("--titulo", required=True, help="6. Título del reporte y del tablero (y nombre de la carpeta de salida)")
    ap.add_argument("--paleta", required=True, help=f"7. Paleta de colores; aptas para daltonismo: {', '.join(config.PALETAS_ACCESIBLES)}")
    ap.add_argument("--sin_tablero", action="store_true", help="Sólo genera los archivos; no abre el tablero")
    ap.add_argument("--puerto", type=int, default=8501, help="Puerto del tablero (8501 por defecto; si está ocupado se usa el siguiente)")
    ap.add_argument("--salida", default="salidas", help="Carpeta de salida (por defecto, salidas)")
    ap.add_argument("--umbral_topicos", type=int, default=config.UMBRAL_TOPICOS,
                    help="Con menos comentarios, frecuencias de palabras en lugar de tópicos (por defecto 30)")
    ap.add_argument("--contaminacion", type=float, default=config.CONTAMINACION_OUTLIERS,
                    help="Proporción de atípicos por fuente (por defecto 0.03)")
    ap.add_argument("--umbral_polaridad", type=float, default=0.0, help="Polaridad mínima para «positivo» (por defecto 0)")
    ap.add_argument("--concepto", default=None, help="Concepto a rastrear (por defecto «precio valor costo» en el idioma)")
    ap.add_argument("--semilla", type=int, default=config.SEMILLA, help="Semilla (por defecto 42)")
    ap.add_argument("--excluir", default="", help="Palabras a ignorar, separadas por coma (p. ej. el nombre del destino)")
    ap.add_argument("--k_topicos", type=int, default=None, help="Fija el número de tópicos (por defecto se elige solo)")
    return ap.parse_args(argv)


def leer_entrada(a):
    """Una tabla con columnas de texto y de fuente a partir de uno o varios archivos (ver la ayuda del módulo)."""
    if len(a.csv) == 1:
        df = lectura.leer_archivo(a.csv[0])
        if a.columna_texto not in df.columns:
            sys.exit(f"La columna «{a.columna_texto}» no existe en {a.csv[0]}. Columnas: {', '.join(map(str, df.columns))}")
        if a.columna_fuente not in df.columns:
            sys.exit(f"La columna «{a.columna_fuente}» no existe en {a.csv[0]}. Columnas: {', '.join(map(str, df.columns))}.\n"
                     "Si este archivo es de una sola fuente, pásalo junto con el de la DMO: --csv <archivo_dmo> <este_archivo>")
        print(f"Archivo: {Path(a.csv[0]).name} · fuentes: "
              + ", ".join(f"{f} ({n:,})" for f, n in df[a.columna_fuente].astype(str).value_counts().items()))
        return df, a.columna_texto, a.columna_fuente

    partes = []  # (archivo, fuente, tabla, viene_de_columna_de_fuente)
    print("Archivos:")
    for ruta in a.csv:
        t = lectura.leer_archivo(ruta)
        nombre = Path(ruta).name
        pedidas = [c.strip() for c in a.columna_texto.split(",") if c.strip() in t.columns]
        cols, lista = (pedidas, None) if pedidas else lectura.sugerir_columnas(t)
        if not cols and not lista:
            sys.exit(f"No encontré una columna de texto en {ruta}. Columnas: {', '.join(map(str, t.columns))}")
        detalle = "" if pedidas else (f" (no tiene «{a.columna_texto}»; uso {', '.join(cols) or '—'}"
                                      + (f" y separo los comentarios de «{lista}»" if lista else "") + ")")
        if a.columna_fuente in t.columns:  # ya trae su columna de fuente (p. ej. la base unificada)
            etq = t[a.columna_fuente].astype(str).str.strip()
            for f in sorted(etq.unique()):
                partes.append((nombre, f, lectura.armar_fuente(t[etq == f], cols, f, columna_lista=lista), True))
            print(f"  {nombre}: trae la columna «{a.columna_fuente}» → "
                  + ", ".join(f"{f} ({n:,})" for f, n in etq.value_counts().items()) + detalle)
        else:
            f = lectura.nombre_sugerido(ruta)
            partes.append((nombre, f, lectura.armar_fuente(t, cols, f, columna_lista=lista), False))
            print(f"  {nombre}: fuente «{f}»{' (DMO)' if f == a.etiqueta_dmo else ''}{detalle}")
    # La DMO en su propio archivo manda: si otro archivo también la trae, esas filas no se duplican
    dmo_propia = [p for p in partes if p[1] == a.etiqueta_dmo and not p[3]]
    if dmo_propia:
        for p in [p for p in partes if p[1] == a.etiqueta_dmo and p[3]]:
            print(f"  {p[0]}: también trae «{a.etiqueta_dmo}» ({len(p[2]):,}); se usa la de {dmo_propia[0][0]} y ésta se omite.")
        partes = [p for p in partes if not (p[1] == a.etiqueta_dmo and p[3])]
    df = pd.concat([p[2] for p in partes], ignore_index=True)
    df = df.rename(columns={"texto": a.columna_texto, "fuente": a.columna_fuente})
    fuentes = df[a.columna_fuente].value_counts()
    print("Fuentes a comparar:", ", ".join(f"{f}{' [DMO]' if f == a.etiqueta_dmo else ''} ({n:,})" for f, n in fuentes.items()))
    if a.etiqueta_dmo not in fuentes:
        sys.exit(f"Ninguna fuente se llama «{a.etiqueta_dmo}». Fuentes: {', '.join(fuentes.index)}. "
                 "Revisa --etiqueta_dmo (con un archivo propio, es el nombre del archivo sin extensión).")
    return df, a.columna_texto, a.columna_fuente


def puerto_libre(desde):
    for p in range(desde, desde + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return desde


def abrir_tablero(carpeta, paleta, puerto):
    """Abre tablero.py (Streamlit) con los resultados de esta corrida y la paleta elegida; se cierra con Ctrl+C."""
    puerto = puerto_libre(puerto)
    url = f"http://localhost:{puerto}"
    cmd = [sys.executable, "-m", "streamlit", "run", str(RAIZ / "tablero.py"), "--server.port", str(puerto),
           "--server.headless", "true", "--browser.gatherUsageStats", "false",
           "--", "--resultados", str(Path(carpeta).resolve()), "--paleta", paleta]
    print(f"\nAbriendo el tablero en {url} … (para cerrarlo: Ctrl+C en esta terminal)")
    proc = subprocess.Popen(cmd, cwd=RAIZ)
    try:
        for _ in range(120):  # espera a que el servidor responda y abre el navegador
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", puerto)) == 0:
                    break
            if proc.poll() is not None:
                sys.exit("No se pudo iniciar el tablero. Revisa que streamlit esté instalado (pip install -r requirements.txt).")
            time.sleep(0.5)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        print(f"Tablero listo: {url}  (si no se abrió solo, copia esa dirección en el navegador)")
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\nTablero cerrado.")


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
    print(f"\nListo. Resultados en {salida}/ (reporte.html, resultados.json, corpus_procesado.parquet)")
    print(f"Temas encontrados: {res['topicos']['conjunto'].get('k', '—')} en común, {res['topicos']['positivo'].get('k', '—')} "
          f"positivos y {res['topicos']['negativo'].get('k', '—')} negativos (número elegido automáticamente).")
    print("\nResumen de brechas:")
    for b in res["resumen_brechas"]:
        print("  -", b)
    for f, c in res["comparacion"].get("dmo_vs_cada_fuente", {}).items():
        print(f"\nDMO frente a {f}:")
        for b in c["resumen"]:
            print("  -", b)
    if res.get("conclusiones"):
        from pipeline.conclusiones import texto
        print("\n" + texto(res["conclusiones"]))
    if not a.sin_tablero:
        abrir_tablero(salida, a.paleta, a.puerto)


if __name__ == "__main__":
    main()
