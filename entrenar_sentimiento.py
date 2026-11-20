"""Entrena el modelo de sentimiento en español que usa el pipeline.

Supervisión débil: las estrellas de TripAdvisor son la etiqueta (1-2 = negativo, 4-5 = positivo;
las de 3 se excluyen por ambiguas). Se reportan métricas con validación cruzada estratificada de
5 pliegues y se guarda el modelo entrenado con todos los datos en modelos/sentimiento_es.joblib.

Uso:
    python entrenar_sentimiento.py --csv datos/cdmx_unificado.csv --columna_texto texto \
        --columna_calificacion rating --fuente tripadvisor --columna_fuente fuente
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

from pipeline.preprocesamiento import limpiar
from pipeline.sentimiento import texto_para_modelo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--columna_texto", required=True)
    ap.add_argument("--columna_calificacion", required=True)
    ap.add_argument("--columna_fuente", default=None)
    ap.add_argument("--fuente", default=None, help="Usar sólo los registros de esta fuente")
    ap.add_argument("--salida", default="modelos")
    a = ap.parse_args()

    df = pd.read_csv(a.csv)
    if a.fuente:
        df = df[df[a.columna_fuente] == a.fuente]
    df = df.assign(cal=pd.to_numeric(df[a.columna_calificacion], errors="coerce")).dropna(subset=["cal"])
    df = df[df.cal.isin([1, 2, 4, 5])].copy()
    df["y"] = (df.cal >= 4).astype(int)
    X = df[a.columna_texto].map(limpiar).map(texto_para_modelo)

    modelo = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True),
        LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0),
    )
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    p = cross_val_predict(modelo, X, df.y, cv=cv, method="predict_proba")[:, 1]
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(df.y, pred).ravel()
    metricas = {
        "n_entrenamiento": int(len(df)), "n_negativos": int((df.y == 0).sum()), "n_positivos": int(df.y.sum()),
        "validacion": "5 pliegues estratificados",
        "exactitud": round(accuracy_score(df.y, pred), 3),
        "f1_macro": round(f1_score(df.y, pred, average="macro"), 3),
        "f1_negativo": round(f1_score(df.y, pred, pos_label=0), 3),
        "f1_positivo": round(f1_score(df.y, pred, pos_label=1), 3),
        "auc_roc": round(roc_auc_score(df.y, p), 3),
        "recall_negativo": round(tn / (tn + fp), 3),
        "precision_negativo": round(tn / (tn + fn), 3),
        "matriz_confusion": {"vn": int(tn), "fp": int(fp), "fn": int(fn), "vp": int(tp)},
    }
    modelo.fit(X, df.y)
    vec, lr = modelo.named_steps["tfidfvectorizer"], modelo.named_steps["logisticregression"]
    voc, coef = vec.get_feature_names_out(), lr.coef_[0]
    orden = np.argsort(coef)
    metricas["terminos_mas_negativos"] = [(voc[i], round(float(coef[i]), 2)) for i in orden[:25]]
    metricas["terminos_mas_positivos"] = [(voc[i], round(float(coef[i]), 2)) for i in orden[::-1][:25]]

    out = Path(a.salida)
    out.mkdir(exist_ok=True)
    joblib.dump(modelo, out / "sentimiento_es.joblib", compress=3)
    json.dump(metricas, open(out / "metricas_sentimiento_es.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in metricas.items() if not k.startswith("terminos")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
