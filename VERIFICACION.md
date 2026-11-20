# Verificación de requisitos

Para comprobar todo de nuevo, en cualquier computadora con el repositorio instalado:

```bash
python verificar_requisitos.py
```

El script prueba el analizador con datos **que no ha visto**, construidos a partir de `datos/ejemplo.csv`:
- un CSV con columnas `review_text` y `canal` y fuentes `dmo`, `google_reviews`, `blog_viajes` y `foro`;
- los mismos datos como **4 archivos sueltos de formatos distintos** (`dmo.xlsx`, `google_reviews.json`, `blog_viajes.txt`, `foro.tsv`) y como sólo 2 archivos;
- el tablero, abierto con las herramientas de prueba de Streamlit.

Resultado: **43 de 43 comprobaciones correctas**.

| Requisito | Dónde se cumple | Comprobación |
|---|---|---|
| CLI con los 7 parámetros | `analizador.py` (argparse) | Corre con columnas y fuentes nuevas; registra los 7 parámetros en `resultados.json` |
| Cualquier archivo, mínimo dos, y tablero con esos archivos | `pipeline/lectura.py`, `app.py` («Subir mis archivos»), `analizador.py --csv a b c` | xlsx, json, txt y tsv (uno por fuente) y sólo dos archivos; también csv, jsonl, parquet, xls y .gz. En el tablero, los 4 archivos originales se subieron, se configuraron y se analizaron sin errores. Con Sectur ya cargada como DMO, basta con subir los 3 archivos de visitantes y presionar «Analizar» (sin tocar ajustes): el resultado es idéntico al del ejemplo |
| Número de temas determinado por el análisis y reportado | `pipeline/topicos.py`, Resumen del tablero, reporte y terminal | Se prueban de 5 a 15 temas y se elige por coherencia NPMI × diversidad; el número aparece en el tablero, en el reporte y al final de la terminal |
| 1. Limpieza, tokenización, palabras vacías, lematización y etiqueta de fuente | `pipeline/preprocesamiento.py` | Sin URLs, menciones, emojis, números ni signos en el texto procesado; las fuentes nuevas se conservan |
| 2. Atípicos con una técnica vista en clase + uni, bi y trigramas; sólo los normales siguen | `pipeline/outliers.py` | Isolation Forest único sobre la base unificada; n-gramas de toda la base y por fuente; los atípicos no tienen tono |
| 3. Sentimiento binario y dos grupos con su fuente | `pipeline/sentimiento.py` | Todos los normales son «positivo» o «negativo» |
| 4. Tópicos por sentimiento; frecuencias bajo un umbral | `pipeline/topicos.py`, `pipeline/nubes.py`, `--umbral_topicos` | Con un umbral alto, ambos grupos pasan a frecuencias; el reporte trae una nube de palabras por fuente y tono |
| 5. Comparación de tópicos, sentimiento, similitud global y tabla por fuente | `pipeline/comparacion.py` | Temas DMO vs. agregado y por fuente, χ² del tono, índice de alineación entre 0 y 1, tabla con todas las fuentes |
| 5. **DMO frente a cada fuente, cuantitativo y cualitativo** | `comparar_por_fuente`, pestaña «DMO vs. cada fuente» | Para cada fuente: temas con IC 95 %, tono con χ², parecido con IC, coincidencia de agenda, palabras propias de cada lado, palabras por tema, ejemplos BM25 y frases de resumen |
| BM25 | `pipeline/bm25.py` | Ordena por las palabras de la consulta y da 0 a los textos que no las usan; se usa en los ejemplos por tema, en el concepto y en el buscador |
| 6. Palabras clave por tópico con su fuente, comentario representativo y resumen de brechas | `resultados.json`, `reporte.html`, tablero | Cada tópico positivo y negativo trae `palabras_por_fuente` y su comentario más cercano al centroide |
| 7. Dispersión interactiva con color + forma, por tópico y por fuente, con hover; gráfica comparativa | `pipeline/visualizaciones.py`, pestaña «Explorar y buscar» | 4 gráficas en el reporte; la forma marca la fuente; el texto aparece al pasar el cursor |
| Paleta para daltonismo | `pipeline/visualizaciones.py`, barra lateral | Okabe-Ito (más la «muted» de Paul Tol para más de 8 categorías), viridis, cividis, plasma, inferno y magma; color y forma redundantes |
| 8. Concepto precio/valor/costo | `pipeline/concepto.py` | Similitud para todos los comentarios normales; frecuencia, tono y contexto por grupo; 5 comentarios con su fuente; mención literal con BM25 |
| Agnóstico a número y nombre de fuentes | Todo el pipeline | Funciona con 4 fuentes y con sólo 2 |
| Sin APIs externas | Todo el pipeline | Corre con la red bloqueada (proxy a un puerto cerrado) |
| Conclusiones para la DMO | `pipeline/conclusiones.py`, pestaña «Conclusiones», reporte y terminal | Con los datos nuevos responde la pregunta del proyecto y propone decisiones, cada una con acción y evidencia |
| Tablero | `app.py` | El modo ejemplo abre sus 9 pestañas sin errores, la primera «Conclusiones»; el modo «Subir mis archivos» muestra la carga, con Sectur ya cargada como DMO |
| Repositorio: README, requirements.txt y CSV de ejemplo anonimizado | Raíz del repositorio | README con ejemplos de todos los parámetros; CSV de ejemplo sin menciones ni enlaces |

## El resultado no depende de cómo se entreguen los archivos

Con los mismos comentarios, el resultado debe ser el mismo si llegan en un archivo unificado o en un archivo por fuente, en otro orden, con otros nombres o con las filas revueltas. Antes no era así: el muestreo, el Isolation Forest y el bootstrap dependían del orden de las filas y del nombre de las fuentes, y al subir las 4 bases al tablero salían 15 temas en lugar de 12. Ahora el análisis ordena las filas de forma canónica (DMO primero, luego las fuentes de más a menos comentarios y, dentro de cada una, por texto limpio) y usa un generador aleatorio por fuente.

Prueba: las 4 bases originales pasadas al script en otro orden (Reddit, Instagram, TripAdvisor, Sectur) y con sus nombres de archivo dan **los mismos 2,053 valores** que el archivo unificado (temas, atípicos, concepto, comparación e intervalos); sólo cambia el orden en que se listan las fuentes. Lo mismo al subirlas en el tablero (unos 3 minutos de análisis, sin errores).

## Atípicos: el número depende del método

Sobre la misma base unificada, el número de atípicos cambia mucho con el método y el umbral (medido en el Avance 2):

| Método | Atípicos |
|---|---|
| LOF con parámetros por defecto | 386 |
| Isolation Forest, contaminación 1.5 % | 428 |
| z-score de la longitud (\|z\| > 3) | 617 |
| Isolation Forest, contaminación automática | 0 |
| **Este proyecto** (un Isolation Forest para la base, corte de 3 % por fuente, corpus en español) | **682** en la versión final |

**Robustez (versión final).** Con tres contaminaciones distintas, las brechas principales se mantienen:

| Contaminación | Atípicos | Temas elegidos | DMO: parques | DMO: Centro Histórico | Tono positivo DMO / visitantes | Parecido global |
|---|---|---|---|---|---|---|
| 1 % | 229 | 12 | +18 pp | +15 pp | 98.4 % / 93.0 % | 0.55 |
| 2 % | 455 | 10 | +20 pp | +13 pp | 98.4 % / 93.0 % | 0.55 |
| 3 % | 682 | 15 | +18 pp | +13 pp | 98.4 % / 92.9 % | 0.55 |

En los tres casos los bigramas más frecuentes de los atípicos son casi los mismos («centro histórico», «pasar rato», «bello arte», «palacio bello», «tomar foto»), y lo que los visitantes mencionan más que la DMO también: la psicología y el autoconocimiento (una cuenta de Instagram), la explosión de la pipa en Iztapalapa (noticias) y la comida y la experiencia de la visita.

El número de temas elegido cambia con la muestra (12, 10 y 15), porque varios valores de k tienen una calidad parecida; por eso las conclusiones se apoyan en lo que se repite, no en un tema en particular.

**Segunda técnica.** En el Avance 2, LOF con el mismo corte de 3 % por fuente coincidió en 87 de 683 atípicos, cuando por azar se esperarían unos 21. Las dos técnicas detectan rarezas distintas:
- LOF busca puntos en zonas de baja densidad local.
- Isolation Forest busca puntos que se aíslan con pocos cortes.

Por eso el análisis se centra en **qué contienen** los atípicos, no en un número exacto.

## Otras comprobaciones

- **Número de temas.** Con k fijo en 7, 10, 12 y 15, las dos brechas principales de la DMO se mantienen: parques, de +18 a +24 pp, y Centro Histórico, de +13 a +25 pp (con k = 15, Chapultepec y Reforma se separan en un tema aparte, +9 pp). Del lado de los visitantes se repiten la psicología, Iztapalapa y la comida o la experiencia de la visita.
- **Limpieza de enlaces.** Se quitan los restos de enlaces que llegaron sin signos («https youtu be XSb9…»), que en el Avance 2 aparecían como palabras. También se quitan las palabras funcionales de otro idioma que se cuelan en comentarios mezclados («you», «and», «not»), que aparecían como palabras propias de Reddit.
- **Tablero con archivos subidos.** Se subieron las 4 bases originales con Playwright, se configuraron y se analizaron en otro orden y con TripAdvisor comprimido (.gz): unos 3 minutos, 9 pestañas sin errores, búsqueda BM25 funcionando y los mismos números que el ejemplo.
- **Reproducibilidad.** Con la semilla 42, dos corridas dan resultados idénticos.
