"""Paso 4. Modelado de tópicos (NMF sobre TF-IDF) con frecuencias como respaldo.

  * El número de tópicos k se elige entre K_TOPICOS con coherencia x diversidad, calculada en
    3 muestras balanceadas distintas; se toma el k con mayor (media - 1 desviación estándar), es
    decir, el que es bueno de forma estable entre muestras. También puede fijarse con `k_fijo`:
      - coherencia: NPMI de las 10 palabras principales de cada tópico, medida sobre los propios
        comentarios y promediada con peso igual a la proporción de comentarios del tópico (así un
        tópico diminuto pero muy coherente no decide k);
      - diversidad: proporción de palabras distintas entre los tópicos (Dieng, Ruiz y Blei, 2020).
  * Los rasgos son unigramas y bigramas de lemas (así "valer pena" queda como una sola unidad).
  * El modelo se ajusta con una muestra balanceada por fuente y después se aplica a todos.
  * Tópico de un comentario = el de mayor peso; "sin tópico" si todos los pesos son cero.
  * Proporción de un tópico en una fuente = promedio de los pesos normalizados de sus comentarios,
    así un texto largo que trata varios temas aporta a cada uno en su medida.
  * Comentario representativo = el más cercano (coseno TF-IDF) al centroide de los comentarios
    del tópico, con al menos 8 palabras útiles.
  * Si el conjunto tiene menos de `umbral` comentarios, se reportan frecuencias de palabras.
Los tópicos se nombran sólo con sus palabras principales: no se les asigna ninguna categoría.
"""
from collections import Counter

import numpy as np
from sklearn.decomposition import NMF
from sklearn.preprocessing import normalize

from .representacion import muestra_balanceada, nuevo_vectorizador



def etiqueta_tema(palabras, n=3):
    """Las n primeras palabras del tema sin repetir: «centro · histórico · centro histórico» -> «centro · histórico · <siguiente>»."""
    elegidas, vistas = [], set()
    for w in palabras:
        partes = set(w.split())
        if partes <= vistas:
            continue
        elegidas.append(w)
        vistas |= partes
        if len(elegidas) == n:
            break
    return " · ".join(elegidas or palabras[:n])

def coherencia_npmi(B, topicos_idx):
    """NPMI promedio por pares de palabras; B = matriz binaria documentos x términos (csc)."""
    n = B.shape[0]
    df_t = np.asarray(B.sum(0)).ravel()
    puntajes = []
    for idx in topicos_idx:
        sub = B[:, idx]
        co = (sub.T @ sub).toarray()
        vals = []
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                pij = co[a, b] / n
                pi, pj = df_t[idx[a]] / n, df_t[idx[b]] / n
                if pij <= 0:
                    vals.append(-1.0)
                else:
                    vals.append(np.log(pij / (pi * pj)) / -np.log(pij))
        puntajes.append(float(np.mean(vals)))
    return float(np.mean(puntajes)), puntajes


def vista(termino, formas):
    return " ".join(formas.get(w, w) for w in termino.split())


def frecuencias(lemas, formas, k=30):
    c = Counter(w for t in lemas for w in t.split())
    return [(formas.get(w, w), int(n)) for w, n in c.most_common(k)]


def modelar(df_part, col_texto, formas, k_opciones, max_por_fuente, semilla, umbral, n_palabras=10,
            vec=None, devolver_modelo=False, k_fijo=None, n_muestras=3):
    """Devuelve (resultado, asignaciones[, modelo]) para un conjunto de comentarios.

    `vec`: vectorizador ya ajustado, para que dos modelos (DMO y percibida) compartan vocabulario.
    """
    n = len(df_part)
    vacio = lambda: ({"tipo": "frecuencias", "n": int(n), "frecuencias": frecuencias(df_part.lemas, formas)}, None) + \
        ((None,) if devolver_modelo else ())
    if n < umbral:
        return vacio()

    lemas = df_part.lemas.to_numpy(dtype=object)
    fuentes = df_part.fuente.to_numpy()
    idx_fit = muestra_balanceada(fuentes, max_por_fuente, semilla)
    if vec is None:
        vec = nuevo_vectorizador(len(idx_fit), ngramas=(1, 2))
        Xfit = vec.fit_transform(lemas[idx_fit])
    else:
        Xfit = vec.transform(lemas[idx_fit])
    X = vec.transform(lemas)
    voc = vec.get_feature_names_out()
    B = (X > 0).astype(np.int32).tocsc()

    # Cada k se evalúa con varias muestras balanceadas (semillas distintas) y se promedia el puntaje,
    # para que la elección no dependa de una sola muestra.
    muestras = [Xfit] + [vec.transform(lemas[muestra_balanceada(fuentes, max_por_fuente, semilla + r)])
                         for r in range(1, n_muestras)]
    evaluacion, modelos = [], {}
    for k in ([k_fijo] if k_fijo else k_opciones):
        if k >= min(Xfit.shape) - 1:
            break
        puntajes, cohs, cohps, divs, m0 = [], [], [], [], None
        for r, Xr in enumerate(muestras):
            m = NMF(n_components=k, init="nndsvda", random_state=semilla, max_iter=1000).fit(Xr)
            m0 = m0 or m
            top = [np.argsort(h)[::-1][:n_palabras] for h in m.components_]
            coh, por_t = coherencia_npmi(B, top)
            Wk = m.transform(X)
            ak = np.where(Wk.max(1) > 0, Wk.argmax(1), -1)
            prev = np.array([(ak == t).sum() for t in range(k)], dtype=float)
            coh_p = float(np.dot(prev / max(prev.sum(), 1), por_t))
            div = len(set(np.concatenate(top))) / (k * n_palabras)
            puntajes.append(coh_p * div); cohs.append(coh); cohps.append(coh_p); divs.append(div)
        puntaje = float(np.mean(puntajes))
        evaluacion.append({"k": int(k), "npmi": round(float(np.mean(cohs)), 4), "npmi_ponderada": round(float(np.mean(cohps)), 4),
                           "diversidad": round(float(np.mean(divs)), 3), "puntaje": round(puntaje, 4),
                           "puntaje_de": round(float(np.std(puntajes)), 4)})
        modelos[k] = m0
    if not evaluacion:
        return vacio()
    # Se elige el k con mejor puntaje "en el peor caso razonable" (media - 1 DE entre muestras):
    # favorece soluciones buenas y estables, no las que sólo salen bien con una muestra.
    elegido = max(evaluacion, key=lambda e: (round(e["puntaje"] - e["puntaje_de"], 4), -e["k"]))["k"]
    mejor = (None, elegido, modelos[elegido])

    _, k, modelo = mejor
    coh = next(e["npmi"] for e in evaluacion if e["k"] == k)
    W = modelo.transform(X)
    suma = W.sum(1, keepdims=True)
    Wn = np.divide(W, suma, out=np.zeros_like(W), where=suma > 0)
    asign = np.where(W.max(1) > 0, W.argmax(1), -1)
    _, coh_por_topico = coherencia_npmi(B, [np.argsort(h)[::-1][:n_palabras] for h in modelo.components_])
    Xn = normalize(X)

    topicos = []
    for t in range(k):
        miembros = np.flatnonzero(asign == t)
        palabras = [vista(voc[i], formas) for i in np.argsort(modelo.components_[t])[::-1][:n_palabras]]
        rep, rep_fuente = None, {}
        if len(miembros):
            cen = normalize(np.asarray(Xn[miembros].mean(0)))[0]
            sims = np.asarray(Xn[miembros] @ cen).ravel()
            largo = df_part.n_tokens.to_numpy()[miembros]
            sims_ok = np.where(largo >= 8, sims, sims - 10)  # preferir comentarios con contenido
            j = miembros[int(np.argmax(sims_ok))]
            rep = {"texto": str(df_part[col_texto].iloc[j])[:500], "fuente": str(fuentes[j]),
                   "similitud_centroide": round(float(sims.max()), 3)}
            for f in np.unique(fuentes[miembros]):
                mf = fuentes[miembros] == f
                jf = miembros[mf][int(np.argmax(sims_ok[mf]))]
                rep_fuente[str(f)] = str(df_part[col_texto].iloc[jf])[:300]
        mezcla = {str(f): int(c) for f, c in Counter(fuentes[miembros]).items()}
        topicos.append({"id": t, "etiqueta": etiqueta_tema(palabras), "palabras": palabras,
                        "n": int(len(miembros)), "npmi": round(coh_por_topico[t], 3), "mezcla_fuentes": mezcla,
                        "representativo": rep, "representativo_por_fuente": rep_fuente})

    por_fuente = {}
    for f in np.unique(fuentes):
        a = asign[fuentes == f]
        wf = Wn[(fuentes == f) & (asign >= 0)]
        por_fuente[str(f)] = {"n": int(len(a)),
                              "pct": {int(t): round(100 * float((a == t).mean()), 2) for t in range(k)},
                              "prop": {int(t): round(100 * float(wf[:, t].mean()), 2) if len(wf) else 0.0 for t in range(k)},
                              "sin_topico_pct": round(100 * float((a == -1).mean()), 2)}
    resultado = {"tipo": "topicos", "n": int(n), "k": int(k), "npmi": round(coh, 4), "evaluacion_k": evaluacion,
                 "topicos": topicos, "por_fuente": por_fuente}
    if devolver_modelo:
        return resultado, asign, {"Wn": Wn, "H": modelo.components_, "voc": voc, "modelo": modelo, "vec": vec}
    return resultado, asign


def frecuencias_por_fuente_pequena(df_part, formas, umbral):
    """Dentro de una partición, las fuentes con menos de `umbral` comentarios se describen por frecuencias."""
    salida = {}
    for f, g in df_part.groupby("fuente"):
        if len(g) < umbral:
            salida[str(f)] = {"n": int(len(g)), "frecuencias": frecuencias(g.lemas, formas, k=25)}
    return salida


def palabras_por_fuente(modelo_info, lemas, fuentes, formas, dmo, percibidas, n=6):
    """Con qué palabras aborda cada fuente cada tema: peso del término en el tema multiplicado por
    su TF-IDF medio en los comentarios de la fuente. "Percibida" promedia las fuentes percibidas."""
    H, vec = modelo_info["H"], modelo_info["vec"]
    voc = modelo_info["voc"]
    X = vec.transform(lemas)
    fuentes = np.asarray(fuentes)
    medias = {f: np.asarray(X[fuentes == f].mean(0)).ravel() for f in np.unique(fuentes)}
    validas = [medias[f] for f in percibidas if f in medias]
    if validas:
        medias["Percibida"] = np.mean(validas, axis=0)
    salida = {}
    for t in range(H.shape[0]):
        salida[t] = {}
        for f, m in medias.items():
            pesos = H[t] * m
            orden = [i for i in np.argsort(pesos)[::-1][:n] if pesos[i] > 0]
            salida[t][str(f)] = [vista(voc[i], formas) for i in orden]
    return salida
