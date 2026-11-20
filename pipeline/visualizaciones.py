"""Paso 7. Proyección 2D y gráficas interactivas (Plotly) con codificación redundante color + forma."""
import numpy as np
from matplotlib import colormaps
from matplotlib.colors import to_hex
from sklearn.manifold import TSNE

SIMBOLOS = ["square", "circle", "diamond", "triangle-up", "x", "triangle-down", "star", "cross", "pentagon", "hexagon"]


# Okabe-Ito: paleta categórica pensada para daltonismo (Okabe e Ito, 2008); el amarillo va al final
# porque contrasta poco sobre blanco.
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#000000", "#F0E442"]


def escala_continua(paleta):
    """Nombre de una escala continua para mapas de calor (Okabe-Ito es categórica: se usa cividis)."""
    return paleta if paleta in {"viridis", "cividis", "plasma", "inferno", "magma"} else "cividis"


# Para más de 8 categorías (p. ej. 15 temas) se agrega la paleta «muted» de Paul Tol, también pensada para
# daltonismo; más allá de 17 categorías ningún conjunto de colores se distingue bien y se usa cividis.
TOL_MUTED = ["#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE", "#882255", "#44AA99", "#999933", "#AA4499"]


def colores(paleta, n, inicio=0.0, fin=0.9):
    if paleta in ("okabe_ito", "okabe-ito"):
        if n <= len(OKABE_ITO) + len(TOL_MUTED):
            return (OKABE_ITO + TOL_MUTED)[:n]
        paleta = "cividis"
    cmap = colormaps[paleta]
    if n == 1:
        return [to_hex(cmap(inicio))]
    return [to_hex(cmap(inicio + (fin - inicio) * i / (n - 1))) for i in range(n)]


def simbolos_fuente(fuentes, dmo):
    """La DMO siempre es el cuadrado; las demás fuentes toman las formas siguientes."""
    otras = [f for f in sorted(fuentes) if f != dmo]
    m = {dmo: SIMBOLOS[0]}
    m.update({f: SIMBOLOS[1 + i % (len(SIMBOLOS) - 1)] for i, f in enumerate(otras)})
    return m


def proyectar_2d(df, Z, max_por_fuente, semilla):
    """t-SNE sobre los vectores LSA de una muestra estratificada de comentarios no atípicos."""
    df = df.copy()
    df["x"], df["y"], df["en_mapa"] = np.nan, np.nan, False
    idx = []
    for f, g in df[~df.outlier].groupby("fuente"):
        ids = g.index.to_numpy()
        if len(ids) > max_por_fuente:
            ids = np.random.default_rng([semilla, len(ids)]).choice(ids, max_por_fuente, replace=False)
        idx.extend(ids.tolist())
    idx = np.sort(np.array(idx))
    if len(idx) < 10:
        return df
    perp = min(30, max(5, (len(idx) - 1) // 3))
    xy = TSNE(2, perplexity=perp, init="pca", random_state=semilla, max_iter=750).fit_transform(Z[idx, :50])
    df.loc[idx, "x"], df.loc[idx, "y"], df.loc[idx, "en_mapa"] = xy[:, 0], xy[:, 1], True
    return df


def _hover(df, col_texto):
    return [f"<b>{f}</b> · {s or ''}<br>{str(t)[:140].replace('<', '&lt;')}…" for f, s, t in zip(df.fuente, df.sentimiento, df[col_texto])]


def figuras(df, res, col_texto, dmo, paleta, titulo):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    figs = {}
    mapa = df[df.en_mapa]
    fuentes = sorted(df.fuente.unique())
    simb = simbolos_fuente(fuentes, dmo)
    col_f = dict(zip([dmo] + [f for f in fuentes if f != dmo], colores(paleta, len(fuentes))))

    # 1. Mapa por fuente: color + forma = fuente
    fig = go.Figure()
    for f in [x for x in fuentes if x != dmo] + [dmo]:
        g = mapa[mapa.fuente == f]
        fig.add_trace(go.Scattergl(x=g.x.round(3), y=g.y.round(3), mode="markers", name=("DMO · " if f == dmo else "") + f,
                                   marker=dict(color=col_f[f], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.75,
                                               line=dict(width=0.5, color="white")),
                                   text=_hover(g, col_texto), hoverinfo="text"))
    fig.update_layout(title=f"{titulo}: comentarios por fuente", xaxis=dict(visible=False), yaxis=dict(visible=False),
                      template="plotly_white", height=620, legend=dict(orientation="h", y=-0.05))
    figs["mapa_fuentes"] = fig

    # 2. Mapa por tópico (positivos y negativos por separado): color = tópico, forma = fuente
    fig = make_subplots(1, 2, subplot_titles=("Comentarios positivos", "Comentarios negativos"), horizontal_spacing=0.03)
    for c, s in enumerate(["positivo", "negativo"], start=1):
        r = res["topicos"][s]
        g = mapa[mapa.sentimiento == s]
        if r.get("tipo") != "topicos" or g.empty:
            continue
        cols = colores(paleta, r["k"])
        for t in range(r["k"]):
            gt = g[g.topico_particion == t]
            primero = True
            for f in fuentes:
                gf = gt[gt.fuente == f]
                if gf.empty:
                    continue
                mostrar, primero = primero, False
                fig.add_trace(go.Scattergl(x=gf.x.round(3), y=gf.y.round(3), mode="markers", legendgroup=f"{s}{t}",
                                           name=f"{s[:3]}. T{t + 1} {r['topicos'][t]['etiqueta']}", showlegend=mostrar,
                                           marker=dict(color=cols[t], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.8,
                                                       line=dict(width=0.4, color="white")),
                                           text=_hover(gf, col_texto), hoverinfo="text"), 1, c)
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    fig.update_layout(title=f"{titulo}: tópicos por sentimiento (color = tópico, forma = fuente)", template="plotly_white",
                      height=640, legend=dict(font=dict(size=10)))
    figs["mapa_topicos"] = fig

    # 3. Comparativo de tópicos y sentimiento DMO vs percibida
    comp = res["comparacion"]["temas"]
    if comp:
        cp = colores(paleta, 2, 0.15, 0.75)
        etiquetas = [f"T{t['id'] + 1} {t['etiqueta']}" for t in comp]
        fig = make_subplots(1, 2, column_widths=[0.62, 0.38], subplot_titles=("Distribución de tópicos (%)", "Comentarios positivos (%)"))
        fig.add_trace(go.Bar(y=etiquetas, x=[t["pct_dmo"] for t in comp], orientation="h", name="DMO", marker_color=cp[0]), 1, 1)
        fig.add_trace(go.Bar(y=etiquetas, x=[t["pct_percibida"] for t in comp], orientation="h", name="Percibida (promedio de fuentes)",
                             marker=dict(color=cp[1], pattern=dict(shape="/"))), 1, 1)
        sp = res["comparacion"]["sentimiento"]["por_fuente"]
        orden = [dmo] + [f for f in sp if f != dmo]
        fig.add_trace(go.Bar(y=orden, x=[sp[f]["pct_positivo"] for f in orden], orientation="h", showlegend=False,
                             marker=dict(color=[col_f[f] for f in orden]), text=[f"{sp[f]['pct_positivo']:.0f} %" for f in orden],
                             textposition="outside"), 1, 2)
        fig.update_layout(barmode="group", template="plotly_white", height=max(420, 34 * len(comp) + 160),
                          title=f"{titulo}: DMO frente a imagen percibida", legend=dict(orientation="h", y=-0.12))
        fig.update_yaxes(autorange="reversed", row=1, col=1)
        fig.update_xaxes(range=[0, 110], row=1, col=2)
        figs["comparativo"] = fig

    # 4. Concepto precio / valor / costo
    conc = res["concepto"]
    g = df[~df.outlier]
    fig = go.Figure()
    for f in [x for x in fuentes if x != dmo] + [dmo]:
        gf = g[g.fuente == f]
        fig.add_trace(go.Scattergl(x=gf.sim_concepto.round(4), y=gf.polaridad.round(4), mode="markers", name=("DMO · " if f == dmo else "") + f,
                                   marker=dict(color=col_f[f], symbol=simb[f], size=8 if f == dmo else 5, opacity=0.6),
                                   text=_hover(gf, col_texto), hoverinfo="text"))
    fig.add_vline(x=conc["umbral_similitud"], line_dash="dot", annotation_text=f"umbral (P{conc['percentil']})")
    fig.update_layout(title=f"{titulo}: relación de cada comentario con «{conc['consulta']}»", template="plotly_white", height=560,
                      xaxis_title="Similitud con el concepto", yaxis_title="Polaridad (−1 negativa, +1 positiva)",
                      legend=dict(orientation="h", y=-0.15))
    figs["concepto"] = fig
    return figs
