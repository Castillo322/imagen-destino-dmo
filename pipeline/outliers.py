"""Paso 2. Comentarios atípicos sobre la base unificada y análisis de n-gramas de los atípicos.

  * Un solo Isolation Forest para TODA la base unificada (todas las fuentes juntas, en el mismo
    espacio LSA). Se entrena con una muestra balanceada por fuente para que la fuente más grande
    no defina sola qué es "normal". Rasgos: los primeros componentes LSA (de qué habla) y el
    logaritmo de la longitud estandarizado (qué tan largo es).
  * El corte (contaminación, 3 % por defecto) se aplica dentro de cada fuente: con un corte único,
    casi todos los atípicos serían de la fuente más grande y no se podría analizar la información
    atípica de las demás. Las fuentes con menos de `min_docs` comentarios usan el corte global.
  * Sobre los atípicos (de toda la base y de cada fuente) se cuentan unigramas, bigramas y
    trigramas, y se buscan las palabras que más los distinguen de los comentarios normales
    (log-odds con prior de Dirichlet). Los atípicos no pasan a los pasos siguientes.
"""
from collections import Counter

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import CountVectorizer


def detectar(df, Z, contaminacion, semilla, max_por_fuente=2000, min_docs=30, dims=50):
    from .representacion import muestra_balanceada
    df = df.copy()
    largo = np.log1p(df["n_tokens"].to_numpy(dtype=float))
    feats = np.hstack([Z[:, :dims], ((largo - largo.mean()) / (largo.std() + 1e-9))[:, None]])
    fuentes = df["fuente"].to_numpy()
    idx = muestra_balanceada(fuentes, max_por_fuente, semilla)
    bosque = IsolationForest(n_estimators=300, random_state=semilla).fit(feats[idx])
    puntaje = -bosque.score_samples(feats)          # más alto = más atípico
    corte_global = np.percentile(puntaje, 100 * (1 - contaminacion))
    outlier = np.zeros(len(df), dtype=bool)
    for f in np.unique(fuentes):
        m = fuentes == f
        corte = np.percentile(puntaje[m], 100 * (1 - contaminacion)) if m.sum() >= min_docs else corte_global
        outlier[m] = puntaje[m] >= corte
    df["outlier"] = outlier
    df["puntaje_atipico"] = puntaje
    df["atipico_corte_global"] = puntaje >= corte_global
    return df


def ngramas(textos, n, k=10):
    textos = [t for t in textos if len(t.split()) >= n]
    if not textos:
        return []
    cv = CountVectorizer(ngram_range=(n, n), tokenizer=str.split, token_pattern=None, lowercase=False)
    try:
        X = cv.fit_transform(textos)
    except ValueError:
        return []
    s = np.asarray(X.sum(0)).ravel()
    orden = np.argsort(s)[::-1][:k]
    voc = cv.get_feature_names_out()
    return [(voc[i], int(s[i])) for i in orden]


def log_odds(c1: Counter, c2: Counter, k=12, min_freq=3):
    """Palabras más asociadas a c1 frente a c2 (Monroe, Colaresi y Quinn, 2008)."""
    prior = c1 + c2
    n1, n2, a0 = sum(c1.values()), sum(c2.values()), sum(prior.values())
    res = []
    for w, a in prior.items():
        if c1[w] < min_freq:
            continue
        l1 = np.log((c1[w] + a) / (n1 + a0 - c1[w] - a))
        l2 = np.log((c2[w] + a) / (n2 + a0 - c2[w] - a))
        res.append((w, float((l1 - l2) / np.sqrt(1 / (c1[w] + a) + 1 / (c2[w] + a)))))
    res.sort(key=lambda x: -x[1])
    return [(w, round(z, 2)) for w, z in res[:k]]


def resumir(df, col_texto, formas):
    """Información contenida en los atípicos de cada fuente."""
    vis = lambda s: " ".join(formas.get(w, w) for w in s.split())
    salida = {}
    for f, g in df.groupby("fuente"):
        at, no = g[g.outlier], g[~g.outlier]
        if at.empty:
            salida[f] = {"n": 0, "n_fuente": int(len(g))}
            continue
        c_at = Counter(w for t in at.lemas for w in t.split())
        c_no = Counter(w for t in no.lemas for w in t.split())
        ejemplos = at.sort_values("puntaje_atipico", ascending=False).head(6)
        salida[f] = {
            "n": int(len(at)), "n_fuente": int(len(g)),
            "pct": round(100 * len(at) / len(g), 2),
            "palabras_mediana_atipicos": float(at.n_tokens.median()),
            "palabras_mediana_normales": float(no.n_tokens.median()) if len(no) else None,
            "unigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 1)],
            "bigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 2)],
            "trigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 3)],
            "distintivas": [(formas.get(w, w), z) for w, z in log_odds(c_at, c_no, min_freq=2 if len(at) < 50 else 3)],
            "ejemplos": [{"texto": str(t)[:400], "puntaje": round(float(p), 3)}
                         for t, p in zip(ejemplos[col_texto], ejemplos.puntaje_atipico)],
        }
    return salida


def resumir_global(df, col_texto, formas, k=15):
    """Atípicos de toda la base unificada: composición, n-gramas, palabras distintivas y ejemplos."""
    vis = lambda t: " ".join(formas.get(w, w) for w in t.split())
    at, no = df[df.outlier], df[~df.outlier]
    if at.empty:
        return {"n": 0}
    c_at = Counter(w for t in at.lemas for w in t.split())
    c_no = Counter(w for t in no.lemas for w in t.split())
    ejemplos = at.sort_values("puntaje_atipico", ascending=False).head(8)
    corte_unico = df[df.atipico_corte_global].fuente.value_counts()
    return {
        "n": int(len(at)), "n_total": int(len(df)), "pct": round(100 * len(at) / len(df), 2),
        "n_normales": int(len(no)),
        "por_fuente": {str(f): int(n) for f, n in at.fuente.value_counts().items()},
        "si_corte_unico": {str(f): int(corte_unico.get(f, 0)) for f in sorted(df.fuente.unique())},
        "palabras_mediana_atipicos": float(at.n_tokens.median()),
        "palabras_mediana_normales": float(no.n_tokens.median()),
        "unigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 1, k)],
        "bigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 2, k)],
        "trigramas": [(vis(t), c) for t, c in ngramas(at.lemas, 3, k)],
        "distintivas": [(formas.get(w, w), z) for w, z in log_odds(c_at, c_no, k=k)],
        "ejemplos": [{"texto": str(t)[:400], "fuente": str(f), "puntaje": round(float(p), 3)}
                     for t, f, p in zip(ejemplos[col_texto], ejemplos.fuente, ejemplos.puntaje_atipico)],
    }
