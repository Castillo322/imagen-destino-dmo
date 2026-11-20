"""Tablero de la versión de terminal (Streamlit).

Lo abre analizador.py al terminar el análisis, con la carpeta de resultados y la paleta que se pidieron en la
terminal. Muestra lo mismo que el tablero web (app.py): las 9 pestañas, empezando por «Conclusiones».

Para volver a abrirlo sin repetir el análisis:
    streamlit run tablero.py -- --resultados salidas/<carpeta> --paleta okabe_ito
Sin --resultados abre la corrida más reciente de salidas/.
"""
import argparse
import json
import os
import runpy
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--resultados", default=None, help="Carpeta de resultados que escribió analizador.py")
ap.add_argument("--paleta", default=None, help="Paleta de colores (por defecto, la de la corrida)")
a, _ = ap.parse_known_args()

carpeta = a.resultados or os.environ.get("IMAGEN_RESULTADOS")
if carpeta is None:  # la corrida más reciente
    corridas = sorted((RAIZ / "salidas").glob("*/resultados.json"), key=lambda p: p.stat().st_mtime)
    carpeta = str(corridas[-1].parent) if corridas else ""
paleta = a.paleta
if not paleta and carpeta and (Path(carpeta) / "resultados.json").exists():
    paleta = json.loads((Path(carpeta) / "resultados.json").read_text(encoding="utf-8"))["parametros"].get("paleta")

runpy.run_path(str(RAIZ / "app.py"), init_globals={"TABLERO_TERMINAL": {"resultados": carpeta, "paleta": paleta}},
               run_name="__main__")
