"""Paso 3. Sentimiento binario (positivo / negativo) por umbral de polaridad.

  * Español: modelo propio (TF-IDF de 1-2 gramas + regresión logística) entrenado con reseñas de
    TripAdvisor usando sus estrellas como etiqueta (1-2 = negativo, 4-5 = positivo). Ver
    `entrenar_sentimiento.py` y `modelos/metricas_sentimiento_es.json`.
  * Inglés: VADER (léxico con reglas para negación e intensificadores).
Polaridad en [-1, 1]; positivo si polaridad >= umbral (0 por defecto).
"""
from pathlib import Path

import joblib
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .preprocesamiento import sin_acentos

RUTA_MODELOS = Path(__file__).resolve().parent.parent / "modelos"


def texto_para_modelo(texto_limpio: str) -> str:
    """El modelo español se entrenó sin acentos y conservando negaciones ("no", "nada")."""
    return sin_acentos(texto_limpio)


class Sentimiento:
    def __init__(self):
        self._vader = SentimentIntensityAnalyzer()
        ruta = RUTA_MODELOS / "sentimiento_es.joblib"
        self._es = None
        if ruta.exists():
            try:
                self._es = joblib.load(ruta)
            except Exception as e:  # p. ej. otra versión de scikit-learn
                raise SystemExit(
                    f"No se pudo cargar {ruta.name} ({e}). Vuelve a entrenarlo con:\n"
                    "  python entrenar_sentimiento.py --csv datos/cdmx_unificado.csv --columna_texto texto "
                    "--columna_calificacion rating --columna_fuente fuente --fuente tripadvisor")

    def metodo(self, idioma):
        if idioma == "es" and self._es is not None:
            return "modelo_es_resenas"
        return "vader"

    def polaridad(self, textos_crudos, textos_limpios, idiomas):
        pol = np.zeros(len(textos_crudos))
        idiomas = np.asarray(idiomas)
        es = np.flatnonzero((idiomas == "es") & (self._es is not None))
        if len(es):
            p = self._es.predict_proba([texto_para_modelo(textos_limpios[i]) for i in es])[:, 1]
            pol[es] = 2 * p - 1
        otros = np.setdiff1d(np.arange(len(textos_crudos)), es)
        for i in otros:
            pol[i] = self._vader.polarity_scores(str(textos_crudos[i]))["compound"]
        return pol


def clasificar(df, col_texto, umbral=0.0):
    s = Sentimiento()
    df = df.copy()
    m = ~df["outlier"]
    df["polaridad"] = np.nan
    df["sentimiento"] = None
    df["metodo_sentimiento"] = None
    sub = df[m]
    pol = s.polaridad(sub[col_texto].tolist(), sub["texto_limpio"].tolist(), sub["idioma_detectado"].tolist())
    df.loc[m, "polaridad"] = pol
    df.loc[m, "sentimiento"] = np.where(pol >= umbral, "positivo", "negativo")
    df.loc[m, "metodo_sentimiento"] = [s.metodo(i) for i in sub["idioma_detectado"]]
    return df
