"""Comprueba, con datos que el script no ha visto, cada requisito del Proyecto Final.

Construye CSV nuevos a partir de datos/ejemplo.csv con OTROS nombres de columnas y de fuentes,
corre analizador.py como lo haría el profesor en la demostración y revisa las salidas.

Uso:  python verificar_requisitos.py
Sale con código 1 si algún requisito falla.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
PY = sys.executable
resultados = []


def ok(req, cond, detalle=""):
    resultados.append((req, bool(cond), detalle))


def correr(args, entorno=None):
    p = subprocess.run([PY, str(RAIZ / "analizador.py")] + args, capture_output=True, text=True, cwd=RAIZ,
                       env=entorno or os.environ.copy())
    return p.returncode, p.stdout + p.stderr


tmp = Path(tempfile.mkdtemp(prefix="verificacion_"))
base = pd.read_csv(RAIZ / "datos" / "ejemplo.csv")

# Datos "no vistos": otras columnas, otras etiquetas de fuente y 4 fuentes
nuevo = base.rename(columns={"comentario": "review_text", "plataforma": "canal"})
nuevo["canal"] = nuevo["canal"].map({"sectur": "dmo", "tripadvisor": "google_reviews", "instagram": "blog_viajes"})
idx = nuevo[nuevo.canal == "google_reviews"].index[::2]
nuevo.loc[idx, "canal"] = "foro"
csv4 = tmp / "datos_nuevos.csv"
nuevo.to_csv(csv4, index=False)

titulo = "Verificación con datos nuevos"
args = ["--csv", str(csv4), "--columna_texto", "review_text", "--columna_fuente", "canal", "--etiqueta_dmo", "dmo",
        "--idioma", "es", "--titulo", titulo, "--paleta", "cividis", "--salida", str(tmp / "salidas")]
rc, log = correr(args)
ok("CLI: corre con los 7 parámetros obligatorios", rc == 0, log.strip().splitlines()[-1] if rc == 0 else log[-400:])
carpeta = next((tmp / "salidas").glob("*_es"), None)
R = json.load(open(carpeta / "resultados.json")) if carpeta else {}
D = pd.read_parquet(carpeta / "corpus_procesado.parquet") if carpeta else pd.DataFrame()
P = R.get("parametros", {})
ok("CLI: registra los 7 parámetros", all(P.get(k) for k in ["csv", "columna_texto", "columna_fuente", "etiqueta_dmo", "idioma", "titulo", "paleta"]),
   f"idioma={P.get('idioma')}, paleta={P.get('paleta')}")

# 1. Limpieza y preprocesamiento
ok("1. Limpieza: sin URLs, menciones, emojis, números ni signos en el texto procesado",
   not any(re.search(r"https?://|www\.|@|\d|[^\w\s]", t) for t in D.lemas))
ok("1. Tokenización, palabras vacías y lematización", D.lemas.str.len().gt(0).all() and "n_tokens" in D)
ok("1. Se preserva la etiqueta de fuente", set(D.fuente) == {"dmo", "google_reviews", "blog_viajes", "foro"}, ", ".join(sorted(set(D.fuente))))

# 2. Atípicos
OG = R.get("outliers_global", {})
ok("2. Atípicos detectados (Isolation Forest sobre la base unificada)", D.outlier.sum() > 0, f"{int(D.outlier.sum())} atípicos")
ok("2. Unigramas, bigramas y trigramas de los atípicos", all(OG.get(k) for k in ("unigramas", "bigramas", "trigramas")),
   f"bigrama más frecuente: {OG.get('bigramas', [['-']])[0][0]}")
ok("2. Sólo los normales pasan al paso 3", D[D.outlier].sentimiento.isna().all() and D[~D.outlier].sentimiento.notna().all())

# 3. Sentimiento
ok("3. Clasificación binaria positivo/negativo", set(D[~D.outlier].sentimiento) <= {"positivo", "negativo"})
ok("3. Dos grupos con etiqueta de fuente", all(R["topicos"][s].get("n", 0) > 0 for s in ("positivo", "negativo")))

# 4. Tópicos por sentimiento (o frecuencias bajo el umbral)
ok("4. Tópicos o frecuencias en positivos y negativos",
   all(R["topicos"][s]["tipo"] in ("topicos", "frecuencias") for s in ("positivo", "negativo")),
   ", ".join(f"{s}: {R['topicos'][s]['tipo']}" for s in ("positivo", "negativo")))
rc2, _ = correr(args[:-2] + ["--salida", str(tmp / "umbral"), "--umbral_topicos", "100000"])
R2 = json.load(open(next((tmp / "umbral").glob("*_es")) / "resultados.json")) if rc2 == 0 else {}
ok("4. Condición especial: con el umbral alto se usan frecuencias de palabras",
   rc2 == 0 and all(R2["topicos"][s]["tipo"] == "frecuencias" for s in ("positivo", "negativo")))
FT, FT2 = R.get("frecuencias_fuente_tono", {}), R2.get("frecuencias_fuente_tono", {})
html2 = (next((tmp / "umbral").glob("*_es")) / "reporte.html").read_text(encoding="utf-8") if rc2 == 0 else ""
ok("4. Nubes de palabras por fuente y tono (todas bajo el umbral alto) en el reporte",
   set(FT) == set(D.fuente) and all(set(v) == {"positivo", "negativo"} for v in FT.values())
   and all(c["bajo_umbral"] for v in FT2.values() for c in v.values())
   and html2.count("data:image/png;base64") >= len(FT2), f"{html2.count('data:image/png;base64')} nubes en el reporte")

# 5. Comparación DMO vs. percibida
C = R.get("comparacion", {})
ok("5. Comparación de tópicos DMO vs. agregado (y por fuente)", C.get("temas") and all("pct_por_fuente" in t for t in C["temas"]),
   f"{len(C.get('temas', []))} temas comparados")
ok("5. Comparación de sentimiento", C.get("sentimiento", {}).get("pct_positivo_dmo") is not None)
ok("5. Índice de alineación semántica", 0 <= C.get("similitud", {}).get("ias", -1) <= 1, f"IAS = {C.get('similitud', {}).get('ias')}")
ok("5. Tabla por fuente (tópicos principales y tono)",
   {r["fuente"] for r in C.get("por_fuente", [])} == set(D.fuente) and all("pct_positivo" in r for r in C["por_fuente"]))

# 6. Reporte
tops = [t for s in ("positivo", "negativo") if R["topicos"][s]["tipo"] == "topicos" for t in R["topicos"][s]["topicos"]]
ok("6. Palabras clave por tópico indicando la fuente", tops and all(t.get("palabras") and t.get("palabras_por_fuente") for t in tops))
ok("6. Comentario representativo por tópico (centroide)", tops and all(t.get("representativo", {}).get("texto") for t in tops))
ok("6. Resumen de brechas", len(R.get("resumen_brechas", [])) > 0)
html = (carpeta / "reporte.html").read_text(encoding="utf-8") if carpeta else ""
ok("6. Reporte HTML generado", "Resumen de brechas" in html and "Comentarios atípicos" in html)

# 7. Visualizaciones
ok("7. Gráficas interactivas en el reporte (4)", html.count("plotly-graph-div") >= 4, f"{html.count('plotly-graph-div')} gráficas")
ok("7. Dispersión por tópico (positivos y negativos) y por fuente", "Comentarios positivos" in html and "Comentarios negativos" in html)
ok("7. Codificación redundante color + forma", '"symbol":"square"' in html.replace(" ", "") or "square" in html)
ok("7. Hover con el comentario", '"hoverinfo":"text"' in html.replace(" ", ""))

# 8. Concepto precio/valor/costo
CC = R.get("concepto", {})
ok("8. Similitud semántica con el concepto", D[~D.outlier].sim_concepto.notna().all())
ok("8. Comparación DMO vs. percibida (frecuencia, tono, contexto)",
   all(k in CC.get("por_grupo", {}) for k in ("DMO", "Percibida")) and "contexto_palabras" in CC["por_grupo"]["DMO"])
ok("8. Los 5 más cercanos con su fuente", len(CC.get("top5_global", [])) == 5 and all(x.get("fuente") for x in CC["top5_global"]))

# Número de temas elegido solo y reportado
CJ = R["topicos"]["conjunto"]
ok("4. El número de temas se determina solo y se reporta",
   CJ.get("tipo") == "topicos" and CJ.get("k") in [e["k"] for e in CJ.get("evaluacion_k", [])] and len(CJ["evaluacion_k"]) > 1
   and "Temas encontrados" in log and "Temas:" in html, f"k = {CJ.get('k')} (probados {len(CJ.get('evaluacion_k', []))})")

# 5. DMO frente a cada fuente por separado (cuantitativo y cualitativo)
IND = C.get("dmo_vs_cada_fuente", {})
perc = sorted(set(D.fuente) - {"dmo"})
ok("5. DMO frente a cada fuente: cifras (temas con IC, tono con χ², parecido, agenda)",
   sorted(IND) == perc and all(all({"pct_dmo", "pct_fuente", "brecha_ic95", "clase"} <= set(t) for t in c["temas"])
                               and c["tono"]["pct_positivo_fuente"] is not None and 0 <= c["parecido"]["valor"] <= 1
                               and 0 <= c["coincidencia_agenda"] <= 1 for c in IND.values()),
   ", ".join(f"{f}: parecido {c['parecido']['valor']:.2f}" for f, c in IND.items()))
ok("5. DMO frente a cada fuente: palabras propias de cada lado, ejemplos y frases",
   all(c["palabras_de_la_fuente"] and c["resumen"] and any(t["ejemplos_fuente"] for t in c["temas"]) for c in IND.values())
   and "DMO frente a cada fuente" in html)

# Respuesta a la pregunta del proyecto y decisiones para la DMO (generadas para estos datos nuevos)
CO = R.get("conclusiones", {})
ok("6. Conclusiones: responde la pregunta del proyecto y propone decisiones con evidencia",
   bool(CO.get("respuesta")) and len(CO.get("decisiones", [])) >= 2 and all(d.get("evidencia") and d.get("accion") for d in CO["decisiones"])
   and "Conclusiones para la DMO" in html, f"{len(CO.get('decisiones', []))} decisiones · {CO.get('respuesta', '')[:80]}…")

# BM25
sys.path.insert(0, str(RAIZ))
from pipeline.bm25 import BM25  # noqa: E402
bm = BM25(["taco comida barato", "museo historia arte", "taco taco taco caro precio", "metro transporte"])
p_bm = bm.puntajes("taco precio")
ok("BM25: ordena por las palabras de la consulta (y da 0 a los que no las usan)",
   p_bm[2] > p_bm[0] > 0 and p_bm[1] == 0 and p_bm[3] == 0 and bm.mejores("taco precio", k=5) == [2, 0])
ok("BM25: complemento del concepto (mención literal) y ejemplos por tema",
   "bm25_concepto" in D and all("pct_mencionan" in v for v in CC.get("por_grupo", {}).values()))

# Archivos sueltos de cualquier formato: uno por fuente
sep_dir = tmp / "archivos"
sep_dir.mkdir()
partes = {f: g.review_text.reset_index(drop=True) for f, g in nuevo.groupby("canal")}
pd.DataFrame({"texto_oficial": partes["dmo"], "categoria": "turismo"}).to_excel(sep_dir / "dmo.xlsx", index=False)
pd.DataFrame({"opinion": partes["google_reviews"]}).to_json(sep_dir / "google_reviews.json", orient="records", force_ascii=False)
(sep_dir / "blog_viajes.txt").write_text("\n".join(t.replace("\n", " ") for t in partes["blog_viajes"]), encoding="utf-8")
pd.DataFrame({"titulo": partes["foro"].str[:40], "cuerpo": partes["foro"]}).to_csv(sep_dir / "foro.tsv", sep="\t", index=False)
rc7, log7 = correr(["--csv", *map(str, [sep_dir / "dmo.xlsx", sep_dir / "google_reviews.json", sep_dir / "blog_viajes.txt",
                                       sep_dir / "foro.tsv"]),
                    "--columna_texto", "texto", "--columna_fuente", "fuente", "--etiqueta_dmo", "dmo", "--idioma", "es",
                    "--titulo", "Archivos sueltos", "--paleta", "okabe_ito", "--salida", str(tmp / "sueltos")])
R7 = json.load(open(next((tmp / "sueltos").glob("*_es")) / "resultados.json")) if rc7 == 0 else {}
ok("Archivos: 4 archivos de formatos distintos (xlsx, json, txt, tsv), uno por fuente, con paleta Okabe-Ito",
   rc7 == 0 and set(R7.get("conteos", {})) == {"dmo", "google_reviews", "blog_viajes", "foro"},
   ", ".join(f"{f} {c['total']}" for f, c in R7.get("conteos", {}).items()) if rc7 == 0 else log7[-300:])
rc8, log8 = correr(["--csv", str(sep_dir / "dmo.xlsx"), str(sep_dir / "blog_viajes.txt"), "--columna_texto", "texto",
                    "--columna_fuente", "fuente", "--etiqueta_dmo", "dmo", "--idioma", "es", "--titulo", "Dos archivos",
                    "--paleta", "okabe_ito", "--salida", str(tmp / "dos_archivos")])
ok("Archivos: con sólo dos archivos (DMO y una fuente)", rc8 == 0, log8[-300:] if rc8 else "")

# Tablero: modo ejemplo sin errores en ninguna pestaña (los resultados de salidas/)
try:
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=180)
    at.run()
    at.sidebar.radio[0].set_value("Ejemplo: Ciudad de México").run()
    pest = [t.label for t in at.tabs]
    ok("Tablero: modo ejemplo abre sus 9 pestañas sin errores (la primera, «Conclusiones»)",
       not at.exception and len(pest) >= 9 and pest[0] == "Conclusiones", ", ".join(pest))
    at2 = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    at2.run()
    ok("Tablero: modo «Subir mis archivos» muestra la carga de archivos, con Sectur ya cargada como DMO", not at2.exception and
       any("dos o más archivos" in m.value for m in at2.markdown) and any("Sectur" in c.label and c.value for c in at2.checkbox))
except Exception as e:  # noqa: BLE001
    ok("Tablero: pruebas automáticas", False, repr(e)[:300])

# Agnóstico al número y nombre de fuentes: sólo 2 fuentes
dos = nuevo[nuevo.canal.isin(["dmo", "blog_viajes"])]
csv2 = tmp / "dos_fuentes.csv"
dos.to_csv(csv2, index=False)
rc3, log3 = correr(["--csv", str(csv2), "--columna_texto", "review_text", "--columna_fuente", "canal", "--etiqueta_dmo", "dmo",
                    "--idioma", "es", "--titulo", "Dos fuentes", "--paleta", "viridis", "--salida", str(tmp / "dos")])
ok("Agnóstico: funciona con 4 fuentes y con sólo 2", rc == 0 and rc3 == 0, log3[-300:] if rc3 else "")

# Errores claros
rc4, log4 = correr(["--csv", str(csv4), "--columna_texto", "no_existe", "--columna_fuente", "canal", "--etiqueta_dmo", "dmo",
                    "--idioma", "es", "--titulo", "x", "--paleta", "viridis", "--salida", str(tmp / "e1")])
rc5, log5 = correr(["--csv", str(csv4), "--columna_texto", "review_text", "--columna_fuente", "canal", "--etiqueta_dmo", "sectur",
                    "--idioma", "es", "--titulo", "x", "--paleta", "viridis", "--salida", str(tmp / "e2")])
ok("Errores claros: columna inexistente y etiqueta de DMO inexistente",
   rc4 != 0 and "no existe" in log4 and rc5 != 0 and "No hay registros" in log5)

# Sin conexión: se bloquea la red apuntando el proxy a un puerto cerrado
sin_red = os.environ.copy()
for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    sin_red[v] = "http://127.0.0.1:9"
sin_red["NO_PROXY"] = sin_red["no_proxy"] = ""
rc6, log6 = correr(args[:-2] + ["--salida", str(tmp / "offline")], sin_red)
ok("Sin APIs externas: corre con la red bloqueada", rc6 == 0, log6[-300:] if rc6 else "")

# Repositorio
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
ok("Repositorio: requirements.txt, README con ejemplos y CSV de ejemplo",
   (RAIZ / "requirements.txt").exists() and (RAIZ / "datos" / "ejemplo.csv").exists() and
   all(f"--{k}" in readme for k in ["csv", "columna_texto", "columna_fuente", "etiqueta_dmo", "idioma", "titulo", "paleta"]))
ok("Repositorio: CSV de ejemplo anonimizado (sin menciones ni enlaces)",
   not base.comentario.str.contains(r"@(?!usuario)\w|https?://", regex=True).any())

ancho = max(len(r) for r, _, _ in resultados)
for req, bien, det in resultados:
    print(f"{'✓' if bien else '✗'}  {req.ljust(ancho)}  {det}")
fallas = sum(not b for _, b, _ in resultados)
print(f"\n{len(resultados) - fallas} de {len(resultados)} comprobaciones correctas. Carpeta de prueba: {tmp}")
sys.exit(1 if fallas else 0)
