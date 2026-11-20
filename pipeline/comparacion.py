"""Paso 5. Comparación entre la imagen proyectada (DMO) y la percibida (resto de fuentes).

Se apoya en el constructo de imagen del destino:
  * componente cognitivo -> de qué se habla (un solo modelo de tópicos para todos los textos, así
                            los temas son los mismos para la DMO y para cada fuente percibida)
  * componente afectivo  -> con qué tono (sentimiento), en total y dentro de cada tópico
  * alineación global    -> similitud semántica entre los corpus (índice de alineación)
"Percibida" se resume como el promedio de las fuentes percibidas, cada una con el mismo peso, para
que la fuente con más comentarios no imponga su agenda; también se reporta el agregado simple.
"""
import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency
from sklearn.preprocessing import normalize


def _intervalos_brecha(Wn, asign, fuentes, dmo, perc, k, semilla, n_boot=500):
    """IC 95 % bootstrap de la brecha (DMO - percibida) por tema, remuestreando comentarios dentro de cada fuente."""
    ok = asign >= 0
    grupos = {f: np.flatnonzero(ok & (fuentes == f)) for f in np.unique(fuentes)}
    # un generador por fuente: los intervalos no dependen del nombre de las fuentes
    rng = {f: np.random.default_rng([semilla, len(i)]) for f, i in grupos.items()}
    perc = [f for f in perc if f in grupos and len(grupos[f])]
    if dmo not in grupos or not len(grupos[dmo]) or not perc:
        return None
    boot = np.empty((n_boot, k))
    for b in range(n_boot):
        media = {f: Wn[rng[f].choice(i, len(i))].mean(0) for f, i in grupos.items() if len(i)}
        boot[b] = 100 * (media[dmo] - np.mean([media[f] for f in perc], axis=0))
    return np.percentile(boot, [2.5, 97.5], axis=0)


def comparar_topicos(df, res_conjunto, dmo, umbral_pp, Wn=None, semilla=42, minimo=0, palabras_fuente=None):
    """Compara qué parte del contenido dedica la DMO y qué parte las fuentes percibidas a cada tema
    de un mismo modelo de tópicos (espacio temático común, sin emparejamientos heurísticos).

    `df` son los comentarios normales en el mismo orden que las filas de `Wn` y con `topico_conjunto`.
    Un tema se marca como brecha si la diferencia es de al menos `umbral_pp` puntos y su IC 95 %
    bootstrap no incluye el cero.
    """
    if res_conjunto.get("tipo") != "topicos":
        return None
    k = res_conjunto["k"]
    pf = res_conjunto["por_fuente"]
    percibidas = [f for f in pf if f != dmo and pf[f]["n"] >= minimo] or [f for f in pf if f != dmo]
    dist_dmo = np.array([pf[dmo]["prop"][t] for t in range(k)]) if dmo in pf else np.zeros(k)
    dist_perc = np.mean([[pf[f]["prop"][t] for t in range(k)] for f in percibidas], axis=0)
    sub = df[df.topico_conjunto >= 0]
    n_perc = {f: pf[f]["n"] for f in percibidas}
    agregado = np.sum([[pf[f]["prop"][t] * n_perc[f] for t in range(k)] for f in percibidas], axis=0) / max(sum(n_perc.values()), 1)
    ic = None
    if Wn is not None:
        ic = _intervalos_brecha(Wn, df.topico_conjunto.fillna(-1).to_numpy().astype(int), df.fuente.to_numpy(), dmo, percibidas, k, semilla)

    filas = []
    for t, info in enumerate(res_conjunto["topicos"]):
        g = sub[sub.topico_conjunto == t]
        gp, gd = g[g.fuente != dmo], g[g.fuente == dmo]
        brecha = float(dist_dmo[t] - dist_perc[t])
        lo, hi = (float(ic[0, t]), float(ic[1, t])) if ic is not None else (brecha, brecha)
        distinto = lo > 0 or hi < 0
        if brecha >= umbral_pp and distinto:
            clase = "Proyectado, poco percibido"
        elif brecha <= -umbral_pp and distinto:
            clase = "Percibido, poco proyectado"
        elif min(dist_dmo[t], dist_perc[t]) >= 100 / (2 * k):
            clase = "Coincidencia"
        else:
            clase = "Marginal en ambos"
        filas.append({
            "id": t, "etiqueta": info["etiqueta"], "palabras": info["palabras"][:8],
            "pct_dmo": round(float(dist_dmo[t]), 2), "pct_percibida": round(float(dist_perc[t]), 2),
            "pct_percibida_agregado": round(float(agregado[t]), 2),
            "pct_por_fuente": {f: pf[f]["prop"][t] for f in pf},
            "brecha_pp": round(brecha, 2), "brecha_ic95": [round(lo, 2), round(hi, 2)], "clase": clase,
            "pct_negativo_percibida": round(100 * float((gp.sentimiento == "negativo").mean()), 2) if len(gp) else None,
            "pct_negativo_dmo": round(100 * float((gd.sentimiento == "negativo").mean()), 2) if len(gd) else None,
            "n_percibida": int(len(gp)), "n_dmo": int(len(gd)),
            "palabras_dmo": (palabras_fuente or {}).get(t, {}).get(dmo, []),
            "palabras_percibida": (palabras_fuente or {}).get(t, {}).get("Percibida", []),
            "palabras_por_fuente": {f: v for f, v in (palabras_fuente or {}).get(t, {}).items() if f != "Percibida"},
            "palabras_compartidas": len(set((palabras_fuente or {}).get(t, {}).get(dmo, [])) &
                                        set((palabras_fuente or {}).get(t, {}).get("Percibida", []))) if palabras_fuente else None,
            "ejemplo_dmo": info["representativo_por_fuente"].get(dmo),
            "ejemplo_percibida": next((v for f, v in info["representativo_por_fuente"].items() if f != dmo), None),
        })
    p, q = dist_dmo / max(dist_dmo.sum(), 1e-9), dist_perc / max(dist_perc.sum(), 1e-9)
    jsd = float(jensenshannon(p, q, base=2) ** 2)
    return {"temas": filas, "jsd": round(jsd, 4), "congruencia_tematica": round(1 - jsd, 4),
            "umbral_brecha_pp": umbral_pp, "fuentes_en_promedio": percibidas}


def comparar_sentimiento(df, dmo, minimo=0):
    sub = df[df.sentimiento.notna()]
    por_fuente = {}
    for f, g in sub.groupby("fuente"):
        por_fuente[str(f)] = {"n": int(len(g)), "pct_positivo": round(100 * float((g.sentimiento == "positivo").mean()), 2),
                              "polaridad_media": round(float(g.polaridad.mean()), 3),
                              "metodo": g.metodo_sentimiento.mode().iloc[0]}
    perc = [f for f in por_fuente if f != dmo and por_fuente[f]["n"] >= minimo] or [f for f in por_fuente if f != dmo]
    bal = float(np.mean([por_fuente[f]["pct_positivo"] for f in perc])) if perc else None
    tabla = np.array([[((sub.fuente == dmo) & (sub.sentimiento == s)).sum() for s in ("positivo", "negativo")],
                      [((sub.fuente != dmo) & (sub.sentimiento == s)).sum() for s in ("positivo", "negativo")]])
    prueba = None
    if tabla.min() >= 0 and tabla.sum(1).min() > 0 and tabla.sum(0).min() > 0:
        chi2, pv, *_ = chi2_contingency(tabla)
        prueba = {"chi2": round(float(chi2), 2), "p_valor": float(f"{pv:.3g}")}
    return {"por_fuente": por_fuente, "pct_positivo_dmo": por_fuente.get(dmo, {}).get("pct_positivo"),
            "pct_positivo_percibida": round(bal, 2) if bal is not None else None,
            "pct_positivo_percibida_agregado": round(100 * float((sub[sub.fuente != dmo].sentimiento == "positivo").mean()), 2),
            "prueba_chi2_dmo_vs_percibida": prueba}


def similitud_global(df, Z, dmo, semilla, n_boot=300, minimo=0):
    m = df.outlier.to_numpy() == False  # noqa: E712
    fuentes = df.fuente.to_numpy()
    idx_dmo = np.flatnonzero(m & (fuentes == dmo))
    percibidas = [f for f in np.unique(fuentes[m]) if f != dmo]
    idx_f = {f: np.flatnonzero(m & (fuentes == f)) for f in percibidas}
    cen = lambda ids: normalize(Z[ids].mean(0, keepdims=True))[0]
    c_dmo = cen(idx_dmo)
    c_f = {f: cen(i) for f, i in idx_f.items()}
    validas = [f for f in percibidas if len(idx_f[f]) >= minimo] or percibidas
    c_perc = normalize(np.mean([c_f[f] for f in validas], axis=0, keepdims=True))[0]
    ias = float(c_dmo @ c_perc)

    rng_d = np.random.default_rng([semilla, len(idx_dmo)])
    rng_f = {f: np.random.default_rng([semilla, len(idx_f[f])]) for f in validas}
    boot = []
    for _ in range(n_boot):
        b_dmo = cen(rng_d.choice(idx_dmo, len(idx_dmo)))
        b_perc = normalize(np.mean([cen(rng_f[f].choice(idx_f[f], len(idx_f[f]))) for f in validas], axis=0, keepdims=True))[0]
        boot.append(float(b_dmo @ b_perc))
    Zd = Z[idx_dmo]
    por_fuente = {}
    for f, ids in idx_f.items():
        mx = (Z[ids] @ Zd.T).max(1)
        por_fuente[str(f)] = {"ias": round(float(c_dmo @ c_f[f]), 3),
                              "similitud_max_mediana": round(float(np.median(mx)), 3),
                              "n": int(len(ids))}
    return {"ias": round(ias, 3), "ic95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
            "ias_agregado": round(float(c_dmo @ cen(np.concatenate(list(idx_f.values())))), 3),
            "por_fuente": por_fuente}


def tabla_por_fuente(res_pos, res_neg, res_conj, sentimiento, similitud, dmo):
    filas = []
    for f, s in sentimiento["por_fuente"].items():
        fila = {"fuente": f, "es_dmo": f == dmo, "pct_positivo": s["pct_positivo"], "n": s["n"]}
        for nombre, res in (("temas_principales", res_conj), ("temas_positivos", res_pos), ("temas_negativos", res_neg)):
            if res and res.get("tipo") == "topicos" and f in res["por_fuente"]:
                pct = res["por_fuente"][f]["prop"]
                top = sorted(pct.items(), key=lambda x: -x[1])[:2]
                fila[nombre] = [{"etiqueta": res["topicos"][t]["etiqueta"], "pct": p} for t, p in top]
        fila["ias"] = similitud["por_fuente"].get(f, {}).get("ias") if f != dmo else None
        filas.append(fila)
    return filas


def resumen_brechas(comp_temas, sent, sim, dmo):
    """Frases para la DMO. Sólo describe los números ya calculados."""
    temas = comp_temas["temas"] if comp_temas else []
    frases = []
    if comp_temas is None:
        frases.append("Hay muy pocos comentarios para comparar temas; se reportan las palabras más frecuentes.")
    proy = sorted([t for t in temas if t["clase"] == "Proyectado, poco percibido"], key=lambda t: -t["brecha_pp"])
    perc = sorted([t for t in temas if t["clase"] == "Percibido, poco proyectado"], key=lambda t: t["brecha_pp"])
    coin = sorted([t for t in temas if t["clase"] == "Coincidencia"], key=lambda t: -(t["pct_dmo"] + t["pct_percibida"]))
    for t in proy[:3]:
        frases.append(f"El tema «{t['etiqueta']}» ocupa {t['pct_dmo']:.0f} % del contenido de la DMO y sólo "
                      f"{t['pct_percibida']:.0f} % del contenido de los visitantes.")
    for t in perc[:3]:
        neg = f"; {t['pct_negativo_percibida']:.0f} % de esos comentarios son negativos" if t["pct_negativo_percibida"] is not None else ""
        frases.append(f"El tema «{t['etiqueta']}» ocupa {t['pct_percibida']:.0f} % del contenido de los visitantes "
                      f"y {t['pct_dmo']:.0f} % del de la DMO{neg}.")
    for t in coin[:2]:
        enfoque = ""
        if t.get("palabras_dmo") and t.get("palabras_percibida"):
            enfoque = (f" La DMO lo aborda con «{', '.join(t['palabras_dmo'][:4])}» y los visitantes con "
                       f"«{', '.join(t['palabras_percibida'][:4])}»")
            enfoque += (": pesan igual, pero no es la misma conversación." if (t.get("palabras_compartidas") or 0) <= 1 else ".")
        frases.append(f"Coinciden en «{t['etiqueta']}»: {t['pct_dmo']:.0f} % del contenido de la DMO y "
                      f"{t['pct_percibida']:.0f} % del de los visitantes.{enfoque}")
    if sent.get("pct_positivo_dmo") is not None and sent.get("pct_positivo_percibida") is not None:
        frases.append(f"Tono: {sent['pct_positivo_dmo']:.0f} % de los textos de la DMO son positivos frente a "
                      f"{sent['pct_positivo_percibida']:.0f} % en promedio de las fuentes de visitantes.")
    frases.append(f"Alineación semántica global: {sim['ias']:.2f} (de 0 a 1; intervalo 95 % {sim['ic95'][0]:.2f}–{sim['ic95'][1]:.2f}).")
    return frases


def _bootstrap_diferencia(A, B, semilla, n_boot=500):
    """IC 95 % de mean(A) − mean(B) por columna, remuestreando filas de cada grupo."""
    rng = np.random.default_rng(semilla)
    boot = np.empty((n_boot, A.shape[1]))
    for b in range(n_boot):
        boot[b] = 100 * (A[rng.integers(0, len(A), len(A))].mean(0) - B[rng.integers(0, len(B), len(B))].mean(0))
    return np.percentile(boot, [2.5, 97.5], axis=0)


def comparar_por_fuente(normales, Wn, Z, terminos_tema, etiquetas, dmo, umbral_pp, col_texto, formas, bm,
                        palabras_fuente=None, semilla=42, minimo=0):
    """Comparación DMO frente a CADA fuente percibida, por separado.

    Cuantitativa: peso de cada tema en la DMO y en la fuente con IC 95 % bootstrap de la diferencia,
    tono (con chi cuadrada), parecido del contenido (coseno de centroides LSA con IC) y coincidencia de
    agenda (1 − Jensen-Shannon). Cualitativa: con qué palabras aborda cada lado cada tema, palabras que
    distinguen a la fuente de la DMO y viceversa (log-odds) y los comentarios de cada lado que mejor
    representan cada tema, recuperados con BM25 usando las palabras del tema como consulta.
    `normales` está en el mismo orden que las filas de `Wn` y `Z`.
    """
    from collections import Counter
    from .outliers import log_odds
    fuentes = normales.fuente.to_numpy()
    asign = normales.topico_conjunto.fillna(-1).to_numpy().astype(int)
    textos = normales[col_texto].astype(str).to_numpy()
    k = Wn.shape[1]
    i_dmo = np.flatnonzero(fuentes == dmo)
    if not len(i_dmo):
        return {}
    cen = lambda ids: normalize(Z[ids].mean(0, keepdims=True))[0]
    c_dmo = cen(i_dmo)
    p_dmo = 100 * Wn[i_dmo].mean(0)
    cont_dmo = Counter(w for t in normales.lemas.to_numpy()[i_dmo] for w in t.split())
    pos_dmo = float((normales.sentimiento.to_numpy()[i_dmo] == "positivo").mean() * 100)
    vista = lambda w: " ".join(formas.get(x, x) for x in w.split())
    rng = np.random.default_rng(semilla)

    largo = normales.n_tokens.to_numpy() if "n_tokens" in normales else np.full(len(normales), 99)

    def ejemplos(t, mascara_fuente, n=2):
        # primero comentarios del tema con algo de contenido (BM25 favorece los muy cortos), luego sin ese filtro
        consulta = " ".join(terminos_tema[t])
        for m in (mascara_fuente & (asign == t) & (largo >= 6), mascara_fuente & (asign == t), mascara_fuente & (largo >= 6)):
            idx = bm.mejores(consulta, k=n, mascara=m)
            if idx:
                return [str(textos[i])[:400] for i in idx]
        return []

    salida = {}
    for f in [x for x in pd_unicos(fuentes) if x != dmo]:
        i_f = np.flatnonzero(fuentes == f)
        if not len(i_f):
            continue
        p_f = 100 * Wn[i_f].mean(0)
        ic = _bootstrap_diferencia(Wn[i_dmo], Wn[i_f], semilla) if len(i_f) >= 2 and len(i_dmo) >= 2 else None
        temas = []
        for t in range(k):
            brecha = float(p_dmo[t] - p_f[t])
            lo, hi = (float(ic[0, t]), float(ic[1, t])) if ic is not None else (brecha, brecha)
            firme = lo > 0 or hi < 0
            if brecha >= umbral_pp and firme:
                clase = "Proyectado, poco percibido"
            elif brecha <= -umbral_pp and firme:
                clase = "Percibido, poco proyectado"
            elif min(p_dmo[t], p_f[t]) >= 100 / (2 * k):
                clase = "Coincidencia"
            else:
                clase = "Marginal en ambos"
            pal = (palabras_fuente or {}).get(t, {})
            temas.append({
                "id": t, "etiqueta": etiquetas[t], "pct_dmo": round(float(p_dmo[t]), 2), "pct_fuente": round(float(p_f[t]), 2),
                "brecha_pp": round(brecha, 2), "brecha_ic95": [round(lo, 2), round(hi, 2)], "clase": clase,
                "palabras_dmo": pal.get(dmo, []), "palabras_fuente": pal.get(f, []),
                "palabras_compartidas": len(set(pal.get(dmo, [])) & set(pal.get(f, []))) if pal else None,
                "ejemplos_dmo": ejemplos(t, fuentes == dmo), "ejemplos_fuente": ejemplos(t, fuentes == f),
            })
        # tono
        s_f = normales.sentimiento.to_numpy()[i_f]
        pos_f = float((s_f == "positivo").mean() * 100)
        tabla = np.array([[np.sum(normales.sentimiento.to_numpy()[i_dmo] == s) for s in ("positivo", "negativo")],
                          [np.sum(s_f == s) for s in ("positivo", "negativo")]])
        prueba = None
        if tabla.sum(1).min() > 0 and tabla.sum(0).min() > 0:
            chi2, pv, *_ = chi2_contingency(tabla)
            prueba = {"chi2": round(float(chi2), 2), "p_valor": float(f"{pv:.3g}")}
        # parecido del contenido y coincidencia de agenda
        c_f = cen(i_f)
        rng = np.random.default_rng([semilla, len(i_dmo), len(i_f)])
        boot = [float(cen(rng.choice(i_dmo, len(i_dmo))) @ cen(rng.choice(i_f, len(i_f)))) for _ in range(200)]
        p, q = p_dmo / max(p_dmo.sum(), 1e-9), p_f / max(p_f.sum(), 1e-9)
        jsd = float(jensenshannon(p, q, base=2) ** 2)
        cont_f = Counter(w for t in normales.lemas.to_numpy()[i_f] for w in t.split())
        salida[str(f)] = {
            "n": int(len(i_f)), "n_dmo": int(len(i_dmo)), "pocos": bool(len(i_f) < minimo),
            "temas": temas,
            "tono": {"pct_positivo_dmo": round(pos_dmo, 2), "pct_positivo_fuente": round(pos_f, 2), "prueba_chi2": prueba},
            "parecido": {"valor": round(float(c_dmo @ c_f), 3),
                         "ic95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)]},
            "coincidencia_agenda": round(1 - jsd, 4),
            "palabras_de_la_fuente": [(vista(w), z) for w, z in log_odds(cont_f, cont_dmo, k=12, min_freq=3)],
            "palabras_de_la_dmo": [(vista(w), z) for w, z in log_odds(cont_dmo, cont_f, k=12, min_freq=3)],
        }
        salida[str(f)]["resumen"] = resumen_fuente(f, salida[str(f)])
    return salida


def pd_unicos(valores):
    vistos = []
    for v in valores:
        if v not in vistos:
            vistos.append(v)
    return sorted(vistos)


def resumen_fuente(f, c):
    """Frases cuantitativas y cualitativas de la DMO frente a una fuente."""
    temas = c["temas"]
    frases = []
    mas_f = sorted([t for t in temas if t["clase"] == "Percibido, poco proyectado"], key=lambda t: t["brecha_pp"])[:2]
    mas_d = sorted([t for t in temas if t["clase"] == "Proyectado, poco percibido"], key=lambda t: -t["brecha_pp"])[:2]
    coin = sorted([t for t in temas if t["clase"] == "Coincidencia"], key=lambda t: -(t["pct_dmo"] + t["pct_fuente"]))[:1]
    for t in mas_d:
        frases.append(f"La DMO dedica {t['pct_dmo']:.0f} % de su contenido a «{t['etiqueta']}»; {f} sólo {t['pct_fuente']:.0f} %.")
    for t in mas_f:
        frases.append(f"{f} dedica {t['pct_fuente']:.0f} % a «{t['etiqueta']}», frente a {t['pct_dmo']:.0f} % de la DMO.")
    for t in coin:
        modo = ""
        if t["palabras_dmo"] and t["palabras_fuente"]:
            modo = (f" La DMO usa «{', '.join(t['palabras_dmo'][:3])}» y {f} «{', '.join(t['palabras_fuente'][:3])}»"
                    + (": no es la misma conversación." if (t["palabras_compartidas"] or 0) <= 1 else "."))
        frases.append(f"Coinciden en «{t['etiqueta']}» ({t['pct_dmo']:.0f} % y {t['pct_fuente']:.0f} %).{modo}")
    to = c["tono"]
    frases.append(f"Tono positivo: DMO {to['pct_positivo_dmo']:.0f} %, {f} {to['pct_positivo_fuente']:.0f} %.")
    if c["palabras_de_la_fuente"]:
        frases.append(f"Lo que más distingue a {f} de la DMO: " + ", ".join(w for w, _ in c["palabras_de_la_fuente"][:6]) + ".")
    frases.append(f"Parecido del contenido con la DMO: {c['parecido']['valor']:.2f} (de 0 a 1).")
    return frases
