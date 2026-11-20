"""Paso 6. Reporte HTML autocontenido (se abre sin conexión) con los resultados clave."""
import html


def _e(x):
    return html.escape(str(x))


def _tabla(filas, columnas):
    cab = "".join(f"<th>{_e(c)}</th>" for c in columnas)
    cuerpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table>"


def _topicos(res, titulo):
    if res.get("tipo") == "frecuencias":
        pal = ", ".join(f"{_e(w)} ({n})" for w, n in res["frecuencias"])
        return f"<h3>{_e(titulo)}</h3><p>Partición con {res['n']} comentarios: por debajo del umbral, se muestran las palabras más frecuentes.</p><p>{pal}</p>"
    filas = []
    for t in res["topicos"]:
        rep = t["representativo"] or {}
        mezcla = ", ".join(f"{_e(f)} {n}" for f, n in sorted(t["mezcla_fuentes"].items(), key=lambda x: -x[1]))
        por_f = "<br>".join(f"<b>{_e(f)}:</b> {_e(', '.join(w[:5]))}" for f, w in t.get("palabras_por_fuente", {}).items())
        filas.append([f"T{t['id'] + 1}", _e(", ".join(t["palabras"])) + (f"<br><small>{por_f}</small>" if por_f else ""), t["n"], mezcla,
                      f"<i>{_e(rep.get('texto', ''))}</i><br><small>Fuente: {_e(rep.get('fuente', ''))}</small>"])
    extra = ""
    for f, fr in res.get("fuentes_pequenas", {}).items():
        extra += f"<p><b>{_e(f)}</b> tiene {fr['n']} comentarios en esta partición; palabras más frecuentes: " + \
                 ", ".join(f"{_e(w)} ({n})" for w, n in fr["frecuencias"]) + "</p>"
    return f"<h3>{_e(titulo)} ({res['k']} tópicos)</h3>" + _tabla(filas, ["Tópico", "Palabras clave (y por fuente de origen)", "Comentarios", "Fuentes", "Comentario representativo"]) + extra


def _nubes(res, nubes):
    """Cuadrícula tono × fuente. Las particiones por debajo del umbral se describen así en lugar de con tópicos."""
    frec = res.get("frecuencias_fuente_tono") or {}
    if not frec or not nubes:
        return ""
    dmo = res["parametros"]["etiqueta_dmo"]
    fuentes = [f for f in nubes if f in frec]
    umbral = res["parametros"].get("umbral_topicos")
    cab = "<tr><th></th>" + "".join(f"<th>{_e(f)}{' (DMO)' if f == dmo else ''}</th>" for f in fuentes) + "</tr>"
    filas = ""
    for s, nom in (("positivo", "Positivos"), ("negativo", "Negativos")):
        celdas = ""
        for f in fuentes:
            d, img = frec[f][s], nubes[f].get(s)
            marca = (f"<br><b>n = {d['n']} &lt; {umbral}: palabras más frecuentes en lugar de tópicos</b>" if d["bajo_umbral"] else "")
            lista = ", ".join(f"{_e(w)} ({c})" for w, c in d["frecuencias"][:12])
            imagen = f"<img src='data:image/png;base64,{img}' style='width:100%;border:1px solid #ddd;border-radius:6px'>" if img else "<i>sin comentarios</i>"
            celdas += f"<td>{imagen}<small>n = {d['n']}{marca}<br>{lista}</small></td>"
        filas += f"<tr><th>{nom}</th>{celdas}</tr>"
    return ("<h3>Palabras más frecuentes por fuente y tono</h3><p>El tamaño de cada palabra indica su frecuencia; los conteos "
            f"exactos van debajo. Con menos de {umbral} comentarios, ésta es la descripción de la partición.</p>"
            f"<table style='table-layout:fixed'>{cab}{filas}</table>")


def _por_fuente_individual(comp):
    """DMO frente a cada fuente: cifras, frases, palabras propias y ejemplos BM25 por tema."""
    html = ""
    for f, c in (comp.get("dmo_vs_cada_fuente") or {}).items():
        to = c["tono"]
        chi = to.get("prueba_chi2")
        chi_txt = f" (χ² = {chi['chi2']:.1f}, p = {chi['p_valor']:.3g})" if chi else ""
        filas = [[_e(t["etiqueta"]), f"{t['pct_dmo']:.1f} %", f"{t['pct_fuente']:.1f} %",
                  f"{t['brecha_pp']:+.1f} <small>[{t['brecha_ic95'][0]:+.1f}, {t['brecha_ic95'][1]:+.1f}]</small>", _e(t["clase"]),
                  _e(", ".join(t.get("palabras_dmo", [])[:5])), _e(", ".join(t.get("palabras_fuente", [])[:5])),
                  "<br>".join(f"<i>{_e(x[:180])}</i>" for x in t.get("ejemplos_fuente", [])[:1])]
                 for t in sorted(c["temas"], key=lambda t: -abs(t["brecha_pp"]))]
        html += (f"<h3>DMO frente a {_e(f)} ({c['n']} comentarios)</h3>"
                 f"<p>Parecido del contenido: <b>{c['parecido']['valor']:.2f}</b> (IC 95 % {c['parecido']['ic95'][0]:.2f}–"
                 f"{c['parecido']['ic95'][1]:.2f}) · coincidencia de agenda: <b>{c['coincidencia_agenda']:.2f}</b> · "
                 f"positivos: DMO {to['pct_positivo_dmo']:.0f} %, {_e(f)} {to['pct_positivo_fuente']:.0f} %{chi_txt}</p>"
                 f"<ul>{''.join(f'<li>{_e(x)}</li>' for x in c.get('resumen', []))}</ul>"
                 f"<p><b>Palabras propias de {_e(f)}:</b> {_e(', '.join(w for w, _ in c.get('palabras_de_la_fuente', [])[:10]))}<br>"
                 f"<b>Palabras propias de la DMO:</b> {_e(', '.join(w for w, _ in c.get('palabras_de_la_dmo', [])[:10]))}</p>"
                 + _tabla(filas, ["Tema", "DMO", _e(f), "Brecha (pp) [IC 95 %]", "Lectura", "Palabras de la DMO",
                                  f"Palabras de {_e(f)}", f"Ejemplo de {_e(f)} (BM25)"]))
    return html


def generar(res, figs, ruta, titulo, nubes=None):
    p = res["parametros"]
    conteo = [[_e(f), c["total"], c["en_idioma"], c["outliers"], c["analizados"]] for f, c in res["conteos"].items()]
    brechas = "".join(f"<li>{_e(b)}</li>" for b in res["resumen_brechas"])
    fig_html = []
    for i, (k, fig) in enumerate(figs.items()):
        fig_html.append(fig.to_html(full_html=False, include_plotlyjs=(i == 0), config={"displaylogo": False}))
    comp = res["comparacion"]
    filas_temas = [[f"T{t['id'] + 1}", _e(t["etiqueta"]), f"{t['pct_dmo']:.1f} %", f"{t['pct_percibida']:.1f} %",
                    f"{t['brecha_pp']:+.1f} <small>[{t['brecha_ic95'][0]:+.1f}, {t['brecha_ic95'][1]:+.1f}]</small>", _e(t["clase"]),
                    _e(", ".join(t.get("palabras_dmo", [])[:5])), _e(", ".join(t.get("palabras_percibida", [])[:5])),
                    "" if t["pct_negativo_percibida"] is None else f"{t['pct_negativo_percibida']:.1f} %"] for t in comp["temas"]]
    filas_fuente = []
    for r in comp["por_fuente"]:
        temas = "; ".join(f"{_e(x['etiqueta'])} ({x['pct']:.0f} %)" for x in r.get("temas_principales", []))
        filas_fuente.append([_e(r["fuente"]) + (" (DMO)" if r["es_dmo"] else ""), r["n"], temas, f"{r['pct_positivo']:.1f} %",
                             "" if r["ias"] is None else f"{r['ias']:.2f}"])
    out_html = ""
    og = res.get("outliers_global", {})
    if og.get("n"):
        ngg = lambda lst: ", ".join(f"{_e(t)} ({c})" for t, c in lst[:10])
        out_html += (f"<h3>Toda la base unificada: {og['n']} atípicos de {og['n_total']} comentarios ({og['pct']} %)</h3>"
                     f"<p>Un solo Isolation Forest para toda la base; corte por fuente. Por fuente: "
                     f"{_e(', '.join(f'{f} {n}' for f, n in og['por_fuente'].items()))}. Con un corte único serían: "
                     f"{_e(', '.join(f'{f} {n}' for f, n in og['si_corte_unico'].items()))}.</p>"
                     f"<p><b>Unigramas:</b> {ngg(og['unigramas'])}<br><b>Bigramas:</b> {ngg(og['bigramas'])}<br>"
                     f"<b>Trigramas:</b> {ngg(og['trigramas'])}<br><b>Palabras que más los distinguen:</b> "
                     f"{', '.join(_e(w) for w, _ in og['distintivas'][:12])}</p>")
    for f, o in res["outliers"].items():
        if not o.get("n"):
            continue
        ng = lambda lst: ", ".join(f"{_e(t)} ({c})" for t, c in lst[:6])
        ej = "".join(f"<li><i>{_e(x['texto'][:250])}</i></li>" for x in o["ejemplos"][:3])
        out_html += (f"<h3>{_e(f)}: {o['n']} atípicos ({o['pct']} %)</h3><p><b>Unigramas:</b> {ng(o['unigramas'])}<br>"
                     f"<b>Bigramas:</b> {ng(o['bigramas'])}<br><b>Trigramas:</b> {ng(o['trigramas'])}<br>"
                     f"<b>Palabras que más los distinguen:</b> {', '.join(_e(w) for w, _ in o['distintivas'][:10])}</p><ul>{ej}</ul>")
    conc = res["concepto"]
    filas_conc = [[_e(g), v["n"], f"{v['pct_ligados']:.1f} %", "" if v["pct_positivo_ligados"] is None else f"{v['pct_positivo_ligados']:.0f} %",
                   _e(", ".join(w for w, _ in v["contexto_palabras"][:8]))] for g, v in conc["por_grupo"].items()]
    top5 = "".join(f"<li><b>{_e(x['fuente'])}</b> ({x['similitud']:.2f}, {_e(x['sentimiento'])}): <i>{_e(x['texto'][:250])}</i></li>" for x in conc["top5_global"])
    sim = comp["similitud"]
    _c = (comp.get("temas_resumen") or {}).get("congruencia_tematica")
    _cong = f"{_c:.2f}" if _c is not None else "—"
    if not comp["temas"]:
        conj = res["topicos"]["conjunto"]
        filas_temas = [["—", _e(", ".join(f"{w} ({n})" for w, n in conj.get("frecuencias", [])[:20])), "", "", "", "Pocos comentarios: palabras más frecuentes", "", "", ""]]

    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{_e(titulo)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1180px;margin:0 auto;padding:24px;color:#1b1e26}}
h1{{font-size:28px}}h2{{margin-top:36px;border-bottom:2px solid #1b1e26;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}}th,td{{border-bottom:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}}
th{{background:#f4f5f8}}small{{color:#666}}.k{{display:flex;gap:16px;flex-wrap:wrap}}.k div{{background:#f4f5f8;padding:10px 14px;border-radius:8px}}
.k b{{display:block;font-size:22px}}</style></head><body>
<h1>{_e(titulo)}</h1>
<p>Idioma del análisis: <b>{_e(p['idioma'])}</b> · DMO: <b>{_e(p['etiqueta_dmo'])}</b> · Paleta: {_e(p['paleta'])} ·
Temas: <b>{res['topicos']['conjunto'].get('k', '—')}</b> en común, {res['topicos']['positivo'].get('k', '—')} positivos,
{res['topicos']['negativo'].get('k', '—')} negativos ({'fijado por el usuario' if p.get('k_topicos') else 'elegidos automáticamente'})</p>
<div class="k"><div><b>{sim['ias']:.2f}</b>alineación semántica (IC 95 % {sim['ic95'][0]:.2f}–{sim['ic95'][1]:.2f})</div>
<div><b>{_cong}</b>congruencia temática</div>
<div><b>{comp['sentimiento']['pct_positivo_dmo']:.0f} % / {comp['sentimiento']['pct_positivo_percibida']:.0f} %</b>positivos DMO / percibida</div></div>
<h2>Resumen de brechas</h2><ul>{brechas}</ul>
<h2>Comentarios por fuente</h2>{_tabla(conteo, ["Fuente", "Total", "En el idioma del análisis", "Atípicos", "Analizados"])}
<h2>Comparación de temas: DMO frente a imagen percibida</h2>
{_tabla(filas_temas, ["Tópico", "Palabras", "DMO", "Percibida", "Brecha (pp) [IC 95 %]", "Lectura", "Palabras de la DMO", "Palabras de los visitantes", "Negativos (percibida)"])}
<h2>DMO frente a cada fuente</h2>{_por_fuente_individual(comp)}
<h2>Por fuente</h2>{_tabla(filas_fuente, ["Fuente", "Comentarios", "Temas principales", "Positivos", "Alineación con la DMO"])}
<h2>Tópicos por sentimiento</h2>{_topicos(res['topicos']['positivo'], 'Comentarios positivos')}{_topicos(res['topicos']['negativo'], 'Comentarios negativos')}{_nubes(res, nubes)}
<h2>Visualizaciones</h2>{''.join(fig_html)}
<h2>Precio, valor y costo</h2><p>Consulta: «{_e(conc['consulta'])}». Términos más cercanos en el corpus: {_e(', '.join(w for w, _ in conc['terminos_cercanos'][:15]))}.</p>
{_tabla(filas_conc, ["Grupo", "Comentarios", "Ligados al concepto", "Positivos entre ligados", "Contexto (palabras distintivas)"])}
<p>Comentarios que usan literalmente las palabras (BM25 &gt; 0): {_e(', '.join(f"{g} {v.get('pct_mencionan', 0):.1f} %" for g, v in conc['por_grupo'].items()))}.</p>
<h3>Los 5 comentarios más cercanos al concepto</h3><ol>{top5}</ol>
<h2>Comentarios atípicos</h2>{out_html}
</body></html>"""
    ruta.write_text(doc, encoding="utf-8")
