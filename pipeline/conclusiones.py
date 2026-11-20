"""Respuesta a la pregunta del proyecto y decisiones para la DMO, generadas a partir de los resultados.

Funciona con cualquier conjunto de archivos: sólo usa lo que calculan los pasos anteriores (temas, brechas con su
intervalo, tono, parecido, coincidencia de agenda, concepto) y reglas explícitas con umbrales fijos, que se
muestran junto con las conclusiones para que se puedan revisar. Las reglas no saben si un tema es turístico:
por eso cada decisión trae su evidencia (palabras del tema, fuentes y cifras) para que una persona la confirme.
"""

PREGUNTA = ("¿La imagen que proyecta la DMO coincide con la que perciben los visitantes? ¿En qué temas hay brechas "
            "y qué debería ajustar la DMO en su comunicación?")

# Umbrales de las reglas (se muestran en el tablero y en el reporte)
UMBRALES = {
    "parecido_alto": 0.70, "parecido_bajo": 0.45,          # coseno de centroides LSA
    "agenda_alta": 0.85, "agenda_baja": 0.70,              # 1 − Jensen-Shannon
    "quejas_x": 2.0,                                       # % negativo del tema ≥ 2 veces el % negativo general
    "concentrado": 0.85,                                   # una fuente aporta ≥ 85 % del peso del tema
    "tono_pp": 3.0,                                        # diferencia de tono mínima (y χ² con p < 0.05)
    "precio_x": 1.5,                                       # los visitantes hablan del concepto ≥ 1.5 veces más
    "prioridad_alta_pp": 10.0,                             # brecha de ≥ 10 puntos = prioridad alta
}


def _nombre(f, nombres):
    return (nombres or {}).get(f, str(f))


def _nivel(valor, alto, bajo):
    return "alto" if valor >= alto else ("bajo" if valor < bajo else "medio")


def _fuente_principal(t, perc):
    pf = {f: t.get("pct_por_fuente", {}).get(f, 0.0) for f in perc}
    total = sum(pf.values())
    if not total:
        return None, 0.0
    f = max(pf, key=pf.get)
    return f, pf[f] / total


def generar(res, nombres=None):
    """Devuelve {pregunta, respuesta, nivel, indicadores, decisiones, por_fuente, notas, umbrales}."""
    p = res.get("parametros", {})
    dmo = p.get("etiqueta_dmo")
    comp = res.get("comparacion", {})
    temas = comp.get("temas") or []
    resumen = comp.get("temas_resumen") or {}
    sent = comp.get("sentimiento") or {}
    sim = comp.get("similitud") or {}
    perc = resumen.get("fuentes_en_promedio") or [f for f in res.get("conteos", {}) if f != dmo]
    nom = lambda f: _nombre(f, nombres)
    U = UMBRALES

    parecido = sim.get("ias")
    agenda = resumen.get("congruencia_tematica")
    pos_dmo, pos_vis = sent.get("pct_positivo_dmo"), sent.get("pct_positivo_percibida")
    neg_base = (100 - pos_vis) if pos_vis is not None else None

    # ---- respuesta corta
    proy = sorted([t for t in temas if t["clase"] == "Proyectado, poco percibido"], key=lambda t: -t["brecha_pp"])
    perci = sorted([t for t in temas if t["clase"] == "Percibido, poco proyectado"], key=lambda t: t["brecha_pp"])
    coinc = sorted([t for t in temas if t["clase"] == "Coincidencia"], key=lambda t: -(t["pct_dmo"] + t["pct_percibida"]))
    if parecido is None:
        nivel, inicio = "sin datos", "No hay suficientes textos para responder con confianza."
    else:
        nivel = {"alto": "alta", "medio": "parcial", "bajo": "baja"}[_nivel(parecido, U["parecido_alto"], U["parecido_bajo"])]
        inicio = {"alta": "Sí, en general.", "parcial": "Sólo en parte.", "baja": "No."}[nivel]
    partes = [inicio]
    if agenda is not None and parecido is not None:
        a = _nivel(agenda, U["agenda_alta"], U["agenda_baja"])
        partes.append(
            ("La DMO y los visitantes reparten los temas de forma " + {"alto": "muy parecida", "medio": "parecida", "bajo": "distinta"}[a]
             + f" (coincidencia de agenda {agenda:.2f}), pero " if a != "bajo" else
             f"La DMO y los visitantes reparten los temas de forma distinta (coincidencia de agenda {agenda:.2f}), y ")
            + f"el contenido se parece {'mucho' if nivel == 'alta' else ('a medias' if nivel == 'parcial' else 'poco')} (parecido {parecido:.2f} de 1).")
    if proy:
        partes.append("La DMO destaca más " + ", ".join(f"«{t['etiqueta']}» ({t['pct_dmo']:.0f} % frente a {t['pct_percibida']:.0f} %)" for t in proy[:3]) + ".")
    perci_turismo = [t for t in perci if not (len(perc) > 1 and _fuente_principal(t, perc)[1] >= U["concentrado"])]
    if perci_turismo:
        partes.append("Los visitantes hablan más de " + ", ".join(f"«{t['etiqueta']}» ({t['pct_percibida']:.0f} % frente a {t['pct_dmo']:.0f} %)" for t in perci_turismo[:3]) + ".")
    conc = [t for t in perci if t not in perci_turismo]
    if conc:
        partes.append("Además circulan temas que vienen casi sólo de una fuente, como " + ", ".join(
            f"«{t['etiqueta']}» ({nom(_fuente_principal(t, perc)[0])})" for t in conc[:2]) + ".")
    if not proy and not perci and temas:
        partes.append("No hay brechas de temas mayores a 5 puntos con intervalo firme.")
    respuesta = " ".join(partes)

    indicadores = []
    if parecido is not None:
        indicadores.append({"nombre": "Parecido del contenido", "valor": f"{parecido:.2f}", "lectura": f"alineación {nivel}"})
    if agenda is not None:
        indicadores.append({"nombre": "Coincidencia de agenda", "valor": f"{agenda:.2f}",
                            "lectura": {"alto": "reparten igual los temas", "medio": "reparten parecido los temas", "bajo": "reparten distinto los temas"}[_nivel(agenda, U['agenda_alta'], U['agenda_baja'])]})
    if pos_dmo is not None and pos_vis is not None:
        indicadores.append({"nombre": "Tono positivo", "valor": f"{pos_dmo:.0f} % / {pos_vis:.0f} %", "lectura": "DMO / visitantes"})
    indicadores.append({"nombre": "Brechas firmes", "valor": str(len(proy) + len(perci)), "lectura": f"de {len(temas)} temas"})

    # ---- decisiones
    dec = []

    def agrega(tipo, titulo, evidencia, accion, prioridad, tema=None):
        dec.append({"tipo": tipo, "titulo": titulo, "evidencia": evidencia, "accion": accion, "prioridad": prioridad,
                    "palabras": (tema or {}).get("palabras", [])[:6]})

    for t in perci:
        f, share = _fuente_principal(t, perc)
        neg = t.get("pct_negativo_percibida")
        origen = f" Viene sobre todo de {nom(f)} ({100 * share:.0f} % del peso del tema)." if f and len(perc) > 1 and share >= 0.6 else ""
        ev = f"Visitantes {t['pct_percibida']:.0f} % del contenido; DMO {t['pct_dmo']:.0f} %." + (f" {neg:.0f} % de esos comentarios son negativos." if neg is not None else "") + origen
        prio = "Alta" if abs(t["brecha_pp"]) >= U["prioridad_alta_pp"] else "Media"
        if len(perc) > 1 and share >= U["concentrado"]:
            agrega("Vigilar", t["etiqueta"], ev, f"Casi todo viene de {nom(f)}: suele ser coyuntura (noticias) o contenido ajeno al destino. "
                   "Vigilarlo; comunicarlo sólo si es parte de la oferta turística.", "Media", t)
        elif neg is not None and neg_base and neg >= U["quejas_x"] * neg_base:
            agrega("Atender", t["etiqueta"], ev, f"Se comenta más que el promedio y con más quejas ({neg:.0f} % negativos frente a {neg_base:.0f} % en general). "
                   "Revisar los comentarios negativos: si es un problema del destino, atenderlo con los operadores e informar; si no es turismo, sólo vigilarlo.", prio, t)
        else:
            agrega("Incorporar", t["etiqueta"], ev, "Los visitantes lo valoran y la DMO casi no lo comunica: incorporarlo a la comunicación, "
                   "con el lenguaje que usan los visitantes.", prio, t)
    for t in proy:
        ev = f"DMO {t['pct_dmo']:.0f} % de su contenido; visitantes {t['pct_percibida']:.0f} %."
        agrega("Replantear", t["etiqueta"], ev, "La DMO invierte espacio en este tema y los visitantes casi no lo comentan: reforzarlo con contenido "
               "de experiencia (qué hacer, cuánto cuesta, cómo llegar) o reasignar parte de ese espacio a los temas que sí comentan.",
               "Alta" if t["brecha_pp"] >= U["prioridad_alta_pp"] else "Media", t)
    for t in coinc[:3]:
        neg = t.get("pct_negativo_percibida")
        ev = f"DMO {t['pct_dmo']:.0f} %; visitantes {t['pct_percibida']:.0f} %."
        if t.get("palabras_compartidas") is not None and t["palabras_compartidas"] <= 1:
            dmo_w, vis_w = ", ".join(t.get("palabras_dmo", [])[:3]), ", ".join(t.get("palabras_percibida", [])[:3])
            agrega("Ajustar enfoque", t["etiqueta"], ev + f" La DMO usa «{dmo_w}» y los visitantes «{vis_w}».",
                   "Pesan igual pero no es la misma conversación: contar el tema desde lo que valoran los visitantes.", "Media", t)
        elif neg is not None and neg_base and neg >= U["quejas_x"] * neg_base:
            agrega("Atender", t["etiqueta"], ev + f" {neg:.0f} % de comentarios negativos.", "Coinciden en el tema, pero los visitantes se quejan más que el promedio: revisar qué falla.", "Media", t)
        else:
            agrega("Mantener", t["etiqueta"], ev, "El mensaje sí llega: mantenerlo.", "Baja", t)

    # quejas más frecuentes (temas de la partición negativa)
    neg_t = res.get("topicos", {}).get("negativo", {})
    if neg_t.get("tipo") == "topicos" and neg_t.get("topicos"):
        tops = sorted(neg_t["topicos"], key=lambda t: -t.get("n", 0))[:3]
        txt = "; ".join(f"«{t['etiqueta']}» ({t.get('n', 0)} comentarios, sobre todo en {nom(max(t['mezcla_fuentes'], key=t['mezcla_fuentes'].get))})"
                        for t in tops if t.get("mezcla_fuentes"))
        agrega("Atender", "Quejas más frecuentes", f"Temas de los comentarios negativos: {txt}.",
               "Llevar estas quejas a los operadores (museos, parques, servicios) y publicar información práctica que las prevenga: "
               "horarios, precios, accesos.", "Alta")

    # tono
    prueba = sent.get("prueba_chi2_dmo_vs_percibida") or {}
    if pos_dmo is not None and pos_vis is not None:
        dif = pos_dmo - pos_vis
        sig = prueba.get("p_valor") is not None and prueba["p_valor"] < 0.05
        if dif >= U["tono_pp"] and sig:
            agrega("Ajustar tono", "La DMO es más positiva que los visitantes", f"Positivo: DMO {pos_dmo:.0f} %, visitantes {pos_vis:.0f} % (χ², p = {prueba['p_valor']:.3g}).",
                   "Incluir información práctica y realista para que las expectativas no se conviertan en quejas.", "Media")
        elif dif <= -U["tono_pp"] and sig:
            agrega("Aprovechar", "Los visitantes son más positivos que la DMO", f"Positivo: DMO {pos_dmo:.0f} %, visitantes {pos_vis:.0f} %.",
                   "Usar testimonios y reseñas de visitantes en la comunicación.", "Media")

    # concepto (precio, valor, costo u otro)
    cc = res.get("concepto") or {}
    pg = cc.get("por_grupo") or {}
    if "DMO" in pg and "Percibida" in pg:
        d, v = pg["DMO"]["pct_ligados"], pg["Percibida"]["pct_ligados"]
        concepto = p.get("concepto") or cc.get("consulta") or "el concepto"
        cerca = ", ".join(t[0] for t in (cc.get("terminos_cercanos") or [])[:5])
        if v >= U["precio_x"] * max(d, 0.1) and v >= 2:
            veces = f"{v / d:.1f} veces más" if d >= 0.5 else "la DMO casi no lo menciona"
            agrega("Informar", f"«{concepto}»", f"Lo mencionan {v:.1f} % de los visitantes y {d:.1f} % de la DMO ({veces})."
                   + (f" Palabras cercanas: {cerca}." if cerca else ""),
                   "Los visitantes hablan de esto mucho más que la DMO: publicar información clara al respecto (por ejemplo, precios y relación calidad-precio).", "Media")

    # por fuente
    ind = comp.get("dmo_vs_cada_fuente") or {}
    por_fuente = []
    for f, c in ind.items():
        mas = sorted([t for t in c["temas"] if t["clase"] == "Percibido, poco proyectado"], key=lambda t: t["brecha_pp"])[:1]
        to = c["tono"]
        por_fuente.append({
            "fuente": f, "parecido": c["parecido"]["valor"], "agenda": c["coincidencia_agenda"],
            "tono": round(to["pct_positivo_fuente"] - to["pct_positivo_dmo"], 1),
            "habla_mas_de": f"{mas[0]['etiqueta']} ({mas[0]['pct_fuente']:.0f} % vs. {mas[0]['pct_dmo']:.0f} %)" if mas else "—",
            "palabras": ", ".join(w for w, _ in c.get("palabras_de_la_fuente", [])[:5]),
        })
    por_fuente.sort(key=lambda x: x["parecido"])
    if len(por_fuente) > 1:
        lejos, cerca_f = por_fuente[0], por_fuente[-1]
        agrega("Canal", f"{nom(lejos['fuente'])} es donde la imagen más se aleja",
               f"Parecido con la DMO: {nom(lejos['fuente'])} {lejos['parecido']:.2f}; {nom(cerca_f['fuente'])} {cerca_f['parecido']:.2f}. "
               f"{nom(lejos['fuente'])} habla más de {lejos['habla_mas_de']}.",
               f"Adaptar el contenido para {nom(lejos['fuente'])} en lugar de repetir el mismo mensaje en todos los canales.", "Media")

    orden_tipo = {"Atender": 0, "Incorporar": 1, "Replantear": 2, "Informar": 3, "Ajustar enfoque": 4, "Ajustar tono": 5,
                  "Canal": 6, "Vigilar": 7, "Aprovechar": 8, "Mantener": 9}
    orden_prio = {"Alta": 0, "Media": 1, "Baja": 2}
    dec.sort(key=lambda d: (orden_prio[d["prioridad"]], orden_tipo.get(d["tipo"], 99)))

    notas = ["Las conclusiones salen de reglas fijas sobre los resultados; no saben si un tema es turístico. "
             "Revisa las palabras y los ejemplos de cada tema antes de decidir."]
    notas += list(res.get("advertencias") or [])
    return {"pregunta": PREGUNTA, "respuesta": respuesta, "nivel": nivel, "indicadores": indicadores, "decisiones": dec,
            "por_fuente": por_fuente, "notas": notas, "umbrales": UMBRALES}


def texto(c, nombres=None):
    """Las conclusiones como texto plano (terminal y descarga)."""
    lineas = ["PREGUNTA", c["pregunta"], "", "RESPUESTA", c["respuesta"], "", "DECISIONES PARA LA DMO"]
    for d in c["decisiones"]:
        lineas.append(f"- [{d['tipo']} · prioridad {d['prioridad'].lower()}] {d['titulo']}: {d['accion']} Evidencia: {d['evidencia']}")
    if c["por_fuente"]:
        lineas += ["", "POR FUENTE"]
        for x in c["por_fuente"]:
            lineas.append(f"- {_nombre(x['fuente'], nombres)}: parecido {x['parecido']:.2f}, agenda {x['agenda']:.2f}, tono {x['tono']:+.1f} puntos "
                          f"frente a la DMO; habla más de {x['habla_mas_de']}.")
    lineas += ["", "NOTAS"] + [f"- {n}" for n in c["notas"]]
    return "\n".join(lineas)
