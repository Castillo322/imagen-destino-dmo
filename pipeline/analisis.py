"""Los 8 pasos del análisis como una sola función, para que la usen el script de terminal y el tablero.

`ejecutar` recibe una tabla con una columna de texto y una de fuente (una o varias fuentes percibidas
además de la DMO) y devuelve los resultados en memoria; `guardar` los escribe en disco.
"""
import json
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from . import comparacion, conclusiones, concepto, config, nubes, outliers, reporte, sentimiento, topicos, visualizaciones
from .bm25 import BM25
from .preprocesamiento import Preprocesador, limpiar, preprocesar
from .representacion import EspacioLSA


class ErrorDeDatos(ValueError):
    """Los datos no permiten el análisis (falta la DMO, una sola fuente, idioma sin textos...)."""


def slug(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()[:60] or "reporte"


class Codificador(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)


def ejecutar(df, col_texto, col_fuente, dmo, idioma, titulo, paleta, excluir=(), umbral_topicos=config.UMBRAL_TOPICOS,
             contaminacion=config.CONTAMINACION_OUTLIERS, umbral_polaridad=0.0, texto_concepto=None, k_topicos=None,
             semilla=config.SEMILLA, cache_idioma=None, progreso=None, origen=""):
    """Corre los 8 pasos. Devuelve {"res": resultados (como JSON), "df": corpus procesado, "figs", "nubes"}.

    `progreso(fraccion, mensaje)` es opcional (el tablero lo usa para la barra de avance).
    """
    t0 = time.time()

    def paso(frac, msg):
        if progreso:
            progreso(frac, msg)
        else:
            print(f"[{time.time() - t0:6.1f} s] {msg}", flush=True)

    for c in (col_texto, col_fuente):
        if c not in df.columns:
            raise ErrorDeDatos(f"La columna «{c}» no existe. Columnas: {', '.join(map(str, df.columns))}")
    df = df[df[col_texto].notna()].copy()
    df[col_texto] = df[col_texto].astype(str)
    df["fuente"] = df[col_fuente].astype(str).str.strip()
    # Tratamiento de la base unificada: textos vacíos y copias exactas dentro de una misma fuente
    llave = df[col_texto].str.strip()
    vacios = llave.str.len() == 0
    duplicados = pd.DataFrame({"f": df["fuente"], "t": llave}).duplicated() & ~vacios
    calidad = {"vacios": {str(f): int(n) for f, n in df[vacios].fuente.value_counts().items()},
               "duplicados": {str(f): int(n) for f, n in df[duplicados].fuente.value_counts().items()}}
    df = df[~vacios & ~duplicados].copy()
    dmo = str(dmo).strip()
    if dmo not in set(df.fuente):
        raise ErrorDeDatos(f"No hay registros con la etiqueta de DMO «{dmo}». Fuentes: {', '.join(sorted(df.fuente.unique()))}")
    if df.fuente.nunique() < 2:
        raise ErrorDeDatos("Se necesitan al menos dos fuentes: la DMO y una fuente percibida.")
    df.insert(0, "id_registro", np.arange(len(df)))
    df["es_dmo"] = df.fuente == dmo
    paso(0.02, f"{len(df):,} comentarios de {df.fuente.nunique()} fuentes; DMO = «{dmo}»")

    # 1. Limpieza y preprocesamiento
    excluir = [w for w in excluir if str(w).strip()]
    texto_conc = texto_concepto or config.CONCEPTO_POR_IDIOMA.get(idioma, config.CONCEPTO_POR_IDIOMA["en"])
    df, formas = preprocesar(df, col_texto, idioma, excluir, cache=cache_idioma, conservar=limpiar(texto_conc).split())
    conteos = {f: {"total": int(len(g)), "en_idioma": int(g.en_idioma_objetivo.sum())} for f, g in df.groupby("fuente")}
    idiomas = {f: g.idioma_detectado.value_counts().head(4).to_dict() for f, g in df.groupby("fuente")}
    df = df[df.en_idioma_objetivo & (df.n_tokens > 0)]
    # Orden canónico: DMO primero, luego las fuentes de más a menos comentarios y, dentro de cada una, por texto
    # limpio. Así el resultado no cambia si los archivos se suben en otro orden, con otro nombre o con las filas
    # revueltas (los muestreos y el Isolation Forest dependen del orden de las filas).
    tam = df.fuente.value_counts()
    rango = {f: i for i, f in enumerate(sorted(tam.index, key=lambda f: (f != dmo, -tam[f], f)))}
    df = (df.assign(_rf=df.fuente.map(rango)).sort_values(["_rf", "texto_limpio", col_texto], kind="stable")
          .drop(columns="_rf").reset_index(drop=True))
    if not (df.fuente == dmo).any() or df.fuente.nunique() < 2:
        raise ErrorDeDatos(f"Tras filtrar por idioma «{idioma}» no quedan la DMO y al menos una fuente percibida. "
                           f"Idiomas detectados: {idiomas}")
    paso(0.35, f"Preprocesamiento: {len(df):,} comentarios en «{idioma}» con contenido")

    espacio = EspacioLSA(semilla=semilla).ajustar(df.lemas, df.fuente, config.MAX_POR_FUENTE)
    bm = BM25(df.lemas)

    # 2. Atípicos
    df = outliers.detectar(df, espacio.Z, contaminacion, semilla, config.MAX_POR_FUENTE)
    info_out = outliers.resumir(df, col_texto, formas)
    info_out_global = outliers.resumir_global(df, col_texto, formas)
    paso(0.42, f"Atípicos (modelo único sobre la base unificada): {int(df.outlier.sum())} {info_out_global.get('por_fuente')}")

    # 3. Sentimiento (sólo comentarios normales)
    df = sentimiento.clasificar(df, col_texto, umbral_polaridad)
    paso(0.48, "Sentimiento listo")

    # 4. Tópicos: modelo conjunto (para comparar) y uno por partición de sentimiento
    normales = df[~df.outlier]
    k_opc = [k_topicos] if k_topicos else config.K_TOPICOS
    res_conj, asign, mod_conj = topicos.modelar(normales, col_texto, formas, k_opc, config.MAX_POR_FUENTE_TOPICOS,
                                                semilla, umbral_topicos, devolver_modelo=True)
    df["topico_conjunto"] = np.nan
    if asign is not None:
        df.loc[normales.index, "topico_conjunto"] = asign
    paso(0.62, f"Temas en común: {res_conj.get('k', 'frecuencias')}")
    res_part = {}
    df["topico_particion"] = np.nan
    for s in ("positivo", "negativo"):
        part = normales[normales.sentimiento == s]
        r, asg, mod_p = topicos.modelar(part, col_texto, formas, k_opc, config.MAX_POR_FUENTE_TOPICOS, semilla,
                                        umbral_topicos, devolver_modelo=True)
        r["fuentes_pequenas"] = topicos.frecuencias_por_fuente_pequena(part, formas, umbral_topicos)
        if mod_p is not None:
            # palabras clave de cada tópico según la fuente de origen (requisito 6)
            pal = topicos.palabras_por_fuente(mod_p, part.lemas, part.fuente, formas, dmo,
                                              [f for f in part.fuente.unique() if f != dmo])
            for t in r["topicos"]:
                t["palabras_por_fuente"] = {f: pal[t["id"]][f] for f in t["mezcla_fuentes"] if f in pal[t["id"]]}
        if asg is not None:
            df.loc[part.index, "topico_particion"] = asg
        res_part[s] = r
    paso(0.75, f"Tópicos: conjunto k={res_conj.get('k')}, positivos k={res_part['positivo'].get('k')}, "
               f"negativos k={res_part['negativo'].get('k')}")
    frec_ft = {}
    for f, g in normales.groupby("fuente"):
        frec_ft[str(f)] = {}
        for s in ("positivo", "negativo"):
            gs = g[g.sentimiento == s]
            frec_ft[str(f)][s] = {"n": int(len(gs)), "bajo_umbral": bool(len(gs) < umbral_topicos),
                                  "frecuencias": topicos.frecuencias(gs.lemas, formas, k=40)}

    # 5. Comparación DMO vs percibida: en conjunto y con cada fuente por separado
    minimo = umbral_topicos
    normales = df[~df.outlier]
    perc_validas = [f for f, n in normales.fuente.value_counts().items() if f != dmo and n >= minimo]
    pal_f = topicos.palabras_por_fuente(mod_conj, normales.lemas, normales.fuente, formas, dmo, perc_validas) if mod_conj else None
    comp_temas = comparacion.comparar_topicos(normales, res_conj, dmo, config.UMBRAL_BRECHA_PP,
                                              Wn=mod_conj["Wn"] if mod_conj else None, semilla=semilla, minimo=minimo,
                                              palabras_fuente=pal_f)
    comp_sent = comparacion.comparar_sentimiento(df, dmo, minimo)
    comp_sim = comparacion.similitud_global(df, espacio.Z, dmo, semilla, minimo=minimo)
    por_fuente_ind = {}
    if mod_conj:
        voc = mod_conj["voc"]
        terminos = [list(dict.fromkeys(w for i in np.argsort(h)[::-1][:10] for w in voc[i].split())) for h in mod_conj["H"]]
        bm_norm = BM25(normales.lemas)
        por_fuente_ind = comparacion.comparar_por_fuente(
            normales, mod_conj["Wn"], espacio.Z[normales.index.to_numpy()], terminos,
            [t["etiqueta"] for t in res_conj["topicos"]], dmo, config.UMBRAL_BRECHA_PP, col_texto, formas, bm_norm,
            palabras_fuente=pal_f, semilla=semilla, minimo=minimo)
    advertencias = []
    n_norm = normales.fuente.value_counts()
    if n_norm.get(dmo, 0) < minimo:
        advertencias.append(f"La DMO tiene sólo {n_norm.get(dmo, 0)} textos en este idioma; la comparación es exploratoria.")
    pocas = [f"{f} ({n})" for f, n in n_norm.items() if f != dmo and n < minimo]
    if pocas:
        advertencias.append("Fuentes con muy pocos comentarios en este idioma, que se muestran pero no entran en el promedio "
                            "de visitantes: " + ", ".join(pocas) + ".")
    tabla = comparacion.tabla_por_fuente(res_part["positivo"], res_part["negativo"], res_conj, comp_sent, comp_sim, dmo)
    brechas = comparacion.resumen_brechas(comp_temas, comp_sent, comp_sim, dmo)
    paso(0.85, f"Comparación: parecido {comp_sim['ias']}, coincidencia de agenda {comp_temas and comp_temas['congruencia_tematica']}")

    # 8. Concepto precio / valor / costo (semántico + BM25)
    consulta = " ".join(Preprocesador(idioma, excluir, limpiar(texto_conc).split()).tokens(limpiar(texto_conc)))
    df, res_conc = concepto.analizar(df, espacio, consulta, formas, dmo, col_texto, config.PERCENTIL_CONCEPTO, bm=bm)
    paso(0.88, f"Concepto «{texto_conc}»: {res_conc['n_ligados_total']} comentarios ligados")

    # 7. Mapa 2D
    df = visualizaciones.proyectar_2d(df, espacio.Z, config.MAX_PUNTOS_MAPA_POR_FUENTE, semilla)
    for f in conteos:
        g = df[df.fuente == f]
        conteos[f].update({"outliers": int(g.outlier.sum()), "analizados": int((~g.outlier).sum())})
    res = {
        "parametros": {"csv": origen, "columna_texto": col_texto, "columna_fuente": col_fuente, "etiqueta_dmo": dmo,
                       "idioma": idioma, "titulo": titulo, "paleta": paleta, "umbral_topicos": umbral_topicos,
                       "contaminacion": contaminacion, "umbral_polaridad": umbral_polaridad, "concepto": texto_conc,
                       "semilla": semilla, "excluir": excluir, "k_topicos": k_topicos},
        "conteos": conteos, "idiomas_detectados": idiomas, "calidad": calidad,
        "outliers": info_out, "outliers_global": info_out_global,
        "topicos": {"conjunto": res_conj, "positivo": res_part["positivo"], "negativo": res_part["negativo"]},
        "frecuencias_fuente_tono": frec_ft,
        "comparacion": {"temas": comp_temas["temas"] if comp_temas else [],
                        "temas_resumen": {k: v for k, v in (comp_temas or {}).items() if k != "temas"},
                        "sentimiento": comp_sent, "similitud": comp_sim, "por_fuente": tabla,
                        "dmo_vs_cada_fuente": por_fuente_ind},
        "resumen_brechas": brechas,
        "advertencias": advertencias,
        "concepto": res_conc,
    }
    res = json.loads(json.dumps(res, ensure_ascii=False, cls=Codificador))  # mismas llaves que al leer de disco
    res["conclusiones"] = conclusiones.generar(res)  # respuesta a la pregunta del proyecto y decisiones para la DMO
    paso(0.92, "Visualizaciones")
    figs = visualizaciones.figuras(df, res, col_texto, dmo, paleta, titulo)
    fuentes_orden = [dmo] + sorted(f for f in frec_ft if f != dmo)
    col_nube = dict(zip(fuentes_orden, visualizaciones.colores(paleta, len(fuentes_orden))))
    imgs = {f: {s: nubes.nube_base64(frec_ft[f][s]["frecuencias"], color=col_nube[f], semilla=semilla)
                for s in ("positivo", "negativo")} for f in fuentes_orden}
    cols = ["id_registro", "fuente", "es_dmo", col_texto, "idioma_detectado", "texto_limpio", "lemas", "n_tokens",
            "outlier", "puntaje_atipico", "atipico_corte_global", "polaridad", "sentimiento", "metodo_sentimiento", "topico_conjunto",
            "topico_particion", "sim_concepto", "bm25_concepto", "ligado_concepto", "x", "y", "en_mapa"]
    extras = [c for c in df.columns if c not in cols and c not in ("en_idioma_objetivo", col_fuente)]
    df = df[cols + extras].rename(columns={col_texto: "texto"} if col_texto != "texto" else {})
    paso(1.0, f"Listo en {time.time() - t0:.0f} s")
    return {"res": res, "df": df, "figs": figs, "nubes": imgs}


def guardar(salida_base, resultado):
    """Escribe corpus_procesado.parquet, resultados.json y reporte.html en <salida>/<titulo>_<idioma>/."""
    res = resultado["res"]
    p = res["parametros"]
    salida = Path(salida_base) / f"{slug(p['titulo'])}_{p['idioma']}"
    salida.mkdir(parents=True, exist_ok=True)
    reporte.generar(res, resultado["figs"], salida / "reporte.html", p["titulo"], nubes=resultado["nubes"])
    # parquet compacto (zstd, decimales en float32); el texto limpio no se guarda: se reconstruye con limpiar(texto)
    # y lo que sigue al análisis son los lemas
    corpus = resultado["df"].drop(columns=["texto_limpio"], errors="ignore")
    for c in corpus.select_dtypes("float64").columns:
        corpus[c] = corpus[c].astype("float32")
    corpus.to_parquet(salida / "corpus_procesado.parquet", index=False, compression="zstd", compression_level=19)
    (salida / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, cls=Codificador), encoding="utf-8")
    return salida


def html_reporte(resultado):
    """El reporte HTML como texto (para descargarlo desde el tablero)."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "reporte.html"
        reporte.generar(resultado["res"], resultado["figs"], ruta, resultado["res"]["parametros"]["titulo"], nubes=resultado["nubes"])
        return ruta.read_text(encoding="utf-8")
