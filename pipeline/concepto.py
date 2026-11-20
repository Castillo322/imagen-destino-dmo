"""Paso 8. Concepto sintético "precio / valor / costo" por similitud semántica.

La consulta (p. ej. "precio valor costo") se lematiza y se proyecta al espacio LSA del corpus;
la similitud de cada comentario es el coseno con ese vector. Un comentario se considera ligado al
concepto si su similitud está en el percentil `percentil` o más de todo el corpus. Como evidencia
de qué capturó el concepto se listan los términos del vocabulario más cercanos al vector.

Como complemento léxico se calcula BM25 de la misma consulta: indica qué comentarios usan literalmente
las palabras del concepto. La similitud semántica encuentra también los que hablan de la idea con otras
palabras («caro», «regatear»); BM25 ordena los que la nombran.
"""
from collections import Counter

import numpy as np

from .outliers import log_odds, ngramas


def analizar(df, espacio, consulta_lemas, formas, dmo, col_texto, percentil, bm=None):
    q = espacio.proyectar_texto(consulta_lemas)
    df = df.copy()
    df["sim_concepto"] = espacio.Z @ q
    df["bm25_concepto"] = bm.puntajes(consulta_lemas) if bm is not None else 0.0
    normales = ~df.outlier
    tau = float(np.percentile(df.loc[normales, "sim_concepto"], percentil))
    df["ligado_concepto"] = normales & (df.sim_concepto >= tau)

    grupos = {"DMO": df[normales & (df.fuente == dmo)], "Percibida": df[normales & (df.fuente != dmo)]}
    for f in sorted(df.fuente.unique()):
        if f != dmo:
            grupos[f] = df[normales & (df.fuente == f)]
    por_grupo = {}
    lig_all = df[df.ligado_concepto]
    for nombre, g in grupos.items():
        lig = g[g.ligado_concepto]
        resto = df[normales & ~df.index.isin(lig.index)]
        c_lig = Counter(w for t in lig.lemas for w in t.split())
        c_rest = Counter(w for t in resto.lemas for w in t.split())
        por_grupo[nombre] = {
            "n": int(len(g)), "n_ligados": int(len(lig)),
            "pct_ligados": round(100 * len(lig) / max(len(g), 1), 2),
            "pct_mencionan": round(100 * float((g.bm25_concepto > 0).mean()), 2) if len(g) else 0.0,
            "pct_positivo_ligados": round(100 * float((lig.sentimiento == "positivo").mean()), 2) if len(lig) else None,
            "pct_positivo_resto": round(100 * float((g[~g.ligado_concepto].sentimiento == "positivo").mean()), 2) if len(g) else None,
            "sim_media": round(float(g.sim_concepto.mean()), 3),
            "contexto_palabras": [(formas.get(w, w), z) for w, z in log_odds(c_lig, c_rest, k=12, min_freq=2)] if len(lig) else [],
            "contexto_bigramas": [(" ".join(formas.get(x, x) for x in t.split()), c) for t, c in ngramas(lig.lemas, 2, k=8)],
        }
    top = lambda g: [{"texto": str(r[col_texto])[:400], "fuente": str(r.fuente), "similitud": round(float(r.sim_concepto), 3),
                      "sentimiento": r.sentimiento} for _, r in g.nlargest(5, "sim_concepto").iterrows()]
    return df, {
        "consulta": consulta_lemas, "umbral_similitud": round(tau, 3), "percentil": percentil,
        "terminos_cercanos": espacio.terminos_cercanos(q, formas, k=20),
        "por_grupo": por_grupo,
        "top5_global": top(df[normales]),
        "top5_bm25": [{"texto": str(r[col_texto])[:400], "fuente": str(r.fuente), "bm25": round(float(r.bm25_concepto), 2),
                       "sentimiento": r.sentimiento} for _, r in df[normales & (df.bm25_concepto > 0)].nlargest(5, "bm25_concepto").iterrows()],
        "top5_por_fuente": {str(f): top(df[normales & (df.fuente == f)]) for f in sorted(df.fuente.unique())},
        "n_ligados_total": int(len(lig_all)),
    }
