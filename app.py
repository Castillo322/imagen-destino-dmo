"""Tablero: imagen proyectada por la DMO frente a la imagen percibida por los visitantes.

Dos modos (barra lateral):
- «Subir mis archivos»: dos o más archivos, uno por fuente (csv, tsv, txt, xlsx, xls, json, jsonl o parquet). Se
  elige cuál es la DMO, el tablero corre los 8 pasos del análisis y muestra los resultados de esos archivos.
- «Ejemplo: Ciudad de México»: muestra los resultados que generó analizador.py en salidas/.
Uso:  streamlit run app.py
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline import lectura
from pipeline.config import CONCEPTO_POR_IDIOMA, K_TOPICOS, PALETAS_ACCESIBLES
from pipeline.visualizaciones import colores, escala_continua, simbolos_fuente

st.set_page_config(page_title="Imagen del destino", page_icon="🗺️", layout="wide")

CARPETA = Path(__file__).parent / "salidas"
IDIOMAS = {"es": "Español", "en": "Inglés", "fr": "Francés", "pt": "Portugués", "it": "Italiano", "de": "Alemán"}
NOMBRES = {"tripadvisor": "TripAdvisor", "instagram": "Instagram", "reddit": "Reddit", "sectur": "Sectur"}
NOMBRE_PALETA = {"okabe_ito": "Okabe-Ito", "viridis": "Viridis", "cividis": "Cividis",
                 "plasma": "Plasma", "inferno": "Inferno", "magma": "Magma"}
CLASES = {
    "Proyectado, poco percibido": ("La DMO lo destaca más", "▲"),
    "Percibido, poco proyectado": ("Los visitantes lo mencionan más", "▼"),
    "Coincidencia": ("Coinciden", "●"),
    "Marginal en ambos": ("Poco presente en ambos", "○"),
}
FORMATOS = ["csv", "tsv", "txt", "xlsx", "xls", "json", "jsonl", "parquet", "gz"]
COLS_D = ["id_registro", "fuente", "texto", "lemas", "outlier", "sentimiento", "polaridad", "topico_conjunto", "topico_particion",
          "sim_concepto", "bm25_concepto", "ligado_concepto", "x", "y", "en_mapa"]
PLANTILLA = "plotly_white"


# ---------------------------------------------------------------- datos
@st.cache_data(show_spinner=False)
def corridas():
    salida = {}
    tam = {}
    for p in CARPETA.glob("*/resultados.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        par = r["parametros"]
        salida[p.parent.name] = f"{IDIOMAS.get(par['idioma'], par['idioma'])} · {par['titulo']}"
        tam[p.parent.name] = r["conteos"].get(par["etiqueta_dmo"], {}).get("analizados", 0)
    # primero el corpus en que la DMO tiene más textos
    return dict(sorted(salida.items(), key=lambda kv: -tam[kv[0]]))


@st.cache_data(show_spinner=False)
def cargar(carpeta):
    r = json.loads((CARPETA / carpeta / "resultados.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(CARPETA / carpeta / "corpus_procesado.parquet")
    return r, df[[c for c in COLS_D if c in df.columns]]


@st.cache_data(show_spinner=False, max_entries=24)
def leer_subido(datos: bytes, nombre_archivo: str):
    return lectura.leer_archivo(datos, nombre_archivo)


@st.cache_data(show_spinner=False)
def idioma_sugerido(muestras: tuple) -> str:
    from langdetect import DetectorFactory, detect
    DetectorFactory.seed = 0
    cuenta = Counter()
    for t in muestras:
        try:
            cuenta[detect(t)] += 1
        except Exception:
            pass
    return cuenta.most_common(1)[0][0] if cuenta else "es"


@st.cache_resource(show_spinner=False, max_entries=6)
def indice_bm25(clave_corpus, _lemas):
    from pipeline.bm25 import BM25
    return BM25(_lemas)


def consulta_lemas(texto, idioma, excluir):
    from pipeline.preprocesamiento import Preprocesador, limpiar
    try:
        return " ".join(Preprocesador(idioma, excluir).tokens(limpiar(texto)))
    except Exception:
        return limpiar(texto)


def nombre(f, dmo):
    base = NOMBRES.get(f, str(f).replace("_", " "))
    base = base[:1].upper() + base[1:]
    return f"{base} (DMO)" if f == dmo else base


def corto(t, n=220):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def hover(textos, fuentes, tonos, dmo):
    return [f"<b>{nombre(f, dmo)}</b> · {t or 'sin tono'}<br>{corto(x, 160).replace('<', '&lt;')}"
            for x, f, t in zip(textos, fuentes, tonos)]


def cita(texto, fuente=None, dmo=None):
    pie = f"<div style='font-size:0.8rem;opacity:.7;margin-top:4px'>— {nombre(fuente, dmo)}</div>" if fuente else ""
    seguro = corto(texto, 420).replace("<", "&lt;")
    st.markdown(f"<div style='border-left:3px solid #8a8a8a;padding:6px 12px;margin:6px 0;font-size:0.92rem'>"
                f"{seguro}{pie}</div>", unsafe_allow_html=True)


def lista_palabras(pares, n=12):
    return " · ".join(str(p[0]) for p in pares[:n])


# ---------------------------------------------------------------- carga de archivos
def panel_carga(paleta):
    """Archivos del usuario -> configuración por fuente -> análisis completo. Guarda el resultado en la sesión."""
    from pipeline.analisis import ErrorDeDatos, ejecutar, html_reporte
    st.markdown("Sube **dos o más archivos**: uno con lo que publica la **DMO** (imagen proyectada) y uno o más con lo que "
                "publican los **visitantes** (imagen percibida). Cada archivo es una fuente. Formatos: CSV, TSV, TXT, "
                "Excel (xlsx, xls), JSON, JSONL y Parquet, también comprimidos con .gz. Si tienes todo en un solo archivo con una columna que indica la "
                "fuente, súbelo solo y elige esa columna.")
    subidos = st.file_uploader("Archivos", type=FORMATOS, accept_multiple_files=True, key="subidos")
    if not subidos:
        return
    tablas = {}
    for s in subidos:
        try:
            tablas[s.name] = leer_subido(s.getvalue(), s.name)
        except Exception as e:
            st.error(f"No pude leer «{s.name}»: {e}")
    if not tablas:
        return
    partes, configs = [], []
    if len(tablas) == 1:
        nom, t = next(iter(tablas.items()))
        st.markdown(f"**{nom}** · {len(t):,} filas · columnas: {', '.join(map(str, t.columns))}")
        cand_f = [c for c in t.columns if 2 <= t[c].nunique() <= 30]
        if not cand_f:
            st.warning("Con un solo archivo se necesita una columna que diga de qué fuente es cada comentario. "
                       "Sube al menos dos archivos (uno por fuente).")
            return
        c1, c2 = st.columns(2)
        col_f = c1.selectbox("Columna que indica la fuente", cand_f)
        cand_t = lectura.columnas_de_texto(t) or list(t.columns)
        ctex = c2.multiselect("Columnas de texto", cand_t, default=[c for c in lectura.sugerir_columnas(t)[0] if c in cand_t
                                                                         and c != col_f][:1] or cand_t[:1])
        if not ctex:
            st.warning("Elige al menos una columna de texto.")
            return
        for f, g in t.groupby(col_f):
            partes.append(lectura.armar_fuente(g, ctex, str(f)))
    else:
        st.markdown("##### Cada fuente")
        cols = st.columns(min(len(tablas), 4))
        for i, (nom, t) in enumerate(tablas.items()):
            with cols[i % len(cols)].container(border=True):
                st.markdown(f"**{nom}**  \n{len(t):,} filas")
                sug_t, sug_l = lectura.sugerir_columnas(t)
                cand = lectura.columnas_de_texto(t) or [str(c) for c in t.columns]
                nf = st.text_input("Nombre de la fuente", lectura.nombre_de_archivo(nom), key=f"nom_{nom}").strip()
                ctex = st.multiselect("Columnas de texto", cand, default=[c for c in sug_t if c in cand], key=f"col_{nom}",
                                      help="Si eliges varias, se unen en un solo comentario (por ejemplo, título y cuerpo).")
                ops = ["(ninguna)"] + cand
                clis = st.selectbox("Columna con varios comentarios por celda", ops,
                                    index=ops.index(sug_l) if sug_l in ops else 0, key=f"lis_{nom}",
                                    help="Por ejemplo, las respuestas de un hilo de foro unidas con « - »: cada una se "
                                         "analiza como un comentario aparte.")
                sep = st.text_input("Separador de esos comentarios", " - ", key=f"sep_{nom}") if clis != "(ninguna)" else " - "
                with st.popover("Vista previa"):
                    st.dataframe(t.head(8), hide_index=True)
                configs.append((nom, nf, ctex, None if clis == "(ninguna)" else clis, sep))
        nombres_f = [c[1] for c in configs]
        if any(not n for n in nombres_f) or len(set(nombres_f)) < len(nombres_f):
            st.error("Cada fuente necesita un nombre distinto.")
            return
        for nom, nf, ctex, clis, sep in configs:
            try:
                partes.append(lectura.armar_fuente(tablas[nom], ctex, nf, clis, sep))
            except ValueError as e:
                st.error(str(e))
                return
    df = pd.concat(partes, ignore_index=True)
    fuentes_d = list(dict.fromkeys(df.fuente))
    if len(fuentes_d) < 2:
        st.warning("Se necesitan al menos dos fuentes para comparar.")
        return
    st.caption("Comentarios por fuente: " + " · ".join(f"{f}: {n:,}" for f, n in df.fuente.value_counts().items()))
    dmo = st.radio("¿Cuál es la DMO (imagen proyectada)?", fuentes_d, horizontal=True,
                   index=fuentes_d.index(lectura.sugerir_dmo(fuentes_d)))
    muestra = tuple(df.groupby("fuente").head(80).texto.astype(str).str[:300])
    sug = idioma_sugerido(muestra)
    lista_idiomas = list(IDIOMAS) + ([sug] if sug not in IDIOMAS else [])
    c1, c2, c3 = st.columns(3)
    idioma = c1.selectbox("Idioma a analizar", lista_idiomas, index=lista_idiomas.index(sug), format_func=lambda x: IDIOMAS.get(x, x),
                          help="Se propone el idioma más frecuente en tus archivos. Los comentarios en otros idiomas se dejan "
                               "fuera; para analizarlos, vuelve a correr con ese idioma.")
    titulo = c2.text_input("Título", "Imagen del destino")
    excluir = c3.text_input("Palabras a ignorar (separadas por coma)", "",
                            help="Por ejemplo, el nombre del destino: aparece en todas partes y no ayuda a distinguir temas.")
    with st.expander("Opciones avanzadas"):
        a1, a2, a3 = st.columns(3)
        k_fijo = a1.number_input("Número de temas (0 = lo elige el análisis)", 0, 30, 0,
                                 help=f"Por defecto se prueban de {K_TOPICOS.start} a {K_TOPICOS.stop - 1} temas y se queda el "
                                      "número que da temas más coherentes y menos repetidos.")
        contam = a2.slider("% de comentarios atípicos a separar", 0.0, 10.0, 3.0, 0.5)
        concepto = a3.text_input("Idea a rastrear", CONCEPTO_POR_IDIOMA.get(idioma, CONCEPTO_POR_IDIOMA["en"]))
    if not st.button("Analizar", type="primary"):
        return
    barra = st.progress(0.0, "Preparando…")
    try:
        resultado = ejecutar(df, "texto", "fuente", dmo, idioma, titulo, paleta, excluir=excluir.split(","),
                             contaminacion=contam / 100, texto_concepto=concepto.strip() or None, k_topicos=int(k_fijo) or None,
                             progreso=lambda f, m: barra.progress(min(float(f), 1.0), m),
                             origen=", ".join(tablas))
    except (ErrorDeDatos, ValueError) as e:
        barra.empty()
        st.error(str(e))
        return
    firma = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()
                           + json.dumps([dmo, idioma, titulo, excluir, int(k_fijo), contam, concepto]).encode()).hexdigest()[:16]
    barra.progress(1.0, "Preparando el reporte descargable…")
    st.session_state["subido"] = {"firma": firma, "res": resultado["res"],
                                  "df": resultado["df"][[c for c in COLS_D if c in resultado["df"].columns]],
                                  "html": html_reporte(resultado)}
    barra.empty()
    st.rerun()


# ---------------------------------------------------------------- barra lateral y datos
with st.sidebar:
    st.markdown("### Imagen del destino")
    modo = st.radio("Datos", ["Subir mis archivos", "Ejemplo: Ciudad de México"],
                    help="Sube tus propios archivos o mira el análisis ya hecho de la Ciudad de México.")
    paleta = st.selectbox("Paleta de colores", PALETAS_ACCESIBLES, format_func=lambda p: NOMBRE_PALETA.get(p, p),
                          help="Todas son legibles con daltonismo. Okabe-Ito usa colores muy distintos entre sí; las demás "
                               "también se distinguen en escala de grises.")

HTML_REPORTE = None
if modo == "Subir mis archivos":
    st.title("Imagen del destino: DMO frente a visitantes")
    hay = "subido" in st.session_state
    with st.expander("Archivos y configuración" + (" (cambiar)" if hay else ""), expanded=not hay):
        panel_carga(paleta)
    if "subido" not in st.session_state:
        st.stop()
    S = st.session_state["subido"]
    R, D, clave, HTML_REPORTE = S["res"], S["df"], S["firma"], S["html"]
else:
    opciones = corridas()
    if not opciones:
        st.error("No hay resultados de ejemplo. Corre primero `python analizador.py ...` (ver README) o sube tus archivos.")
        st.stop()
    with st.sidebar:
        clave = st.selectbox("Corpus", list(opciones), format_func=opciones.get)
    R, D = cargar(clave)
    ruta_html = CARPETA / clave / "reporte.html"
    if ruta_html.exists():
        HTML_REPORTE = ruta_html.read_text(encoding="utf-8")
    elif ruta_html.with_suffix(".html.gz").exists():  # en el repositorio va comprimido
        import gzip
        HTML_REPORTE = gzip.decompress(ruta_html.with_suffix(".html.gz").read_bytes()).decode("utf-8")

P = R["parametros"]
dmo = P["etiqueta_dmo"]
fuentes = [dmo] + sorted(f for f in R["conteos"] if f != dmo)
simb = simbolos_fuente(fuentes, dmo)
col_f = dict(zip(fuentes, colores(paleta, len(fuentes))))
forma_txt = {"square": "■", "circle": "●", "diamond": "◆", "triangle-up": "▲", "x": "✕", "triangle-down": "▼"}
with st.sidebar:
    st.caption("Cada fuente tiene siempre el mismo color y la misma forma en todas las gráficas.")
    for f in fuentes:
        st.markdown(f"<span style='color:{col_f[f]};font-size:1.2rem'>{forma_txt.get(simb[f], '●')}</span> {nombre(f, dmo)}",
                    unsafe_allow_html=True)
    if HTML_REPORTE:
        st.download_button("Descargar reporte (HTML)", HTML_REPORTE.encode("utf-8"), f"reporte_{P['idioma']}.html", "text/html")

COMP = R["comparacion"]
TEMAS = COMP["temas"]
CONJ = R["topicos"]["conjunto"]
SENT = COMP["sentimiento"]
SIM = COMP["similitud"]
PF_IND = COMP.get("dmo_vs_cada_fuente") or {}
perc_prom = COMP.get("temas_resumen", {}).get("fuentes_en_promedio") or [f for f in fuentes if f != dmo]
c2 = colores(paleta, 2, 0.15, 0.7)
COL_DMO, COL_VIS = c2[0], c2[1]
if paleta == "okabe_ito":  # el promedio de visitantes en gris para no confundirlo con una fuente
    COL_DMO, COL_VIS = col_f[dmo], "#5F5F5F"
ESCALA = escala_continua(paleta)

if modo != "Subir mis archivos":
    st.title(P["titulo"])
else:
    st.subheader(P["titulo"])
st.caption(f"Comentarios en {IDIOMAS.get(P['idioma'], P['idioma']).lower()} · imagen proyectada por la DMO "
           f"({nombre(dmo, None)}) frente a lo que publican los visitantes en " +
           ", ".join(nombre(f, dmo) for f in fuentes if f != dmo))
for a in R.get("advertencias", []):
    st.info(a, icon="ℹ️")

pestanas = st.tabs(["Resumen", "Proyectado vs. percibido", "DMO vs. cada fuente", "Lo que gusta y lo que no", "Por fuente",
                    "Explorar y buscar", "Precio, valor y costo", "Comentarios atípicos"])


# ---------------------------------------------------------------- gráficas comunes
def fig_comparativo(temas, altura=None, campo="pct_percibida", nombre_vis="Visitantes (promedio de fuentes)", color_vis=None,
                    color_dmo=None):
    orden = sorted(temas, key=lambda t: t["brecha_pp"])
    y = [f"{t['id'] + 1}. {t['etiqueta']}" for t in orden]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=y, x=[t["pct_dmo"] for t in orden], orientation="h", name="DMO", marker_color=color_dmo or COL_DMO,
                         hovertemplate="%{y}<br>DMO: %{x:.1f} %<extra></extra>"))
    fig.add_trace(go.Bar(y=y, x=[t[campo] for t in orden], orientation="h", name=nombre_vis,
                         marker=dict(color=color_vis or COL_VIS, pattern=dict(shape="/", fgcolor="white", size=6)),
                         hovertemplate="%{y}<br>" + nombre_vis + ": %{x:.1f} %<extra></extra>"))
    fig.update_layout(barmode="group", template=PLANTILLA, height=altura or max(380, 30 * len(orden) + 120),
                      margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.04, x=0),
                      xaxis_title="% del contenido dedicado al tema", bargap=0.25)
    return fig


def fig_brechas(temas, lado="los visitantes", color_vis=None, color_dmo=None):
    orden = sorted(temas, key=lambda t: t["brecha_pp"])
    y = [f"{t['id'] + 1}. {t['etiqueta']}" for t in orden]
    x = [t["brecha_pp"] for t in orden]
    lo = [t["brecha_pp"] - t.get("brecha_ic95", [t["brecha_pp"]] * 2)[0] for t in orden]
    hi = [t.get("brecha_ic95", [t["brecha_pp"]] * 2)[1] - t["brecha_pp"] for t in orden]
    col = [(color_dmo or COL_DMO) if v > 0 else (color_vis or COL_VIS) for v in x]
    pat = ["" if v > 0 else "/" for v in x]
    fig = go.Figure(go.Bar(y=y, x=x, orientation="h", marker=dict(color=col, pattern=dict(shape=pat, fgcolor="white", size=6)),
                           error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color="#555", thickness=1.2),
                           customdata=[[CLASES[t["clase"]][0], *t.get("brecha_ic95", [0, 0])] for t in orden],
                           hovertemplate="%{y}<br>Diferencia: %{x:.1f} puntos<br>Rango probable: %{customdata[1]:.1f} a "
                                         "%{customdata[2]:.1f}<br>%{customdata[0]}<extra></extra>"))
    fig.add_vline(x=0, line_color="#333", line_width=1)
    fig.add_annotation(x=1, y=1.06, xref="paper", yref="paper", text="más en la DMO ▶", showarrow=False,
                       xanchor="right", font=dict(size=12))
    fig.add_annotation(x=0, y=1.06, xref="paper", yref="paper", text=f"◀ más en {lado}", showarrow=False,
                       xanchor="left", font=dict(size=12))
    fig.update_layout(template=PLANTILLA, height=max(380, 30 * len(orden) + 120), margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title=f"Diferencia en puntos porcentuales (DMO − {lado})", showlegend=False)
    return fig


def fig_tono_fuentes():
    sp = SENT["por_fuente"]
    orden = [f for f in fuentes if f in sp]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[nombre(f, dmo) for f in orden], y=[sp[f]["pct_positivo"] for f in orden], name="Positivo",
                         marker=dict(color=[col_f[f] for f in orden]), text=[f"{sp[f]['pct_positivo']:.0f} %" for f in orden],
                         textposition="outside", hovertemplate="%{x}: %{y:.1f} % positivos<extra></extra>"))
    fig.update_layout(template=PLANTILLA, height=320, yaxis=dict(range=[0, 108], title="% de comentarios positivos"),
                      margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    return fig


# ---------------------------------------------------------------- 1. Resumen
with pestanas[0]:
    cols = st.columns(len(fuentes))
    for c, f in zip(cols, fuentes):
        n = R["conteos"][f]
        c.metric(nombre(f, dmo), f"{n['analizados']:,}", help=f"Comentarios analizados en este idioma (de {n['total']:,} en total)")
    st.divider()
    a, b, c = st.columns(3)
    pd_, pp_ = SENT.get("pct_positivo_dmo"), SENT.get("pct_positivo_percibida")
    a.metric("Tono positivo · DMO", f"{pd_:.0f} %" if pd_ is not None else "—")
    a.metric("Tono positivo · visitantes", f"{pp_:.0f} %" if pp_ is not None else "—",
             delta=f"{pp_ - pd_:+.0f} puntos frente a la DMO" if None not in (pd_, pp_) else None, delta_color="off")
    b.metric("Parecido del contenido DMO–visitantes", f"{SIM['ias']:.2f}",
             help="0 = hablan de cosas totalmente distintas; 1 = hablan de lo mismo y con las mismas palabras.")
    b.caption(f"Rango probable: {SIM['ic95'][0]:.2f} a {SIM['ic95'][1]:.2f}")
    ct = COMP.get("temas_resumen", {}).get("congruencia_tematica")
    if ct is not None:
        c.metric("Coincidencia de agenda temática", f"{ct:.2f}",
                 help="Qué tanto se reparten igual los temas en la DMO y en los visitantes (0 a 1).")
    cuenta = pd.Series([CLASES[t["clase"]][0] for t in TEMAS]).value_counts()
    c.caption(" · ".join(f"{k}: {v} temas" for k, v in cuenta.items()))

    st.divider()
    k1, k2, k3 = st.columns(3)
    TP, TN = R["topicos"]["positivo"], R["topicos"]["negativo"]
    k1.metric("Temas encontrados", CONJ.get("k", "—") if CONJ.get("tipo") == "topicos" else "—",
              help="Temas comunes con los que se compara la DMO con los visitantes.")
    k2.metric("Temas en comentarios positivos", TP.get("k", "—") if TP.get("tipo") == "topicos" else "—")
    k3.metric("Temas en comentarios negativos", TN.get("k", "—") if TN.get("tipo") == "topicos" else "—")
    if CONJ.get("evaluacion_k"):
        manual = bool(P.get("k_topicos"))
        st.caption("El número de temas lo fijó el usuario." if manual else
                   f"El número de temas lo eligió el análisis: probó de {CONJ['evaluacion_k'][0]['k']} a "
                   f"{CONJ['evaluacion_k'][-1]['k']} y se quedó con el que da temas más coherentes (sus palabras aparecen "
                   "juntas) y menos repetidos entre sí.")
        if not manual and len(CONJ["evaluacion_k"]) > 1:
            with st.expander("¿Cómo se eligió el número de temas?"):
                ev = CONJ["evaluacion_k"]
                fig = go.Figure(go.Scatter(x=[e["k"] for e in ev], y=[e["puntaje"] for e in ev], mode="lines+markers",
                                           line=dict(color=COL_VIS), marker=dict(size=[14 if e["k"] == CONJ["k"] else 7 for e in ev],
                                                                                  color=[COL_DMO if e["k"] == CONJ["k"] else COL_VIS for e in ev]),
                                           error_y=dict(type="data", array=[e.get("puntaje_de", 0) for e in ev], color="#999"),
                                           hovertemplate="%{x} temas<br>calidad: %{y:.3f}<extra></extra>"))
                fig.update_layout(template=PLANTILLA, height=300, margin=dict(l=10, r=10, t=10, b=10),
                                  xaxis_title="Número de temas probado", yaxis_title="Calidad (coherencia × diversidad)")
                st.plotly_chart(fig, width="stretch", key="eleccion_k")
                st.caption("Calidad = coherencia NPMI (Röder et al., 2015) × diversidad de palabras entre temas (Dieng et al., "
                           "2020), promediada en 3 muestras; se elige el mejor valor descontando su variación. El punto grande "
                           "es el elegido.")

    st.subheader("Hallazgos principales")
    izq, der = st.columns([0.45, 0.55])
    with izq:
        for frase in R.get("resumen_brechas", []):
            st.markdown(f"- {frase}")
    with der:
        if TEMAS:
            st.plotly_chart(fig_brechas(TEMAS), width="stretch", key="res_brechas")


# ---------------------------------------------------------------- 2. Proyectado vs percibido
with pestanas[1]:
    if not TEMAS:
        st.warning("No hubo suficientes comentarios para identificar temas comunes.")
    else:
        st.markdown("Los mismos temas se buscaron en el contenido de la DMO y en el de los visitantes. "
                    "Cada barra indica qué parte del contenido de cada lado trata ese tema.")
        izq, der = st.columns(2)
        with izq:
            st.markdown("**Cuánto habla cada lado de cada tema**")
            st.plotly_chart(fig_comparativo(TEMAS), width="stretch", key="comp_barras")
        with der:
            st.markdown("**Diferencia entre lo proyectado y lo percibido**")
            st.plotly_chart(fig_brechas(TEMAS), width="stretch", key="comp_brechas")

        npmi = {t["id"]: t.get("npmi", 1) for t in CONJ.get("topicos", [])}
        tabla = pd.DataFrame([{
            "Tema": f"{t['id'] + 1}. {t['etiqueta']}",
            "Cómo lo dice la DMO": ", ".join(t.get("palabras_dmo", [])[:5]) or ", ".join(t["palabras"][:5]),
            "Cómo lo dicen los visitantes": ", ".join(t.get("palabras_percibida", [])[:5]),
            "% DMO": t["pct_dmo"], "% visitantes": t["pct_percibida"],
            "Diferencia (puntos)": t["brecha_pp"],
            "% negativos (visitantes)": t["pct_negativo_percibida"],
            "Situación": f"{CLASES[t['clase']][1]} {CLASES[t['clase']][0]}",
        } for t in sorted(TEMAS, key=lambda t: -abs(t["brecha_pp"]))])
        st.dataframe(tabla, hide_index=True, width="stretch",
                     column_config={"% DMO": st.column_config.ProgressColumn(format="%.1f", min_value=0, max_value=max(tabla["% DMO"].max(), 1)),
                                    "% visitantes": st.column_config.ProgressColumn(format="%.1f", min_value=0, max_value=max(tabla["% visitantes"].max(), 1)),
                                    "Diferencia (puntos)": st.column_config.NumberColumn(format="%+.1f"),
                                    "% negativos (visitantes)": st.column_config.NumberColumn(format="%.1f")})
        st.download_button("Descargar tabla (CSV)", tabla.to_csv(index=False).encode("utf-8"), "temas_dmo_vs_visitantes.csv",
                           "text/csv")

        st.subheader("Cómo se habla de cada tema")
        info = {t["id"]: t for t in CONJ.get("topicos", [])}
        for t in sorted(TEMAS, key=lambda t: -abs(t["brecha_pp"])):
            etiqueta, icono = CLASES[t["clase"]]
            with st.expander(f"{icono} Tema {t['id'] + 1}: {t['etiqueta']} — {etiqueta.lower()} "
                             f"(DMO {t['pct_dmo']:.0f} % · visitantes {t['pct_percibida']:.0f} %)"):
                if npmi.get(t["id"], 1) < 0.05:
                    st.caption("⚠️ Este tema reúne palabras de asuntos distintos; léase con cautela.")
                st.markdown("**Palabras clave del tema:** " + ", ".join(t["palabras"]))
                ppf = t.get("palabras_por_fuente", {})
                if ppf:
                    st.markdown("**Con qué palabras lo aborda cada fuente:**  \n" + "  \n".join(
                        f"{nombre(f, dmo)}: {', '.join(ppf[f][:6])}" for f in fuentes if ppf.get(f)))
                if (t.get("palabras_compartidas") is not None and t["palabras_compartidas"] <= 1
                        and min(t["pct_dmo"], t["pct_percibida"]) >= 5):
                    st.caption("⚠️ La DMO y los visitantes abordan este tema con palabras distintas: "
                               "no es la misma conversación.")
                pf = t["pct_por_fuente"]
                fig = go.Figure(go.Bar(x=[nombre(f, dmo) for f in fuentes if f in pf], y=[pf[f] for f in fuentes if f in pf],
                                       marker=dict(color=[col_f[f] for f in fuentes if f in pf]),
                                       text=[f"{pf[f]:.1f} %" for f in fuentes if f in pf], textposition="outside"))
                fig.update_layout(template=PLANTILLA, height=230, margin=dict(l=10, r=10, t=10, b=10),
                                  yaxis=dict(title="% del contenido", range=[0, max(pf.values()) * 1.3 + 1]))
                c1, c2_ = st.columns([0.4, 0.6])
                c1.plotly_chart(fig, width="stretch", key=f"tema_fuentes_{t['id']}")
                with c2_:
                    st.markdown("**Así lo presenta la DMO**")
                    rpf = info.get(t["id"], {}).get("representativo_por_fuente", {})
                    if rpf.get(dmo):
                        cita(rpf[dmo], dmo, dmo)
                    else:
                        st.caption("La DMO no tiene textos centrados en este tema.")
                    st.markdown("**Así lo cuentan los visitantes**")
                    otros = [(f, v) for f, v in rpf.items() if f != dmo]
                    for f, v in otros[:3]:
                        cita(v, f, dmo)
                    if not otros:
                        st.caption("Los visitantes no tienen comentarios centrados en este tema.")


# ---------------------------------------------------------------- 2b. DMO frente a cada fuente
def fig_palabras(pares, color, titulo, n=12):
    datos = pares[:n]
    fig = go.Figure(go.Bar(y=[w for w, _ in datos][::-1], x=[z for _, z in datos][::-1], orientation="h", marker=dict(color=color),
                           hovertemplate="%{y}: %{x:.1f}<extra></extra>"))
    fig.update_layout(template=PLANTILLA, height=max(260, 24 * len(datos) + 80), margin=dict(l=10, r=10, t=36, b=10), title=titulo,
                      xaxis_title="Qué tanto la distingue (log-odds z)")
    return fig


with pestanas[2]:
    if not PF_IND:
        st.warning("No hubo suficientes comentarios para comparar la DMO con cada fuente por separado.")
    else:
        st.markdown("La DMO se compara con **cada fuente por separado**, con los mismos temas. Primero las cifras "
                    "(cuantitativo) y después cómo habla cada lado de cada tema, con sus propias palabras y ejemplos "
                    "(cualitativo).")
        filas = []
        for f, c in PF_IND.items():
            temas_f = c["temas"]
            mayor = max(temas_f, key=lambda t: abs(t["brecha_pp"])) if temas_f else None
            filas.append({
                "Fuente": nombre(f, dmo), "Comentarios": c["n"],
                "% positivos": c["tono"]["pct_positivo_fuente"],
                "Tono frente a la DMO (puntos)": c["tono"]["pct_positivo_fuente"] - c["tono"]["pct_positivo_dmo"],
                "Parecido del contenido": c["parecido"]["valor"],
                "Coincidencia de agenda": c["coincidencia_agenda"],
                "La DMO destaca más (temas)": sum(t["clase"] == "Proyectado, poco percibido" for t in temas_f),
                "La fuente menciona más (temas)": sum(t["clase"] == "Percibido, poco proyectado" for t in temas_f),
                "Mayor diferencia": f"{mayor['etiqueta']} ({mayor['brecha_pp']:+.0f} pts)" if mayor else "—",
            })
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                     column_config={"% positivos": st.column_config.NumberColumn(format="%.1f"),
                                    "Tono frente a la DMO (puntos)": st.column_config.NumberColumn(format="%+.1f"),
                                    "Parecido del contenido": st.column_config.ProgressColumn(
                                        format="%.2f", min_value=0, max_value=1,
                                        help="Coseno entre el contenido promedio de la DMO y el de la fuente (0 a 1)."),
                                    "Coincidencia de agenda": st.column_config.ProgressColumn(
                                        format="%.2f", min_value=0, max_value=1,
                                        help="1 − divergencia de Jensen-Shannon entre cómo reparten los temas (0 a 1).")})
        orden_pf = list(PF_IND)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[nombre(f, dmo) for f in orden_pf], y=[PF_IND[f]["parecido"]["valor"] for f in orden_pf],
                             name="Parecido del contenido", marker=dict(color=[col_f.get(f, COL_VIS) for f in orden_pf]),
                             error_y=dict(type="data", symmetric=False,
                                          array=[PF_IND[f]["parecido"]["ic95"][1] - PF_IND[f]["parecido"]["valor"] for f in orden_pf],
                                          arrayminus=[PF_IND[f]["parecido"]["valor"] - PF_IND[f]["parecido"]["ic95"][0] for f in orden_pf],
                                          color="#444"),
                             text=[f"{PF_IND[f]['parecido']['valor']:.2f}" for f in orden_pf], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="white", size=14)))
        fig.add_trace(go.Bar(x=[nombre(f, dmo) for f in orden_pf], y=[PF_IND[f]["coincidencia_agenda"] for f in orden_pf],
                             name="Coincidencia de agenda", marker=dict(color=[col_f.get(f, COL_VIS) for f in orden_pf],
                                                                        pattern=dict(shape="/", fgcolor="white", size=6)),
                             text=[f"{PF_IND[f]['coincidencia_agenda']:.2f}" for f in orden_pf], textposition="outside"))
        fig.update_layout(template=PLANTILLA, barmode="group", height=330, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
                          yaxis=dict(range=[0, 1.12], title="0 = nada en común · 1 = igual"))
        st.plotly_chart(fig, width="stretch", key="pf_resumen")
        st.caption("Barra lisa: parecido del contenido (con su rango probable). Barra rayada: coincidencia de agenda temática.")

        st.divider()
        f_sel = st.radio("Comparar la DMO con", orden_pf, horizontal=True, format_func=lambda f: nombre(f, dmo), key="pf_sel")
        c = PF_IND[f_sel]
        cf = col_f.get(f_sel, COL_VIS)
        if c.get("pocos"):
            st.info(f"{nombre(f_sel, dmo)} tiene pocos comentarios en este idioma ({c['n']}); tómalo como exploratorio.", icon="ℹ️")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Comentarios", f"{c['n']:,}", help=f"La DMO tiene {c['n_dmo']:,}.")
        to = c["tono"]
        m2.metric("Tono positivo", f"{to['pct_positivo_fuente']:.0f} %",
                  delta=f"{to['pct_positivo_fuente'] - to['pct_positivo_dmo']:+.0f} puntos frente a la DMO ({to['pct_positivo_dmo']:.0f} %)",
                  delta_color="off")
        m3.metric("Parecido del contenido", f"{c['parecido']['valor']:.2f}",
                  help="0 = hablan de cosas totalmente distintas; 1 = hablan de lo mismo y con las mismas palabras.")
        m3.caption(f"Rango probable: {c['parecido']['ic95'][0]:.2f} a {c['parecido']['ic95'][1]:.2f}")
        m4.metric("Coincidencia de agenda", f"{c['coincidencia_agenda']:.2f}",
                  help="Qué tanto reparten igual los temas la DMO y esta fuente (0 a 1).")
        if to.get("prueba_chi2"):
            pv = to["prueba_chi2"]["p_valor"]
            st.caption(f"Diferencia de tono: χ² = {to['prueba_chi2']['chi2']:.1f}, p = {pv:.3g} → "
                       + ("es una diferencia real, no producto del azar." if pv < 0.05 else
                          "no se puede afirmar que el tono sea distinto."))

        st.markdown(f"#### Cuantitativo: cuánto habla cada uno de cada tema")
        izq, der = st.columns(2)
        with izq:
            st.plotly_chart(fig_comparativo(c["temas"], campo="pct_fuente", nombre_vis=nombre(f_sel, dmo), color_vis=cf,
                                            color_dmo=col_f[dmo]), width="stretch", key=f"pf_barras_{f_sel}")
        with der:
            st.plotly_chart(fig_brechas(c["temas"], lado=nombre(f_sel, dmo), color_vis=cf, color_dmo=col_f[dmo]),
                            width="stretch", key=f"pf_brechas_{f_sel}")
        st.caption("Las líneas de cada barra son el rango probable de la diferencia (bootstrap, 95 %). Una diferencia cuenta "
                   "si supera 5 puntos y su rango no cruza el cero.")

        st.markdown(f"#### Cualitativo: cómo lo dice cada uno")
        visible = nombre(f_sel, dmo)
        for frase in c.get("resumen", []):
            st.markdown("- " + re.sub(rf"(?<![\w«]){re.escape(f_sel)}(?![\w»])", visible, frase))
        a, b = st.columns(2)
        if c.get("palabras_de_la_dmo"):
            a.plotly_chart(fig_palabras(c["palabras_de_la_dmo"], col_f[dmo], "Palabras propias de la DMO"), width="stretch",
                           key=f"pf_pd_{f_sel}")
        if c.get("palabras_de_la_fuente"):
            b.plotly_chart(fig_palabras(c["palabras_de_la_fuente"], cf, f"Palabras propias de {nombre(f_sel, dmo)}"),
                           width="stretch", key=f"pf_pf_{f_sel}")
        st.markdown("**Tema por tema**")
        lectura_f = {"Proyectado, poco percibido": "la DMO lo destaca más", "Percibido, poco proyectado": f"{visible} lo menciona más",
                     "Coincidencia": "coinciden", "Marginal en ambos": "poco presente en ambos"}
        for t in sorted(c["temas"], key=lambda t: -abs(t["brecha_pp"])):
            icono = CLASES[t["clase"]][1]
            with st.expander(f"{icono} {t['etiqueta']} — {lectura_f[t['clase']]} "
                             f"(DMO {t['pct_dmo']:.0f} % · {nombre(f_sel, dmo)} {t['pct_fuente']:.0f} %)"):
                x1, x2 = st.columns(2)
                with x1:
                    st.markdown(f"**DMO** · palabras: {', '.join(t.get('palabras_dmo', [])[:6]) or '—'}")
                    for e in t.get("ejemplos_dmo", []):
                        cita(e)
                    if not t.get("ejemplos_dmo"):
                        st.caption("La DMO no tiene textos sobre este tema.")
                with x2:
                    st.markdown(f"**{nombre(f_sel, dmo)}** · palabras: {', '.join(t.get('palabras_fuente', [])[:6]) or '—'}")
                    for e in t.get("ejemplos_fuente", []):
                        cita(e)
                    if not t.get("ejemplos_fuente"):
                        st.caption("Esta fuente no tiene comentarios sobre este tema.")
        st.caption("Los ejemplos se eligieron con BM25 (Robertson y Zaragoza, 2009): dentro de los comentarios de cada lado "
                   "asignados al tema, los que más usan sus palabras clave.")


# ---------------------------------------------------------------- 3. Positivo / negativo
def bloque_particion(s, titulo):
    r = R["topicos"][s]
    st.markdown(f"#### {titulo}")
    if r.get("tipo") != "topicos":
        st.caption(f"Sólo {r.get('n', 0)} comentarios: se muestran las palabras más frecuentes.")
        fr = r.get("frecuencias", [])[:20]
        if fr:
            fig = go.Figure(go.Bar(y=[w for w, _ in fr][::-1], x=[n for _, n in fr][::-1], orientation="h", marker_color=COL_VIS))
            fig.update_layout(template=PLANTILLA, height=420, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch", key=f"frec_{s}")
        return
    temas = sorted(r["topicos"], key=lambda t: -t["n"])
    y = [f"{t['id'] + 1}. {t['etiqueta']}" for t in temas]
    fig = go.Figure()
    for f in fuentes:
        fig.add_trace(go.Bar(y=y, x=[t["mezcla_fuentes"].get(f, 0) for t in temas], orientation="h", name=nombre(f, dmo),
                             marker=dict(color=col_f[f], line=dict(width=0))))
    fig.update_layout(barmode="stack", template=PLANTILLA, height=max(300, 28 * len(temas) + 110), margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", y=-0.12), xaxis_title="Número de comentarios")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch", key=f"part_{s}")
    for t in temas:
        with st.expander(f"Tema {t['id'] + 1}: {t['etiqueta']} · {t['n']:,} comentarios"):
            st.markdown("**Palabras clave:** " + ", ".join(t["palabras"]))
            ppf = t.get("palabras_por_fuente", {})
            if ppf:
                st.markdown("**Según la fuente:**  \n" + "  \n".join(f"{nombre(f, dmo)}: {', '.join(ppf[f][:6])}"
                                                                       for f in fuentes if ppf.get(f)))
            rep = t.get("representativo") or {}
            if rep:
                st.markdown("**Comentario más representativo**")
                cita(rep["texto"], rep["fuente"], dmo)
            otros = {f: v for f, v in t.get("representativo_por_fuente", {}).items() if f != rep.get("fuente")}
            if otros:
                st.markdown("**En otras fuentes**")
                for f, v in otros.items():
                    cita(v, f, dmo)
    peq = r.get("fuentes_pequenas", {})
    if peq:
        st.caption("Con muy pocos comentarios en este grupo, " + ", ".join(f"{nombre(f, dmo)} ({v['n']})" for f, v in peq.items()) +
                   " se describe con sus palabras más frecuentes (abajo, en las nubes de palabras).")


@st.cache_data(show_spinner=False)
def imagen_nube(clave_corpus, fuente, tono, color, frecuencias):
    from pipeline.nubes import nube_png
    return nube_png([tuple(x) for x in frecuencias], color=color, ancho=520, alto=300)


def nubes_por_fuente():
    frec = R.get("frecuencias_fuente_tono")
    if not frec:
        return
    st.markdown("#### Palabras más frecuentes por fuente y tono")
    st.caption("El tamaño de la palabra indica qué tan seguido aparece. Cuando una fuente tiene muy pocos comentarios "
               "en un tono, ésta es su descripción.")
    for s, titulo in (("positivo", "Comentarios positivos"), ("negativo", "Comentarios negativos")):
        st.markdown(f"**{titulo}**")
        cols = st.columns(len(fuentes))
        for c, f in zip(cols, fuentes):
            d = frec.get(f, {}).get(s)
            if not d:
                continue
            c.markdown(f"<span style='color:{col_f[f]}'>{forma_txt.get(simb[f], '●')}</span> **{nombre(f, dmo)}** · {d['n']:,}",
                       unsafe_allow_html=True)
            png = imagen_nube(clave, f, s, col_f[f], d["frecuencias"]) if d["frecuencias"] else None
            if png:
                c.image(png, width="stretch")
            else:
                c.caption("Sin comentarios")
            if d.get("bajo_umbral") and d["n"]:
                c.caption("Muy pocos comentarios: " + ", ".join(f"{w} ({n})" for w, n in d["frecuencias"][:8]))


with pestanas[3]:
    st.markdown("**Porcentaje de comentarios con tono positivo**")
    st.plotly_chart(fig_tono_fuentes(), width="stretch", key="tono")
    izq, der = st.columns(2)
    with izq:
        bloque_particion("positivo", "De qué se habla cuando el tono es positivo")
    with der:
        bloque_particion("negativo", "De qué se habla cuando el tono es negativo")
    nubes_por_fuente()


# ---------------------------------------------------------------- 4. Por fuente
with pestanas[4]:
    filas = []
    for fila in COMP.get("por_fuente", []):
        f = fila["fuente"]
        filas.append({"Fuente": nombre(f, dmo), "Comentarios": fila["n"], "% positivos": fila["pct_positivo"],
                      "Temas principales": "; ".join(f"{x['etiqueta']} ({x['pct']:.0f} %)" for x in fila.get("temas_principales", [])),
                      "Temas en comentarios positivos": "; ".join(x["etiqueta"] for x in fila.get("temas_positivos", [])),
                      "Temas en comentarios negativos": "; ".join(x["etiqueta"] for x in fila.get("temas_negativos", [])),
                      "Parecido con la DMO": fila.get("ias")})
    orden_f = {nombre(f, dmo): i for i, f in enumerate(fuentes)}
    tf = pd.DataFrame(filas).sort_values("Fuente", key=lambda s: s.map(orden_f))
    st.dataframe(tf, hide_index=True, width="stretch",
                 column_config={"% positivos": st.column_config.NumberColumn(format="%.1f"),
                                "Parecido con la DMO": st.column_config.NumberColumn(format="%.2f",
                                                                                      help="0 a 1: qué tanto se parece el contenido de la fuente al de la DMO")})
    if CONJ.get("tipo") == "topicos":
        st.markdown("**Qué parte del contenido de cada fuente dedica a cada tema (%)**")
        pf = CONJ["por_fuente"]
        z = [[pf[f]["prop"].get(str(t["id"]), 0) for f in fuentes if f in pf] for t in CONJ["topicos"]]
        fig = go.Figure(go.Heatmap(z=z, x=[nombre(f, dmo) for f in fuentes if f in pf],
                                   y=[f"{t['id'] + 1}. {t['etiqueta']}" for t in CONJ["topicos"]], colorscale=ESCALA,
                                   text=[[f"{v:.0f}" for v in fila] for fila in z], texttemplate="%{text}",
                                   hovertemplate="%{y}<br>%{x}: %{z:.1f} %<extra></extra>", colorbar=dict(title="%")))
        fig.update_layout(template=PLANTILLA, height=max(380, 30 * len(z) + 100), margin=dict(l=10, r=10, t=10, b=10))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch", key="heat")
        st.caption("Fuentes que entran en el promedio de visitantes: " + ", ".join(nombre(f, dmo) for f in perc_prom) +
                   ". Cada una pesa lo mismo, sin importar cuántos comentarios tenga.")


# ---------------------------------------------------------------- 5. Explorar
with pestanas[5]:
    mapa = D[D.en_mapa].copy()
    if mapa.empty:
        st.warning("No hay suficientes comentarios para dibujar el mapa.")
    else:
        st.markdown("Cada punto es un comentario; los que están cerca hablan de cosas parecidas. "
                    "Selecciona puntos con el lazo o el recuadro para leerlos abajo.")
        c1, c2_, c3 = st.columns([0.3, 0.4, 0.3])
        color_por = c1.radio("Color según", ["Tema", "Tema por tono", "Fuente", "Tono"], horizontal=True)
        ver_f = c2_.multiselect("Fuentes", fuentes, default=fuentes, format_func=lambda f: nombre(f, dmo))
        ver_t = c3.multiselect("Tono", ["positivo", "negativo"], default=["positivo", "negativo"])
        mapa = mapa[mapa.fuente.isin(ver_f) & mapa.sentimiento.isin(ver_t)]
        etiquetas = {t["id"]: f"{t['id'] + 1}. {t['etiqueta']}" for t in CONJ.get("topicos", [])}
        fig = go.Figure()
        if color_por == "Tema" and etiquetas:
            col_t = colores(paleta, len(etiquetas))
            grupos = [(int(t), mapa[mapa.topico_conjunto == t]) for t in sorted(etiquetas)]
            for t, g in grupos:
                for f in fuentes:
                    gf = g[g.fuente == f]
                    if gf.empty:
                        continue
                    fig.add_trace(go.Scattergl(x=gf.x, y=gf.y, mode="markers", name=etiquetas[t], legendgroup=str(t),
                                               showlegend=f == next(ff for ff in fuentes if not g[g.fuente == ff].empty),
                                               marker=dict(color=col_t[t], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.8,
                                                           line=dict(width=0.4, color="white")),
                                               customdata=gf.id_registro, text=hover(gf.texto, gf.fuente, gf.sentimiento, dmo),
                                               hoverinfo="text"))
        elif color_por == "Tema por tono":
            # temas de los comentarios positivos y de los negativos, con distinción en la leyenda
            et_p = {}
            for s_ in ("positivo", "negativo"):
                rp = R["topicos"][s_]
                if rp.get("tipo") == "topicos":
                    for t in rp["topicos"]:
                        et_p[(s_, t["id"])] = f"{'+' if s_ == 'positivo' else '−'} {t['id'] + 1}. {t['etiqueta']}"
            col_p = dict(zip(et_p, colores(paleta, max(len(et_p), 1))))
            for (s_, t), etiqueta in et_p.items():
                g = mapa[(mapa.sentimiento == s_) & (mapa.topico_particion == t)]
                primero = True
                for f in fuentes:
                    gf = g[g.fuente == f]
                    if gf.empty:
                        continue
                    fig.add_trace(go.Scattergl(x=gf.x, y=gf.y, mode="markers", name=etiqueta, legendgroup=etiqueta, showlegend=primero,
                                               marker=dict(color=col_p[(s_, t)], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.8,
                                                           line=dict(width=0.4, color="white")),
                                               customdata=gf.id_registro, text=hover(gf.texto, gf.fuente, gf.sentimiento, dmo),
                                               hoverinfo="text"))
                    primero = False
            st.caption("Leyenda: «+» temas de comentarios positivos · «−» temas de comentarios negativos.")
        elif color_por == "Tono":
            ct_ = dict(zip(["positivo", "negativo"], colores(paleta, 2, 0.15, 0.8)))
            for s in ["positivo", "negativo"]:
                for f in fuentes:
                    gf = mapa[(mapa.sentimiento == s) & (mapa.fuente == f)]
                    if gf.empty:
                        continue
                    fig.add_trace(go.Scattergl(x=gf.x, y=gf.y, mode="markers", name=f"{s} · {nombre(f, dmo)}",
                                               marker=dict(color=ct_[s], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.75,
                                                           line=dict(width=0.4, color="white")),
                                               customdata=gf.id_registro, text=hover(gf.texto, gf.fuente, gf.sentimiento, dmo),
                                               hoverinfo="text"))
        else:
            for f in [x for x in fuentes if x != dmo] + [dmo]:
                gf = mapa[mapa.fuente == f]
                if gf.empty:
                    continue
                fig.add_trace(go.Scattergl(x=gf.x, y=gf.y, mode="markers", name=nombre(f, dmo),
                                           marker=dict(color=col_f[f], symbol=simb[f], size=9 if f == dmo else 6, opacity=0.75,
                                                       line=dict(width=0.4, color="white")),
                                           customdata=gf.id_registro, text=hover(gf.texto, gf.fuente, gf.sentimiento, dmo),
                                           hoverinfo="text"))
        fig.update_layout(template=PLANTILLA, height=640, margin=dict(l=10, r=10, t=10, b=10), dragmode="lasso",
                          xaxis=dict(visible=False), yaxis=dict(visible=False), legend=dict(font=dict(size=11)))
        ev = st.plotly_chart(fig, width="stretch", key="mapa", on_select="rerun", selection_mode=("lasso", "box", "points"))
        st.caption("Forma = fuente (■ es la DMO). Se muestra una muestra de hasta 1,200 comentarios por fuente.")
        ids = [p.get("customdata") for p in (ev.selection.points if ev and ev.selection else [])]
        ids = [i[0] if isinstance(i, list) else i for i in ids if i is not None]
        if ids:
            sel = D[D.id_registro.isin(ids)]
            st.markdown(f"**{len(sel):,} comentarios seleccionados**")
            resumen = sel.fuente.map(lambda f: nombre(f, dmo)).value_counts()
            st.caption(" · ".join(f"{k}: {v}" for k, v in resumen.items()) +
                       f" · positivos: {(sel.sentimiento == 'positivo').mean() * 100:.0f} %")
            st.dataframe(pd.DataFrame({"Fuente": sel.fuente.map(lambda f: nombre(f, dmo)), "Tono": sel.sentimiento,
                                       "Tema": sel.topico_conjunto.map(lambda t: etiquetas.get(int(t), "—") if pd.notna(t) and t >= 0 else "—"),
                                       "Comentario": sel.texto.map(lambda t: corto(t, 400))}),
                         hide_index=True, width="stretch", height=360)

    st.divider()
    st.subheader("Buscar comentarios")
    st.caption("Escribe palabras y se ordenan los comentarios que las usan con BM25 (Robertson y Zaragoza, 2009): pesa más "
               "las palabras poco comunes en la base y no premia a un comentario sólo por ser largo. Se buscan también las "
               "formas de la palabra (comer, comida, comí → misma raíz).")
    if "lemas" not in D.columns:
        st.info("Este corpus se generó con una versión anterior; vuelve a correr el análisis para activar la búsqueda.")
    else:
        b1, b2 = st.columns([0.6, 0.4])
        q = b1.text_input("Palabras a buscar", placeholder="por ejemplo: comida precio metro", key="q_bm25")
        ver_q = b2.multiselect("En", fuentes, default=fuentes, format_func=lambda f: nombre(f, dmo), key="q_fuentes")
        if q.strip():
            idx = indice_bm25(clave, D.lemas.fillna(""))
            cons = consulta_lemas(q, P["idioma"], tuple(P.get("excluir") or ()))
            puntajes = idx.puntajes(cons)
            if not cons or not (puntajes > 0).any():
                st.warning("Ningún comentario usa esas palabras. Prueba con otras o revisa el idioma.")
            else:
                mascara = D.fuente.isin(ver_q).to_numpy()
                tiene = puntajes > 0
                por_f = {f: 100 * tiene[(D.fuente == f).to_numpy()].mean() for f in fuentes if f in ver_q}
                fig = go.Figure(go.Bar(x=[nombre(f, dmo) for f in por_f], y=list(por_f.values()),
                                       marker=dict(color=[col_f[f] for f in por_f]),
                                       text=[f"{v:.1f} %" for v in por_f.values()], textposition="outside"))
                fig.update_layout(template=PLANTILLA, height=260, margin=dict(l=10, r=10, t=30, b=10),
                                  title="% de comentarios de cada fuente que usan esas palabras",
                                  yaxis=dict(range=[0, max(por_f.values() or [1]) * 1.3 + 0.5]))
                st.plotly_chart(fig, width="stretch", key="q_por_fuente")
                mejores = idx.mejores(cons, k=30, mascara=mascara)
                et_q = {t["id"]: f"{t['id'] + 1}. {t['etiqueta']}" for t in CONJ.get("topicos", [])}
                res_q = D.iloc[mejores]
                st.dataframe(pd.DataFrame({
                    "Puntaje BM25": np.round(puntajes[mejores], 2), "Fuente": res_q.fuente.map(lambda f: nombre(f, dmo)).to_numpy(),
                    "Tono": res_q.sentimiento.fillna("atípico").to_numpy(),
                    "Tema": res_q.topico_conjunto.map(lambda t: et_q.get(int(t), "—") if pd.notna(t) and t >= 0 else "—").to_numpy(),
                    "Comentario": res_q.texto.map(lambda t: corto(t, 400)).to_numpy()}),
                    hide_index=True, width="stretch", height=420,
                    column_config={"Puntaje BM25": st.column_config.NumberColumn(format="%.2f")})
                st.caption(f"Se buscó: {cons}. Se muestran hasta 30 comentarios, del más al menos relevante.")

# ---------------------------------------------------------------- 6. Concepto
with pestanas[6]:
    CC = R["concepto"]
    pg = CC["por_grupo"]
    st.markdown(f"Comentarios cuyo contenido se acerca a **«{P['concepto']}»**, aunque no usen esas palabras exactas. "
                f"Palabras que más se asocian a la idea en este corpus: *{lista_palabras(CC['terminos_cercanos'], 12)}*.")
    grupos = ["DMO", "Percibida"] + [f for f in fuentes if f != dmo and f in pg]
    nom_g = lambda g: "DMO" if g == "DMO" else ("Visitantes (todas)" if g == "Percibida" else nombre(g, dmo))
    a, b = st.columns(2)
    if "DMO" in pg and "Percibida" in pg:
        a.metric("DMO: textos que tocan el tema", f"{pg['DMO']['pct_ligados']:.1f} %")
        b.metric("Visitantes: comentarios que tocan el tema", f"{pg['Percibida']['pct_ligados']:.1f} %",
                 delta=f"{pg['Percibida']['pct_ligados'] - pg['DMO']['pct_ligados']:+.1f} puntos frente a la DMO", delta_color="off")
    izq, der = st.columns(2)
    with izq:
        colg = {"DMO": col_f[dmo], "Percibida": "#6b6f73", **{f: col_f[f] for f in fuentes}}
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[nom_g(g) for g in grupos], y=[pg[g]["pct_ligados"] for g in grupos],
                             marker=dict(color=[colg[g] for g in grupos]),
                             text=[f"{pg[g]['pct_ligados']:.1f} % ({pg[g]['n_ligados']})" for g in grupos],
                             textposition="outside", name="Tocan el tema"))
        fig.update_layout(template=PLANTILLA, height=320, margin=dict(l=10, r=10, t=30, b=10), title="% de textos que tocan el tema",
                          yaxis=dict(range=[0, max(pg[g]["pct_ligados"] for g in grupos) * 1.3 + 0.5]), showlegend=False)
        st.plotly_chart(fig, width="stretch", key="conc_pct")
    with der:
        gv = [g for g in grupos if pg[g].get("pct_positivo_ligados") is not None]
        fig = go.Figure(go.Bar(x=[nom_g(g) for g in gv], y=[pg[g]["pct_positivo_ligados"] for g in gv],
                               marker=dict(color=[colg[g] for g in gv], pattern=dict(shape="/", fgcolor="white", size=5)),
                               text=[f"{pg[g]['pct_positivo_ligados']:.0f} % (de {pg[g]['n_ligados']})" for g in gv],
                               textposition="outside"))
        fig.update_layout(template=PLANTILLA, height=320, margin=dict(l=10, r=10, t=30, b=10),
                          title="De esos, % con tono positivo", yaxis=dict(range=[0, 110]))
        st.plotly_chart(fig, width="stretch", key="conc_pos")

    if all("pct_mencionan" in pg[g] for g in grupos):
        st.markdown("**Cercanía semántica frente a mención literal**")
        st.dataframe(pd.DataFrame([{"Grupo": nom_g(g), "% cercanos a la idea (semántico)": pg[g]["pct_ligados"],
                                    "% que usan las palabras (BM25 > 0)": pg[g]["pct_mencionan"]} for g in grupos]),
                     hide_index=True, width="stretch",
                     column_config={"% cercanos a la idea (semántico)": st.column_config.NumberColumn(format="%.1f"),
                                    "% que usan las palabras (BM25 > 0)": st.column_config.NumberColumn(format="%.1f")})
        st.caption("La cercanía semántica (LSA) encuentra también comentarios que hablan de la idea con otras palabras "
                   "(«caro», «regatear»); BM25 sólo cuenta los que usan literalmente las palabras buscadas.")

    st.markdown("**Con qué palabras aparece la idea en cada grupo**")
    cols = st.columns(len(grupos))
    for c, g in zip(cols, grupos):
        c.markdown(f"*{nom_g(g)}*")
        c.caption(lista_palabras(pg[g].get("contexto_palabras", []), 10) or "—")
        if pg[g].get("contexto_bigramas"):
            c.caption("Frases: " + lista_palabras(pg[g]["contexto_bigramas"], 5))

    g = D[~D.outlier & D.sentimiento.notna()]  # todos los comentarios analizados
    fig = go.Figure()
    for f in [x for x in fuentes if x != dmo] + [dmo]:
        gf = g[g.fuente == f]
        fig.add_trace(go.Scattergl(x=gf.sim_concepto, y=gf.polaridad, mode="markers", name=nombre(f, dmo),
                                   marker=dict(color=col_f[f], symbol=simb[f], size=9 if f == dmo else 5, opacity=0.6,
                                               line=dict(width=0.3, color="white")),
                                   text=hover(gf.texto, gf.fuente, gf.sentimiento, dmo), hoverinfo="text"))
    fig.add_vrect(x0=CC["umbral_similitud"], x1=1, fillcolor="#999", opacity=0.08, line_width=0,
                  annotation_text="tocan el tema", annotation_position="top left")
    fig.update_layout(template=PLANTILLA, height=520, margin=dict(l=10, r=10, t=20, b=10),
                      xaxis_title=f"Cercanía con «{P['concepto']}»", yaxis_title="Tono (−1 negativo · +1 positivo)",
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch", key="conc_scatter")

    st.markdown("**Los cinco comentarios más cercanos a la idea**")
    for x in CC.get("top5_global", []):
        cita(x["texto"], x["fuente"], dmo)
    if CC.get("top5_bm25"):
        with st.expander("Los cinco que más usan esas palabras (BM25)"):
            for x in CC["top5_bm25"]:
                cita(x["texto"], x["fuente"], dmo)
    with st.expander("Los más cercanos en cada fuente"):
        for f, xs in CC.get("top5_por_fuente", {}).items():
            st.markdown(f"**{nombre(f, dmo)}**")
            for x in xs:
                cita(x["texto"], None)


# ---------------------------------------------------------------- 7. Atípicos
with pestanas[7]:
    O = R["outliers"]
    OG = R.get("outliers_global", {})
    st.markdown("Comentarios que se apartan claramente de lo habitual: temas poco comunes, textos muy cortos o muy "
                "largos, o texto deformado. Se buscan en toda la base a la vez y se separan del resto para revisarlos "
                "aparte, porque pueden señalar asuntos emergentes o problemas de calidad.")
    if OG.get("n"):
        st.subheader("En toda la base")
        m1, m2, m3 = st.columns(3)
        m1.metric("Comentarios atípicos", f"{OG['n']:,}", help=f"de {OG['n_total']:,} comentarios")
        m2.metric("Porcentaje de la base", f"{OG['pct']:.1f} %")
        m3.metric("Palabras útiles (mediana)", f"{OG['palabras_mediana_atipicos']:.0f}",
                  delta=f"{OG['palabras_mediana_atipicos'] - OG['palabras_mediana_normales']:+.0f} frente a los demás",
                  delta_color="off")
        st.caption("Atípicos por fuente: " + " · ".join(f"{nombre(f, dmo)}: {OG['por_fuente'].get(f, 0)}" for f in fuentes))
        cols_ng = st.columns(3)
        for c, (clave, titulo) in zip(cols_ng, [("unigramas", "Palabras más frecuentes"), ("bigramas", "Pares de palabras"),
                                                ("trigramas", "Tríos de palabras")]):
            datos = OG.get(clave, [])[:10]
            if datos:
                fig = go.Figure(go.Bar(y=[w for w, _ in datos][::-1], x=[n for _, n in datos][::-1], orientation="h",
                                       marker=dict(color=COL_DMO), text=[n for _, n in datos][::-1], textposition="outside"))
                fig.update_layout(template=PLANTILLA, height=380, margin=dict(l=10, r=30, t=40, b=10), title=titulo,
                                  xaxis=dict(title="Veces que aparece", range=[0, max(n for _, n in datos) * 1.25]))
                c.plotly_chart(fig, width="stretch", key=f"og_{clave}")
        st.markdown("**Palabras que más distinguen a los atípicos del resto:** " + lista_palabras(OG.get("distintivas", []), 15))
        with st.expander("Los comentarios más atípicos de toda la base"):
            for e in OG.get("ejemplos", [])[:6]:
                cita(e["texto"], e.get("fuente"), dmo)
        st.subheader("En cada fuente")
    cols = st.columns(len(fuentes))
    for c, f in zip(cols, fuentes):
        if f in O and O[f]["n"] == 0:
            c.metric(nombre(f, dmo), "0")
            c.caption("Sin comentarios atípicos" + (" (la detección requiere al menos 30 comentarios)" if O[f]["n_fuente"] < 30 else ""))
        elif f in O:
            c.metric(nombre(f, dmo), f"{O[f]['n']:,}", help=f"{O[f]['pct']:.1f} % de sus comentarios")
            c.caption(f"{O[f]['pct']:.1f} % · palabras útiles (mediana): {O[f]['palabras_mediana_atipicos']:.0f} "
                      f"frente a {O[f]['palabras_mediana_normales']:.0f} en los demás")
    for f in fuentes:
        o = O.get(f)
        if not o or not o["n"]:
            continue
        with st.expander(f"{nombre(f, dmo)}: de qué hablan sus {o['n']} comentarios atípicos", expanded=(f == dmo)):
            cols_f = st.columns(3)
            for c, (k_ng, tit, n_ng) in zip(cols_f, [("unigramas", "Palabras más frecuentes", 8), ("bigramas", "Pares de palabras", 6),
                                                     ("trigramas", "Tríos de palabras", 5)]):
                datos = o.get(k_ng, [])[:n_ng]
                if not datos:
                    continue
                if max(v for _, v in datos) <= 1:
                    c.markdown(f"**{tit}**")
                    c.caption("Cada uno aparece una sola vez: " + lista_palabras(datos, n_ng))
                    continue
                fig = go.Figure(go.Bar(y=[w for w, _ in datos][::-1], x=[v for _, v in datos][::-1], orientation="h",
                                       marker=dict(color=col_f[f]), text=[v for _, v in datos][::-1], textposition="outside"))
                fig.update_layout(template=PLANTILLA, height=300, margin=dict(l=10, r=30, t=40, b=10), title=tit,
                                  xaxis=dict(title="Veces que aparece", range=[0, max(v for _, v in datos) * 1.3]))
                c.plotly_chart(fig, width="stretch", key=f"out_{k_ng}_{f}")
            izq, der = st.columns([0.45, 0.55])
            with izq:
                dist = o.get("distintivas", [])[:12]
                if dist:
                    fig = go.Figure(go.Bar(y=[w for w, _ in dist][::-1], x=[v for _, v in dist][::-1], orientation="h",
                                           marker=dict(color=col_f[f])))
                    fig.update_layout(template=PLANTILLA, height=360, margin=dict(l=10, r=10, t=30, b=10),
                                      title="Palabras que los distinguen del resto de la fuente", xaxis_title="Qué tanto los distingue")
                    st.plotly_chart(fig, width="stretch", key=f"out_{f}")
            with der:
                st.markdown("**Ejemplos**")
                for e in o.get("ejemplos", [])[:4]:
                    cita(e["texto"] if isinstance(e, dict) else e, None)
