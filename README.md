# Imagen del destino: proyectada (DMO) vs. percibida

Compara la imagen de un destino que proyecta su organización de marketing (DMO) con la que perciben los visitantes en otras fuentes (reseñas, redes sociales, foros). El caso de estudio es la Ciudad de México: **Sectur CDMX** (DMO) frente a **TripAdvisor**, **Instagram** y **Reddit**.

Funciona con **cualquier conjunto de archivos**: se suben dos o más (uno de la DMO y uno o más de visitantes), en CSV, TSV, TXT, Excel (xlsx, xls), JSON, JSONL o Parquet, y se genera el tablero de esos archivos. El número de temas lo determina el propio análisis.

El proyecto tiene dos piezas que usan el mismo código (`pipeline/analisis.py`):

- `app.py`, el tablero de Streamlit. En **«Subir mis archivos»** se cargan los archivos, se elige cuál es la DMO y el tablero corre los 8 pasos. En **«Ejemplo: Ciudad de México»** muestra el análisis ya hecho del caso.
- `analizador.py`, el mismo análisis desde la terminal. Acepta un archivo unificado o varios archivos (uno por fuente) y escribe los resultados en `salidas/`.

Todo corre sin conexión; no se usa ninguna API externa. El resultado no depende del orden en que se suban los archivos, de su nombre ni del orden de sus filas.

Proyecto final de Visualización de Datos. Alejandro Castillo Avalos, Ingeniería de Datos e Inteligencia Artificial, DICIS, Universidad de Guanajuato.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Tablero

```bash
streamlit run app.py
```

**Subir mis archivos.** Por cada archivo se propone automáticamente el nombre de la fuente (el nombre del archivo), las columnas de texto y, si existe, una columna con varios comentarios por celda (por ejemplo, las respuestas de un hilo de Reddit unidas con « - »), que se separan en comentarios individuales. Todo se puede cambiar. Después se elige cuál es la DMO, el idioma (se propone el más frecuente) y, si se quiere, palabras a ignorar. «Analizar» corre todo y muestra el tablero; el reporte HTML se descarga desde la barra lateral.

Para reproducir el caso CDMX, sube los 4 archivos de `datos/originales/`, renombra `instaUGC` como Instagram y `redditcdmx` como Reddit (opcional) y escribe en palabras a ignorar `mexico,ciudad,cdmx,df,city`. El resultado es idéntico al del ejemplo.

El tablero tiene nueve pestañas:

- **Conclusiones**: responde la pregunta del proyecto (¿la imagen que proyecta la DMO coincide con la que perciben los visitantes y qué debería ajustar?) con una respuesta corta, indicadores y **decisiones para la DMO** ordenadas por prioridad, cada una con su evidencia: replantear, incorporar, atender, informar, ajustar enfoque o tono, canal, vigilar y mantener. Se generan solas, con las mismas reglas, para cualquier conjunto de archivos (`pipeline/conclusiones.py`); los umbrales se muestran en la pestaña. También van en el reporte HTML, en la terminal y se descargan como texto.
- **Resumen**: comentarios por fuente, tono, parecido del contenido, coincidencia de agenda, **número de temas encontrados** y cómo se eligió, y hallazgos principales.
- **Proyectado vs. percibido**: cada tema en la DMO frente al promedio de visitantes, con su diferencia e intervalo.
- **DMO vs. cada fuente**: la DMO frente a cada fuente por separado. Cuantitativo: peso de cada tema y diferencia con IC 95 %, tono con χ², parecido y coincidencia de agenda. Cualitativo: frases de resumen, palabras propias de cada lado y, tema por tema, con qué palabras lo dice cada uno y ejemplos de cada lado elegidos con BM25.
- **Lo que gusta y lo que no**: tono por fuente, temas de cada tono y nubes de palabras por fuente y tono.
- **Por fuente**: temas principales y tono de cada fuente, y mapa de calor fuente × tema.
- **Explorar y buscar**: mapa de comentarios con color y forma, *hover* y selección con lazo, y **búsqueda BM25** (qué porcentaje de cada fuente usa las palabras buscadas y los comentarios más relevantes).
- **Precio, valor y costo**: cercanía semántica con la idea y, como complemento, mención literal con BM25.
- **Comentarios atípicos**: unigramas, bigramas y trigramas de toda la base y de cada fuente.

Paletas aptas para daltonismo: **Okabe-Ito** (por defecto; colores muy distintos entre sí, ampliada con la paleta «muted» de Paul Tol cuando hay más de 8 categorías) y viridis, cividis, plasma, inferno y magma. Cada fuente conserva siempre el mismo color y la misma forma; la DMO es siempre el cuadrado.

### Publicarlo en Streamlit Community Cloud

1. En [share.streamlit.io](https://share.streamlit.io), entra con la cuenta de GitHub dueña del repositorio.
2. «Create app» → elige el repositorio, la rama `main` y `app.py` como archivo principal.
3. En «Advanced settings» elige Python 3.11 o superior. Las dependencias salen de `requirements.txt`.

El repositorio es privado porque `datos/` y `salidas/` contienen publicaciones reales; la app desplegada desde un repositorio privado sólo la ven las cuentas invitadas.

## Uso desde la terminal (7 parámetros obligatorios)

```bash
python analizador.py \
  --csv datos/cdmx_unificado.csv.gz \
  --columna_texto texto \
  --columna_fuente fuente \
  --etiqueta_dmo sectur \
  --idioma es \
  --titulo "Imagen de la Ciudad de México" \
  --paleta viridis \
  --excluir "mexico,ciudad,cdmx,df,city"
```

| # | Parámetro | Qué es |
|---|-----------|--------|
| 1 | `--csv` | Un archivo unificado (una fila por comentario) **o varios archivos, uno por fuente**. Formatos: csv, tsv, txt, xlsx, xls, json, jsonl, parquet |
| 2 | `--columna_texto` | Columna con el texto. Con varios archivos se pueden unir varias separadas por coma; si un archivo no la tiene, se detecta sola |
| 3 | `--columna_fuente` | Columna que identifica la fuente. Con varios archivos, la fuente es el nombre de cada archivo |
| 4 | `--etiqueta_dmo` | Fuente que corresponde a la DMO (con varios archivos, el nombre del archivo de la DMO sin extensión) |
| 5 | `--idioma` | Idioma objetivo: `es`, `en`, `fr`, `pt`, `it`, `de`… Sólo se analizan los comentarios en ese idioma |
| 6 | `--titulo` | Título del reporte y nombre de la carpeta de salida |
| 7 | `--paleta` | Paleta. Aptas para daltonismo: `okabe_ito`, `viridis`, `cividis`, `plasma`, `inferno`, `magma` |

Parámetros opcionales:

| Parámetro | Por defecto | Qué hace |
|-----------|-------------|----------|
| `--excluir` | vacío | Palabras a ignorar, separadas por coma. Se usa para el nombre del destino, que aparece en casi todo y no distingue temas |
| `--umbral_topicos` | 30 | Con menos comentarios se reportan frecuencias de palabras en lugar de tópicos. Una fuente con menos comentarios no entra en el promedio de visitantes |
| `--contaminacion` | 0.03 | Proporción esperada de comentarios atípicos por fuente |
| `--umbral_polaridad` | 0 | Polaridad mínima para llamar positivo a un comentario |
| `--concepto` | «precio valor costo» | Concepto a buscar por similitud semántica (se traduce según el idioma) |
| `--k_topicos` | automático | Fija el número de tópicos (por defecto el análisis lo elige y lo imprime al terminar) |
| `--semilla` | 42 | Semilla para que todo sea reproducible |
| `--salida` | `salidas` | Carpeta de salida |

El script no supone nombres ni número de fuentes; los toma del CSV. Por ejemplo, con el CSV de ejemplo, que usa otros nombres de columnas:

```bash
python analizador.py --csv datos/ejemplo.csv --columna_texto comentario --columna_fuente plataforma \
  --etiqueta_dmo sectur --idioma es --titulo "Ejemplo" --paleta cividis
```

Con todos los parámetros (obligatorios y opcionales):

```bash
python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente \
  --etiqueta_dmo sectur --idioma es --titulo "Imagen de la Ciudad de México" --paleta cividis \
  --excluir "mexico,ciudad,cdmx,df,city" --umbral_topicos 30 --contaminacion 0.03 --umbral_polaridad 0 \
  --concepto "precio valor costo" --k_topicos 10 --semilla 42 --salida salidas
```

Con un archivo por fuente, en cualquier formato (aquí, las 4 bases originales tal como vienen):

```bash
python analizador.py --csv datos/originales/sectur.csv datos/originales/TripAdvisor.csv.gz \
  datos/originales/instaUGC.csv datos/originales/redditcdmx.csv \
  --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es \
  --titulo "Imagen de la Ciudad de México" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

Al terminar imprime cuántos temas encontró, el resumen de brechas y la comparación de la DMO con cada fuente.

Para el corpus en inglés (sobre todo Reddit):

```bash
python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente \
  --etiqueta_dmo sectur --idioma en --titulo "Imagen de la Ciudad de México" --paleta viridis \
  --excluir "mexico,city,cdmx,mexican"
```

### Salidas

En `salidas/<titulo>_<idioma>/`:

- `corpus_procesado.parquet`: una fila por comentario, con su fuente, texto original, lemas (el texto ya limpio y lematizado), si es atípico, tono, tema, cercanía con el concepto, puntaje BM25 del concepto y coordenadas del mapa.
- `resultados.json`: todos los resultados agregados. Es lo que lee el tablero.
- `reporte.html`: reporte interactivo autocontenido (funciona sin conexión).

Los archivos más pesados del repositorio van comprimidos con gzip para que GitHub los acepte por la web: `datos/cdmx_unificado.csv.gz`, `datos/originales/TripAdvisor.csv.gz` y el reporte de cada ejemplo (`salidas/*/reporte.html.gz`, que también se descarga ya descomprimido desde el tablero). El script y el tablero leen los `.gz` directamente.

## Qué hace cada paso

1. **Preprocesamiento.** Detecta el idioma de cada comentario (`langdetect`). Quita URLs, menciones, emojis, números y signos, y convierte los hashtags en palabras. Después quita las palabras vacías ISO del idioma y lematiza (`simplemma`). La etiqueta de fuente no se modifica.
2. **Atípicos.** Trabaja sobre la base unificada completa. Primero quita textos vacíos y copias exactas dentro de una misma fuente (en el CSV del caso: 13). Después convierte todos los textos en vectores en un mismo espacio (TF-IDF reducido con LSA a 100 dimensiones) y entrena **un solo Isolation Forest para toda la base** con una muestra balanceada por fuente. El corte del 3 % se aplica dentro de cada fuente: con un corte único, casi todos los atípicos serían de la fuente más grande. De los atípicos de toda la base y de cada fuente reporta unigramas, bigramas y trigramas, las palabras que los distinguen (log-odds con prior de Dirichlet) y ejemplos. Los atípicos no pasan a los pasos siguientes.
3. **Sentimiento binario.** En español usa un modelo propio: regresión logística sobre TF-IDF, entrenada con las calificaciones de TripAdvisor (`entrenar_sentimiento.py`; las métricas están en `modelos/metricas_sentimiento_es.json`). En otros idiomas usa VADER.
4. **Tópicos.** Usa NMF sobre unigramas y bigramas. Elige k entre 5 y 15 por coherencia NPMI × diversidad, medida en 3 muestras. Lo hace para el corpus común y para cada tono. Con menos de 30 comentarios (`--umbral_topicos`) recurre a frecuencias de palabras: listas con conteos y nubes de palabras por fuente y tono (`wordcloud`, sin conexión), en el reporte y en el tablero.
5. **Comparación DMO vs. visitantes.** Calcula el peso de cada tema por fuente y la diferencia DMO − visitantes con IC 95 % bootstrap. Los visitantes son el promedio de las fuentes, cada una con el mismo peso. También calcula con qué palabras aborda cada lado el tema, el parecido global (coseno de centroides LSA), la coincidencia de agenda (1 − Jensen-Shannon) y una χ² del tono. **Lo mismo se hace para la DMO frente a cada fuente por separado**, con dos capas: cuantitativa (temas con IC, tono con χ², parecido con IC, agenda) y cualitativa (palabras propias de cada lado por log-odds, palabras con que cada lado aborda cada tema y ejemplos de cada lado elegidos con **BM25**, usando las palabras del tema como consulta).
6. **Reporte.** Incluye las conclusiones para la DMO (respuesta a la pregunta del proyecto y decisiones con evidencia), las palabras clave por tema y fuente, el comentario representativo (el más cercano al centro del tema) y un resumen de brechas.
7. **Visualizaciones.** Mapa t-SNE con color y forma redundantes, por tema y por fuente, y gráficas comparativas.
8. **Concepto «precio, valor, costo».** Proyecta la consulta al espacio LSA y mide su similitud con cada comentario. Un comentario se considera ligado al concepto si supera el percentil 95. Reporta la comparación DMO vs. visitantes y los 5 comentarios más cercanos, con su fuente. Como complemento calcula **BM25** de la misma consulta: qué porcentaje de cada grupo usa literalmente esas palabras y los 5 que más las usan.

**Por qué BM25.** Okapi BM25 (Robertson y Zaragoza, 2009) es el modelo clásico de recuperación de información: puntúa un comentario por las palabras de la consulta que contiene, pesa más las palabras raras en la base (idf) y satura la repetición y el largo del texto (k1 = 1.5, b = 0.75). Se usa donde hace falta *recuperar* textos a partir de palabras: para elegir los ejemplos de cada tema en cada fuente, en el buscador del tablero y para medir la mención literal del concepto. Para *comparar significados* se sigue usando LSA, porque encuentra también los comentarios que hablan de la idea con otras palabras.

Los temas se nombran sólo con sus palabras principales: no se les asigna ninguna categoría turística.

## Estructura

```
analizador.py            script principal (CLI)
app.py                   tablero de Streamlit
entrenar_sentimiento.py  entrena el modelo de tono en español
unificar_fuentes.py      une las 4 bases originales en datos/cdmx_unificado.csv.gz
pipeline/                módulos de cada paso (analisis.py los encadena; lectura.py lee cualquier formato; bm25.py)
datos/                   cdmx_unificado.csv, ejemplo.csv y originales/ (las 4 bases tal como se entregaron)
modelos/                 modelo de tono y sus métricas
salidas/                 resultados (los lee el tablero)
validacion/              muestra para validar el tono a mano (100 comentarios por fuente)
verificar_requisitos.py  prueba cada requisito con datos nuevos (ver VERIFICACION.md)
```

Para regenerar `datos/cdmx_unificado.csv.gz` a partir de las 4 bases originales (sectur.csv, TripAdvisor.csv, instaUGC.csv y redditcdmx.csv):

```bash
python unificar_fuentes.py --dir datos/originales --salida datos/cdmx_unificado.csv.gz
```

Si `modelos/sentimiento_es.joblib` no carga porque tienes otra versión de scikit-learn, vuelve a entrenarlo:

```bash
python entrenar_sentimiento.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto \
  --columna_calificacion rating --columna_fuente fuente --fuente tripadvisor
```

## Verificación

`python verificar_requisitos.py` corre el script con datos que no ha visto (otras columnas, otras fuentes, archivos sueltos en xlsx, json, txt y tsv) y revisa cada requisito del proyecto, incluidos el tablero, BM25, la comparación con cada fuente y las conclusiones (43 comprobaciones). Los resultados y las pruebas de robustez están en `VERIFICACION.md`.
