# Imagen del destino: proyectada (DMO) vs. percibida

Compara la imagen de un destino que proyecta su organización de marketing (DMO) con la que perciben los visitantes en otras fuentes digitales (reseñas, redes sociales, foros). El caso de estudio es la Ciudad de México: **Sectur CDMX** (DMO) frente a **TripAdvisor**, **Instagram** y **Reddit**.

Responde la pregunta del proyecto: **¿la imagen que proyecta la DMO coincide con la que perciben los visitantes? ¿En qué temas hay brechas y qué debería ajustar la DMO en su comunicación?**

Proyecto final de Visualización de Datos · **Autor: [Alejandro Castillo Avalos](#autor-y-contacto)** · Ingeniería de Datos e Inteligencia Artificial, DICIS, Universidad de Guanajuato.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-tablero-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Plotly](https://img.shields.io/badge/Plotly-gr%C3%A1ficas-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/python/)
[![Sin APIs](https://img.shields.io/badge/funciona-sin_conexi%C3%B3n-2E7D32)](#verificación)
[![Contacto](https://img.shields.io/badge/Contacto-a.castilloavalos%40ugto.mx-0072B2)](mailto:a.castilloavalos@ugto.mx)

## Las dos versiones

| | **Versión de terminal** (la que se presenta) | Versión web |
|---|---|---|
| Cómo se usa | `python analizador.py` con los **7 parámetros obligatorios** | Se abre una página y se suben los archivos |
| Qué hace | Corre los 8 pasos del análisis, imprime el resumen y las conclusiones, guarda los resultados y **abre solo el tablero de Streamlit** con esos resultados | Corre los mismos 8 pasos y muestra el mismo tablero |
| Archivos | `analizador.py` → `tablero.py` | `app.py` |
| Dónde corre | En la computadora (sin conexión) | En la computadora o publicada en Streamlit Community Cloud |

Las dos usan exactamente el mismo código de análisis (`pipeline/analisis.py`) y el mismo tablero, con sus nueve pestañas. Por eso dan los mismos resultados. Todo corre sin conexión: no se usa ninguna API externa ni se envía ningún texto a otro servicio. El resultado no depende del orden en que se den los archivos, de su nombre ni del orden de sus filas.

## Contenido

1. [Cumplimiento del proyecto, punto por punto](#cumplimiento-del-proyecto-punto-por-punto)
2. [Requisitos: Python y librerías](#requisitos-python-y-librerías)
3. [Instalación paso a paso](#instalación-paso-a-paso)
4. [Versión de terminal (la que se presenta)](#versión-de-terminal-la-que-se-presenta)
5. [Archivos de prueba](#archivos-de-prueba)
6. [El tablero: las nueve pestañas](#el-tablero-las-nueve-pestañas)
7. [Versión web y publicación en Streamlit Community Cloud](#versión-web-y-publicación-en-streamlit-community-cloud)
8. [Actualizar el repositorio desde la página de GitHub](#actualizar-el-repositorio-desde-la-página-de-github)
9. [Qué hace cada paso](#qué-hace-cada-paso)
10. [Estructura del repositorio](#estructura-del-repositorio)
11. [Problemas comunes](#problemas-comunes)
12. [Verificación](#verificación)
13. [Autor y contacto](#autor-y-contacto)

## Cumplimiento del proyecto, punto por punto

| Requisito del proyecto | Cómo se cumple | Dónde |
|---|---|---|
| Script de Python ejecutable desde la línea de comandos | `python analizador.py` con los 7 parámetros obligatorios; al terminar abre el tablero | `analizador.py`, `tablero.py` |
| 1. Ruta del CSV unificado con columna de fuente | `--csv`: la base unificada, o el archivo de la DMO y el de los visitantes. Formatos: csv, tsv, txt, xlsx, xls, json, jsonl, parquet y `.gz` | `pipeline/lectura.py` |
| 2. Columna de comentarios | `--columna_texto`. Si un archivo no la tiene, se detecta sola | |
| 3. Columna de fuente | `--columna_fuente` | |
| 4. Etiqueta de la DMO | `--etiqueta_dmo`. Sus registros son la imagen proyectada; el resto, la percibida | |
| 5. Idioma objetivo | `--idioma` (`es`, `en`, `fr`, `pt`, `it`, `de`…): cambia la detección de idioma, las palabras vacías, la lematización y el modelo de tono | `pipeline/preprocesamiento.py` |
| 6. Título del reporte | `--titulo`: en el reporte, el tablero y el nombre de la carpeta de salida | |
| 7. Paleta accesible | `--paleta`: `okabe_ito`, `viridis`, `cividis`, `plasma`, `inferno`, `magma`; el tablero se abre con esa paleta | `pipeline/visualizaciones.py` |
| Procesamiento 1. Limpieza y preprocesamiento | Quita URLs, menciones, emojis, números y signos; minúsculas; tokeniza, quita palabras vacías y lematiza según el idioma. La etiqueta de fuente se conserva en cada registro | `pipeline/preprocesamiento.py` |
| 2. Atípicos y n-gramas | Isolation Forest (visto en clase). Unigramas, bigramas y trigramas de los atípicos (de toda la base y por fuente). Sólo los normales siguen | `pipeline/outliers.py` |
| 3. Sentimiento binario | Positivo/negativo. En español, regresión logística entrenada con las estrellas de TripAdvisor; en otros idiomas, VADER. Dos grupos, cada uno con su fuente | `pipeline/sentimiento.py` |
| 4. Tópicos por sentimiento | NMF para positivos y para negativos; el número de temas se elige solo. **Condición especial:** con menos de 30 comentarios (`--umbral_topicos`) se usan frecuencias de palabras y nubes de palabras | `pipeline/topicos.py`, `pipeline/nubes.py` |
| 5. Comparación DMO vs. percibida | Tópicos (DMO vs. agregado y vs. cada fuente, con brechas e intervalos), sentimiento (con χ²), similitud semántica global (**índice de alineación**, coseno LSA con intervalo) y tabla por fuente | `pipeline/comparacion.py` |
| 6. Resultados clave | Palabras clave de cada tópico positivo y negativo indicando la fuente; comentario representativo (el más cercano al centroide); resumen de brechas. Se imprimen en la terminal, van en el reporte HTML y en el tablero | `pipeline/reporte.py` |
| 7. Visualizaciones interactivas | Dispersión de comentarios (t-SNE) con **color + forma**, por tópico (positivos y negativos) y por fuente, con el comentario al pasar el cursor; gráficas que contrastan temas y tono de la DMO y de los visitantes | Tablero y reporte |
| 8. Concepto «precio, valor, costo» | Similitud semántica de cada comentario con el concepto; dispersión interactiva; comparación DMO vs. percibida (frecuencia, tono y contexto); los 5 más cercanos con su fuente; como complemento, mención literal con BM25 | `pipeline/concepto.py` |
| GitHub, `requirements.txt` y `README.md` con ejemplos con todos los parámetros | Este archivo; ver [Uso desde la terminal](#versión-de-terminal-la-que-se-presenta) | |
| CSV de ejemplo anonimizado con la columna de fuente | `datos/ejemplo.csv` (columna `plataforma`) y `datos/ejemplo_visitantes.csv` | [Archivos de prueba](#archivos-de-prueba) |
| Sin APIs externas, offline | Se comprobó corriendo con la red bloqueada | `verificar_requisitos.py` |
| Agnóstico al número y nombre de las fuentes | Se comprobó con 2 y 4 fuentes, con otros nombres de columnas y fuentes, y con un archivo por fuente | `verificar_requisitos.py` |
| Demostración en vivo con datos no vistos | Se corre con el archivo que dé el profesor: `--csv <archivo_de_la_DMO> <archivo_del_profesor>` | [Comandos](#comandos-listos-para-copiar) |

Además, el tablero responde la pregunta del proyecto en su primera pestaña («Conclusiones»): una respuesta corta, indicadores y decisiones para la DMO con su evidencia.

## Requisitos: Python y librerías

### Python

- **Versión recomendada: Python 3.13.** Con ella se desarrolló y probó todo, y es la que usa el tablero publicado en Streamlit Community Cloud.
- **Versión mínima: Python 3.11.** La exige scikit-learn 1.9, la versión con que se entrenó el modelo de tono (`modelos/sentimiento_es.joblib`). Con Python 3.10 o anterior la instalación falla.
- Se descarga de https://www.python.org/downloads/.

### Computadora

- Windows 10/11, macOS o Linux.
- Unos **700 MB de disco** para el entorno con las librerías y unos 20 MB para el proyecto.
- **4 GB de RAM o más.** El análisis completo de las 4 bases (28 mil textos) usa alrededor de 750 MB de memoria y tarda unos 3 minutos. Con archivos chicos tarda segundos.
- Internet sólo para instalar las librerías. Después todo funciona sin conexión.

### Librerías

Se instalan todas con `pip install -r requirements.txt`. Ninguna se descarga aparte: los diccionarios de palabras vacías, el lematizador y el diccionario de VADER vienen dentro de sus paquetes.

| Librería | Versión probada | Mínima | Para qué se usa |
|---|---|---|---|
| `pandas` | 3.0.5 y 3.1.1 | 2.1 | Tablas de comentarios; leer CSV, TSV, TXT, JSON, Excel y Parquet |
| `numpy` | 2.5.3 | 1.26 | Cálculo numérico |
| `scipy` | 1.18.1 | 1.11 | Prueba χ² del tono y distancia de Jensen-Shannon |
| `scikit-learn` | 1.9.1 | **1.9 y menor que 1.10** | TF-IDF, LSA, NMF (temas), Isolation Forest (atípicos), regresión logística (tono) y t-SNE (mapa) |
| `joblib` | 1.6.0 | 1.3 | Guardar y cargar el modelo de tono |
| `pyarrow` | 26.0.1 | 14.0 | Leer y escribir archivos Parquet |
| `matplotlib` | 3.11.2 | 3.8 | Escalas de color y nubes de palabras |
| `plotly` | 7.1.0 | 5.20 | Gráficas interactivas del tablero y del reporte |
| `streamlit` | 1.67.0 | 1.50 | El tablero |
| `langdetect` | 1.0.9 | 1.0.9 | Detectar el idioma de cada comentario |
| `stopwordsiso` | 0.7.1 | 0.6.1 | Palabras vacías («de», «la», «que») de muchos idiomas |
| `simplemma` | 2.0.0 | 1.0 | Lematizar («tacos» → «taco», «cuesta» → «costar») |
| `emoji` | 2.16.0 | 2.8 | Quitar emojis |
| `vaderSentiment` | 3.3.2 | 3.3.2 | Tono en inglés |
| `wordcloud` | 1.9.6 | 1.9.3 | Nubes de palabras |
| `openpyxl` | 3.1.5 | 3.1 | Leer archivos `.xlsx` |
| `xlrd` | 2.0.2 | 2.0 | Leer archivos `.xls` |

Sólo `scikit-learn` está fijado a una versión: el modelo de tono se guardó con la 1.9 y otra versión puede no cargarlo (ver [Problemas comunes](#problemas-comunes)). Las demás aceptan versiones más nuevas.

## Instalación paso a paso

### 1. Instala Python

- **Windows:** descarga el instalador de Python 3.13 de https://www.python.org/downloads/. En la primera pantalla del instalador **marca «Add python.exe to PATH»** y después «Install Now».
- **macOS:** descarga el instalador de Python 3.13 (macOS 64-bit universal2) de la misma página y ábrelo. Al terminar, abre la carpeta *Aplicaciones › Python 3.13* y haz doble clic en «Install Certificates.command».
- **Linux:** usa el gestor de paquetes de tu distribución, por ejemplo `sudo apt install python3.13 python3.13-venv`.

Comprueba la versión en una terminal (en Windows, «Símbolo del sistema» o «PowerShell»; en macOS, «Terminal»):

```bash
python --version        # Windows
python3 --version       # macOS y Linux
```

Debe decir `Python 3.11` o superior. Si en Windows dice que no se reconoce el comando, ve a [Problemas comunes](#problemas-comunes).

### 2. Descarga el proyecto

El repositorio es privado, así que primero el dueño tiene que invitarte: en GitHub, *Settings › Collaborators › Add people*, con tu usuario o correo. Acepta la invitación que te llega por correo. Después hay dos formas de descargarlo:

- **Sin instalar nada más:** en la página del repositorio, botón verde **«Code» › «Download ZIP»**. Descomprime el ZIP y entra a la carpeta `imagen-destino-dmo-main`.
- **Con git:**

  ```bash
  git clone https://github.com/Castillo322/imagen-destino-dmo.git
  cd imagen-destino-dmo
  ```

  Como el repositorio es privado, git pide iniciar sesión. Como contraseña se usa un *token* de GitHub (*Settings › Developer settings › Personal access tokens*), no la contraseña de la cuenta. También se puede clonar con GitHub Desktop.

### 3. Crea un entorno virtual

Un entorno virtual guarda las librerías del proyecto aparte de las del sistema. Abre la terminal **dentro de la carpeta del proyecto** (la que tiene `analizador.py`) y ejecuta:

**Windows (PowerShell o Símbolo del sistema):**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS y Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Al activarlo, la línea de la terminal empieza con `(.venv)`. Cada vez que abras una terminal nueva para usar el proyecto, entra a la carpeta y vuelve a activarlo con la segunda línea.

### 4. Instala las librerías

Con el entorno activado:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tarda unos minutos la primera vez. Para comprobar que quedó bien:

```bash
python -c "import sklearn, streamlit, pandas; print('scikit-learn', sklearn.__version__, '· streamlit', streamlit.__version__, '· pandas', pandas.__version__)"
```

Debe mostrar `scikit-learn 1.9.x`.

### 5. Prueba rápida

```bash
python analizador.py --csv datos/ejemplo.csv --columna_texto comentario --columna_fuente plataforma \
  --etiqueta_dmo sectur --idioma es --titulo "Prueba" --paleta viridis
```

En unos segundos imprime el avance, el resumen y las conclusiones, y abre el tablero en el navegador. Para cerrarlo, presiona `Ctrl+C` en la terminal.

## Versión de terminal (la que se presenta)

### Los 7 parámetros obligatorios

| # | Parámetro | Qué es | Ejemplo |
|---|-----------|--------|---------|
| 1 | `--csv` | La **base unificada** (un archivo con la columna de texto y la de fuente) **o el archivo de la DMO y el de los visitantes**. Formatos: csv, tsv, txt, xlsx, xls, json, jsonl, parquet (también `.gz`) | `datos/cdmx_unificado.csv.gz` |
| 2 | `--columna_texto` | Columna con los comentarios. Si un archivo no la tiene, se detecta sola | `texto` |
| 3 | `--columna_fuente` | Columna que identifica la fuente. En un archivo sin esa columna, la fuente es el nombre del archivo | `fuente` |
| 4 | `--etiqueta_dmo` | Valor de la fuente que corresponde a la DMO (con su propio archivo, el nombre del archivo sin extensión) | `sectur` |
| 5 | `--idioma` | Idioma objetivo. Sólo se analizan los comentarios en ese idioma | `es` |
| 6 | `--titulo` | Título del reporte y del tablero; también nombra la carpeta de salida | `"Imagen de la CDMX"` |
| 7 | `--paleta` | Paleta de colores. Aptas para daltonismo: `okabe_ito`, `viridis`, `cividis`, `plasma`, `inferno`, `magma` | `okabe_ito` |

Ejemplo con los 7 parámetros (en macOS y Linux; en Windows, ver la nota de abajo):

```bash
python analizador.py \
  --csv datos/cdmx_unificado.csv.gz \
  --columna_texto texto \
  --columna_fuente fuente \
  --etiqueta_dmo sectur \
  --idioma es \
  --titulo "Imagen de la Ciudad de México" \
  --paleta okabe_ito
```

**En Windows**, escribe el comando en una sola línea (sin `\`) o cambia `\` por `^` en el Símbolo del sistema o por `` ` `` en PowerShell. Las rutas pueden ir con `/` o con `\`.

### Qué pasa al correrlo

1. Dice qué archivos leyó y qué fuentes va a comparar, por ejemplo: `Fuentes a comparar: tripadvisor (22,128), reddit (5,450), sectur [DMO] (487), instagram (424)`.
2. Muestra el avance de cada paso con el tiempo transcurrido.
3. Guarda los resultados en `salidas/<titulo>_<idioma>/`: `reporte.html`, `resultados.json` y `corpus_procesado.parquet`.
4. Imprime cuántos temas encontró, el resumen de brechas, la comparación de la DMO con cada fuente y las conclusiones para la DMO (respuesta a la pregunta del proyecto y decisiones).
5. **Abre el tablero de Streamlit** (`tablero.py`) en el navegador, en http://localhost:8501, con los resultados de esa corrida y la paleta elegida. Si el puerto está ocupado usa el siguiente (8502…). Si el navegador no se abre solo, copia la dirección que aparece en la terminal.
6. El tablero sigue abierto mientras la terminal esté abierta. Para cerrarlo, presiona `Ctrl+C` en la terminal.

### Dar los datos: un archivo o dos

**Un archivo: la base unificada.** Tiene una fila por comentario, una columna de texto y una columna de fuente. Los registros cuya fuente es `--etiqueta_dmo` son la imagen proyectada; el resto, la percibida. Así viene `datos/cdmx_unificado.csv.gz` (columnas `texto` y `fuente`, con `sectur`, `tripadvisor`, `instagram` y `reddit`).

**Dos archivos: el de la DMO y el de los visitantes.** Se ponen uno tras otro en `--csv`. El archivo de los visitantes puede ser la base unificada, una sola plataforma (TripAdvisor, Instagram o Reddit) o el archivo que proponga el profesor. También se aceptan más de dos archivos. Así se reparten las fuentes:

- **Si un archivo trae la columna de fuente** (como la base unificada), cada fila conserva su etiqueta.
- **Si no la trae**, todo el archivo es una sola fuente con el nombre del archivo. Se reconocen las fuentes del caso: `sectur.csv` → `sectur`, `TripAdvisor.csv.gz` → `tripadvisor`, `instaUGC.csv` → `instagram`, `redditcdmx.csv` → `reddit`. Cualquier otro archivo usa su nombre: `google_reviews.xlsx` → `google_reviews`.
- **La DMO no se duplica:** si la DMO viene en su propio archivo y otro archivo también la trae (como la base unificada, que ya incluye a Sectur), se usa la del archivo propio y la otra se omite. La terminal lo avisa.
- **Columna de texto:** si un archivo no tiene la columna de `--columna_texto`, se detecta sola. Por ejemplo, `instaUGC.csv` la tiene en `description`, y en `redditcdmx.csv` se unen `title` y `text`. Si una celda trae varios comentarios juntos separados por « - », como las respuestas de un hilo de Reddit, se separan en comentarios individuales.

### Comandos listos para copiar

Desde la carpeta del proyecto, con el entorno virtual activado. Cada comando usa un título distinto, así que cada corrida queda en su propia carpeta de `salidas/`. Con Sectur conviene `--excluir "mexico,ciudad,cdmx,df,city"`: el nombre del destino aparece en todo y no distingue temas.

**Sectur frente a la base unificada (las 3 fuentes de visitantes):**

```bash
python analizador.py --csv datos/originales/sectur.csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Sectur vs visitantes" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

**Sectur frente a TripAdvisor:**

```bash
python analizador.py --csv datos/originales/sectur.csv datos/originales/TripAdvisor.csv.gz --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Sectur vs TripAdvisor" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

**Sectur frente a Instagram:**

```bash
python analizador.py --csv datos/originales/sectur.csv datos/originales/instaUGC.csv --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Sectur vs Instagram" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

**Sectur frente a Reddit** (en español quedan pocos comentarios porque casi todo Reddit está en inglés; el segundo comando analiza el inglés):

```bash
python analizador.py --csv datos/originales/sectur.csv datos/originales/redditcdmx.csv --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Sectur vs Reddit" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
python analizador.py --csv datos/originales/sectur.csv datos/originales/redditcdmx.csv --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma en --titulo "Sectur vs Reddit" --paleta okabe_ito --excluir "mexico,city,cdmx,mexican"
```

**Sólo la base unificada (un archivo, como dice el proyecto):**

```bash
python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Imagen de la Ciudad de México" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

**Sectur frente al archivo del profesor.** Copia el archivo a la carpeta `datos/` y cambia `ARCHIVO_DEL_PROFESOR.csv` por su nombre:

```bash
python analizador.py --csv datos/originales/sectur.csv datos/ARCHIVO_DEL_PROFESOR.csv --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Sectur vs archivo del profesor" --paleta okabe_ito --excluir "mexico,ciudad,cdmx,df,city"
```

- Si el archivo del profesor **ya trae su propia DMO y una columna de fuente**, es una base unificada: pásalo solo, con sus nombres de columnas y su etiqueta de DMO, por ejemplo: `--csv datos/ARCHIVO.csv --columna_texto comentario --columna_fuente plataforma --etiqueta_dmo dmo`.
- Si una columna no existe, la terminal dice cuáles hay. Corrige el nombre y vuelve a correr.
- Si los comentarios están en otro idioma, cambia `--idioma` (por ejemplo, `en`).

### Parámetros opcionales

| Parámetro | Por defecto | Qué hace |
|-----------|-------------|----------|
| `--excluir` | vacío | Palabras a ignorar, separadas por coma. Se usa para el nombre del destino, que aparece en casi todo y no distingue temas |
| `--sin_tablero` | — | Sólo genera los archivos; no abre el tablero |
| `--puerto` | 8501 | Puerto del tablero; si está ocupado se usa el siguiente |
| `--umbral_topicos` | 30 | Con menos comentarios se reportan frecuencias de palabras en lugar de tópicos. Una fuente con menos comentarios no entra en el promedio de visitantes |
| `--contaminacion` | 0.03 | Proporción de comentarios atípicos que se separa en cada fuente |
| `--umbral_polaridad` | 0 | Polaridad mínima para llamar positivo a un comentario |
| `--concepto` | «precio valor costo» | Concepto a buscar por similitud semántica (se traduce según el idioma) |
| `--k_topicos` | automático | Fija el número de tópicos (por defecto el análisis lo elige y lo imprime al terminar) |
| `--semilla` | 42 | Semilla para que todo sea reproducible |
| `--salida` | `salidas` | Carpeta de salida |

Con todos los parámetros (obligatorios y opcionales):

```bash
python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente \
  --etiqueta_dmo sectur --idioma es --titulo "Imagen de la Ciudad de México" --paleta cividis \
  --excluir "mexico,ciudad,cdmx,df,city" --umbral_topicos 30 --contaminacion 0.03 --umbral_polaridad 0 \
  --concepto "precio valor costo" --k_topicos 10 --semilla 42 --salida salidas --puerto 8501
```

`python analizador.py --help` muestra todos los parámetros.

### Volver a abrir el tablero sin repetir el análisis

```bash
streamlit run tablero.py -- --resultados salidas/sectur_vs_tripadvisor_es --paleta okabe_ito
```

Sin `--resultados` abre la corrida más reciente de `salidas/`.

### Salidas

En `salidas/<titulo>_<idioma>/`:

- `corpus_procesado.parquet`: una fila por comentario. Para cada uno guarda:
  - su fuente y su texto original;
  - los lemas (el texto ya limpio y lematizado);
  - si es atípico, su tono y su tema;
  - su cercanía con el concepto y su puntaje BM25 del concepto;
  - sus coordenadas en el mapa.
- `resultados.json`: todos los resultados agregados, incluidas las conclusiones. Es lo que lee el tablero.
- `reporte.html`: reporte interactivo autocontenido (funciona sin conexión). En el repositorio, el de los ejemplos va comprimido (`reporte.html.gz`); desde el tablero se descarga ya descomprimido.

## Archivos de prueba

Dos archivos anonimizados para probar el script en segundos. Las menciones a cuentas aparecen como `@usuario`, y se quitaron teléfonos, correos y enlaces:

- **`datos/ejemplo.csv`**: el formato de entrada que pide el proyecto, una base unificada. Trae 360 comentarios: 120 de la DMO (Sectur), 120 de TripAdvisor y 120 de Instagram. Usa a propósito otros nombres de columnas: el texto está en `comentario` y la fuente en `plataforma`, con los valores `sectur`, `tripadvisor` e `instagram`.

  ```
  plataforma,comentario
  sectur,dishes local flavor seafood city without eat good seafood ceviche tostadas …
  instagram,"Feria Oaxaqueña en CDMX 😱 Puedes encontrar deliciosa comida de Oaxaca …"
  tripadvisor,hermoso gastar monton aqui bonito interesante historia antecedentes diseno general merece parada
  ```

  ```bash
  python analizador.py --csv datos/ejemplo.csv --columna_texto comentario --columna_fuente plataforma --etiqueta_dmo sectur --idioma es --titulo "Prueba" --paleta viridis
  ```

- **`datos/ejemplo_visitantes.csv`**: un archivo de visitantes de una sola plataforma, sin columna de fuente. Es como el que podría dar el profesor: 300 reseñas con columnas `comentario`, `calificacion` y `fecha`. Se compara con Sectur:

  ```bash
  python analizador.py --csv datos/originales/sectur.csv datos/ejemplo_visitantes.csv --columna_texto texto --columna_fuente fuente --etiqueta_dmo sectur --idioma es --titulo "Prueba con dos archivos" --paleta cividis --excluir "mexico,ciudad,cdmx,df,city"
  ```

  Como no tiene la columna `texto`, la terminal avisa que usa `comentario`. Como tiene pocas reseñas negativas, los negativos se analizan con frecuencias de palabras en lugar de tópicos: es la condición especial del paso 4.

Los datos completos del caso están en `datos/originales/` (las 4 bases tal como se entregaron) y en `datos/cdmx_unificado.csv.gz` (las 4 unidas).

## El tablero: las nueve pestañas

Es el mismo en la versión de terminal (`tablero.py`) y en la web (`app.py`). La paleta se cambia en la barra lateral; en la versión de terminal empieza con la que se pidió en `--paleta`. Cada fuente conserva siempre el mismo color y la misma forma; la DMO es siempre el cuadrado. El reporte HTML se descarga desde la barra lateral.

- **Conclusiones**: responde la pregunta del proyecto con una respuesta corta, indicadores y **decisiones para la DMO** ordenadas por prioridad, cada una con su evidencia. Los tipos de decisión son: replantear, incorporar, atender, informar, ajustar enfoque o tono, canal, vigilar y mantener. Se generan solas, con las mismas reglas, para cualquier conjunto de archivos (`pipeline/conclusiones.py`). Los umbrales se muestran en la pestaña.
- **Resumen**: muestra:
  - comentarios por fuente;
  - tono, parecido del contenido y coincidencia de agenda;
  - el **número de temas encontrados** y cómo se eligió;
  - los hallazgos principales.
- **Proyectado vs. percibido**: cada tema en la DMO frente al promedio de visitantes, con su diferencia e intervalo.
- **DMO vs. cada fuente**: la DMO frente a cada fuente por separado.
  - Cuantitativo: peso de cada tema y diferencia con IC 95 %, tono con χ², parecido y coincidencia de agenda.
  - Cualitativo: frases de resumen y palabras propias de cada lado. Tema por tema, con qué palabras lo dice cada uno, con ejemplos de cada lado elegidos con BM25.
- **Lo que gusta y lo que no**: tono por fuente, temas de cada tono y nubes de palabras por fuente y tono.
- **Por fuente**: temas principales y tono de cada fuente, y mapa de calor fuente × tema.
- **Explorar y buscar**: mapa de comentarios con color y forma, *hover* y selección con lazo. Incluye la **búsqueda BM25**: qué porcentaje de cada fuente usa las palabras buscadas y los comentarios más relevantes.
- **Precio, valor y costo**: dispersión de todos los comentarios según su cercanía con la idea, comparación DMO vs. visitantes, los 5 más cercanos y, como complemento, la mención literal con BM25.
- **Comentarios atípicos**: unigramas, bigramas y trigramas de toda la base y de cada fuente.

Paletas aptas para daltonismo:
- **Okabe-Ito**: colores muy distintos entre sí. Se amplía con la paleta «muted» de Paul Tol cuando hay más de 8 categorías.
- viridis, cividis, plasma, inferno y magma.

## Versión web y publicación en Streamlit Community Cloud

### Usarla en la computadora

```bash
streamlit run app.py
```

En **«Subir mis archivos»** la casilla «Comparar contra Sectur CDMX (ya cargada)» está activada:

1. Arrastra el archivo de los visitantes.
2. Revisa la línea que resume qué se va a comparar.
3. Presiona **«Analizar»**.

Columnas, idioma y parámetros se detectan solos y se pueden cambiar en **«Ajustes (opcional)»**. Para usar otra DMO, quita la casilla y sube dos o más archivos. En **«Ejemplo: Ciudad de México»** se ven al instante los resultados guardados en `salidas/`. Se aceptan archivos de hasta 200 MB.

### Publicarla en internet

Así se publicó https://imagen-destino-cdmx.streamlit.app. Es gratis y no necesita servidor propio: Streamlit lee el repositorio de GitHub y corre `app.py`.

1. Entra a https://share.streamlit.io e inicia sesión **con la cuenta de GitHub dueña del repositorio**. La primera vez, autoriza a Streamlit a ver tus repositorios, incluidos los privados.
2. Presiona **«Create app»** y elige desplegar una app que ya está en GitHub.
3. Llena el formulario:
   - **Repository:** `Castillo322/imagen-destino-dmo`
   - **Branch:** `main`
   - **Main file path:** `app.py`. Escríbelo completo; el autocompletado puede proponer otro archivo.
   - **App URL:** el nombre de la dirección, por ejemplo `imagen-destino-cdmx`.
4. Abre **«Advanced settings»** y en **Python version** elige **3.13**. No hace falta agregar *secrets*: el proyecto no usa contraseñas ni APIs.
5. Presiona **«Deploy»**. La primera vez instala las librerías de `requirements.txt` y tarda unos minutos.

**Quién puede entrar.** Como el repositorio es privado, la app también lo es: sólo la ven las cuentas invitadas. Para invitar a alguien, abre la app, presiona **«Share»** (arriba a la derecha) y escribe su correo. Esa persona recibe un correo y entra con la cuenta de ese correo. En el mismo menú está la opción para hacerla pública. El repositorio es privado porque `datos/` y `salidas/` contienen publicaciones reales.

**Actualizaciones.** Cada vez que se sube un cambio a la rama `main` de GitHub, la app se actualiza sola en uno o dos minutos. Si no se actualiza, en la app abre **«Manage app»** (abajo a la derecha) y usa **«Reboot app»**. Si la app pasa un tiempo sin visitas, se «duerme»: al abrirla aparece un botón para despertarla y tarda un poco en volver.

## Actualizar el repositorio desde la página de GitHub

No hace falta saber git: todo se puede hacer desde la página del repositorio.

- **Subir o reemplazar archivos:** **«Add file» › «Upload files»**. Arrastra los archivos o carpetas; un archivo con el mismo nombre y ubicación se reemplaza. Para una subcarpeta, arrastra la carpeta completa o entra primero a esa carpeta en GitHub. Escribe una descripción y presiona **«Commit changes»**.
- **Borrar un archivo:** ábrelo, presiona **«…»** (arriba a la derecha) › **«Delete file»** › **«Commit changes»**. Queda en el historial, así que se puede recuperar.
- **Límite de la página:** 25 MB por archivo. Por eso los archivos más pesados van comprimidos con gzip:
  - `datos/cdmx_unificado.csv.gz`
  - `datos/originales/TripAdvisor.csv.gz`
  - `salidas/*/reporte.html.gz`

  El script y los tableros los leen así, sin descomprimirlos.
- **No subas** la carpeta `.venv/`, carpetas `__pycache__/`, archivos `.DS_Store` de macOS, ZIP del proyecto ni las carpetas nuevas de `salidas/` que se crean al probar.

## Qué hace cada paso

1. **Preprocesamiento.**
   - Detecta el idioma de cada comentario (`langdetect`).
   - Quita URLs, menciones, emojis, números y signos, y convierte los hashtags en palabras.
   - Quita las palabras vacías ISO del idioma y lematiza (`simplemma`).
   - La etiqueta de fuente no se modifica.
2. **Atípicos.** Trabaja sobre la base unificada completa.
   - Primero quita textos vacíos y copias exactas dentro de una misma fuente (en el caso CDMX, 13).
   - Convierte todos los textos en vectores en un mismo espacio (TF-IDF reducido con LSA a 100 dimensiones).
   - Entrena **un solo Isolation Forest para toda la base**, con una muestra balanceada por fuente.
   - El corte del 3 % se aplica dentro de cada fuente, para que todas pierdan la misma proporción. Con un corte único, cada fuente perdería una proporción distinta según cuánto se parece a TripAdvisor, que domina la base.
   - De los atípicos de toda la base y de cada fuente reporta unigramas, bigramas y trigramas, las palabras que los distinguen (log-odds con prior de Dirichlet) y ejemplos.
   - Los atípicos no pasan a los pasos siguientes.
3. **Sentimiento binario.**
   - En español usa un modelo propio: regresión logística sobre TF-IDF, entrenada con las calificaciones de TripAdvisor (`entrenar_sentimiento.py`). Las métricas están en `modelos/metricas_sentimiento_es.json`: F1 macro 0.82, AUC 0.95.
   - En otros idiomas usa VADER.
4. **Tópicos.**
   - Usa NMF sobre unigramas y bigramas.
   - Elige k entre 5 y 15 por coherencia NPMI × diversidad, medida en 3 muestras.
   - Lo hace para el corpus común y para cada tono.
   - Con menos de 30 comentarios (`--umbral_topicos`) recurre a frecuencias de palabras: listas con conteos y nubes de palabras por fuente y tono (`wordcloud`, sin conexión), en el reporte y en el tablero.
5. **Comparación DMO vs. visitantes.**
   - Calcula el peso de cada tema por fuente y la diferencia DMO − visitantes con IC 95 % bootstrap. Los visitantes son el promedio de las fuentes, cada una con el mismo peso.
   - También calcula:
     - con qué palabras aborda cada lado el tema;
     - el parecido global o índice de alineación (coseno de centroides LSA);
     - la coincidencia de agenda (1 − Jensen-Shannon);
     - una χ² del tono.
   - **Lo mismo se hace para la DMO frente a cada fuente por separado**, con dos capas:
     - Cuantitativa: temas con IC, tono con χ², parecido con IC y agenda.
     - Cualitativa: palabras propias de cada lado por log-odds, palabras con que cada lado aborda cada tema y ejemplos de cada lado elegidos con **BM25**, usando las palabras del tema como consulta.
6. **Reporte.** Incluye:
   - las conclusiones para la DMO (respuesta a la pregunta del proyecto y decisiones con evidencia);
   - las palabras clave por tema y fuente;
   - el comentario representativo (el más cercano al centro del tema);
   - un resumen de brechas.
7. **Visualizaciones.** Mapa t-SNE con color y forma redundantes, por tema y por fuente, y gráficas comparativas.
8. **Concepto «precio, valor, costo».**
   - Proyecta la consulta al espacio LSA y mide su similitud con cada comentario. Un comentario se considera ligado al concepto si supera el percentil 95.
   - Reporta la comparación DMO vs. visitantes y los 5 comentarios más cercanos, con su fuente.
   - Como complemento calcula **BM25** de la misma consulta: qué porcentaje de cada grupo usa literalmente esas palabras y los 5 que más las usan.

**Cómo salen las decisiones para la DMO** (`pipeline/conclusiones.py`). Primero cada tema se ubica según cuánto lo comunica la DMO y cuánto lo comentan los visitantes. Es la lógica del análisis de importancia-desempeño de Martilla y James (1977). Después se aplica este árbol:

- La DMO lo destaca 5 pp o más que los visitantes, con IC 95 % que no cruza el 0 → **Replantear**.
- Los visitantes lo mencionan 5 pp o más que la DMO:
  - si una sola fuente aporta el 85 % o más del tema → **Vigilar** (suele ser noticia o contenido ajeno);
  - si no, y sus quejas son el doble del % negativo general o más → **Atender**;
  - si no → **Incorporar**.
- Sin brecha firme, si ambos lo tratan: comparten dos o más palabras principales → **Mantener**; si no → **Ajustar enfoque**.

Además hay reglas que no dependen de un tema:
- las quejas más frecuentes → **Atender**;
- la idea rastreada mencionada 1.5 veces más por los visitantes → **Informar**;
- la DMO 3 puntos o más positiva, con χ² significativa → **Ajustar tono**;
- la fuente con menor parecido → **Canal**.

**Por qué BM25.** Okapi BM25 (Robertson y Zaragoza, 2009) es el modelo clásico de recuperación de información. Puntúa un comentario por las palabras de la consulta que contiene, pesa más las palabras raras en la base (idf) y satura la repetición y el largo del texto (k1 = 1.5, b = 0.75). Se usa donde hace falta *recuperar* textos a partir de palabras:
- para elegir los ejemplos de cada tema en cada fuente;
- en el buscador del tablero;
- para medir la mención literal del concepto.

Para *comparar significados* se sigue usando LSA, porque encuentra también los comentarios que hablan de la idea con otras palabras.

Los temas se nombran sólo con sus palabras principales: no se les asigna ninguna categoría turística.

## Estructura del repositorio

```
analizador.py              EL SCRIPT: los 7 parámetros, los 8 pasos y abre el tablero (versión de terminal)
tablero.py                 tablero de la versión de terminal (lo abre analizador.py)
app.py                     tablero completo; versión web (subir archivos) y base de tablero.py
requirements.txt           librerías que se instalan con pip
README.md                  este archivo
VERIFICACION.md            qué se comprobó y cómo (requisitos y robustez)
verificar_requisitos.py    prueba cada requisito con datos nuevos
entrenar_sentimiento.py    entrena el modelo de tono en español
unificar_fuentes.py        une las 4 bases originales en datos/cdmx_unificado.csv.gz
.gitignore                 archivos que git no debe subir
.streamlit/config.toml     colores y ajustes del tablero
pipeline/                  el análisis, un módulo por paso:
  analisis.py                encadena los 8 pasos (lo usan las dos versiones)
  lectura.py                 lee cualquier formato, propone columnas y nombra las fuentes
  preprocesamiento.py        idioma, limpieza, palabras vacías y lemas
  representacion.py          TF-IDF y LSA
  outliers.py                atípicos (Isolation Forest) y sus n-gramas
  sentimiento.py             tono (regresión logística o VADER)
  topicos.py                 temas (NMF con k automático)
  comparacion.py             DMO vs. visitantes y vs. cada fuente
  bm25.py                    Okapi BM25
  concepto.py                rastreo del concepto «precio, valor, costo»
  conclusiones.py            respuesta a la pregunta y decisiones para la DMO
  reporte.py                 reporte HTML
  visualizaciones.py         paletas, formas y gráficas
  nubes.py                   nubes de palabras
  config.py                  parámetros por defecto
datos/
  ejemplo.csv                ARCHIVO DE PRUEBA: base unificada chica y anonimizada (columna de fuente «plataforma»)
  ejemplo_visitantes.csv     ARCHIVO DE PRUEBA: archivo de visitantes de una sola plataforma, sin columna de fuente
  originales/                las 4 bases tal como se entregaron (sectur.csv es la DMO)
  cdmx_unificado.csv.gz      las 4 bases unidas en un archivo
modelos/                     modelo de tono en español y sus métricas
salidas/                     resultados del ejemplo CDMX (español e inglés); aquí se guardan también las corridas nuevas
validacion/                  muestra para validar el tono a mano (100 comentarios por fuente)
```

Para regenerar `datos/cdmx_unificado.csv.gz` a partir de las 4 bases originales:

```bash
python unificar_fuentes.py --dir datos/originales --salida datos/cdmx_unificado.csv.gz
```

Para volver a entrenar el modelo de tono:

```bash
python entrenar_sentimiento.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto \
  --columna_calificacion rating --columna_fuente fuente --fuente tripadvisor
```

## Problemas comunes

| Qué pasa | Qué hacer |
|---|---|
| Windows: «python no se reconoce como un comando» | Python no quedó en el PATH. Reinstálalo marcando «Add python.exe to PATH», o usa `py` en lugar de `python` (`py -m venv .venv`). |
| PowerShell no deja activar el entorno («la ejecución de scripts está deshabilitada») | Ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y confirma, o usa el Símbolo del sistema (`.venv\Scripts\activate.bat`). |
| `pip install` dice que no encuentra `scikit-learn>=1.9` | Tu Python es 3.10 o anterior. Instala Python 3.13 y vuelve a crear el entorno. |
| macOS: error de certificados (SSL) al instalar | Ejecuta «Install Certificates.command» en *Aplicaciones › Python 3.13*. |
| Aviso `InconsistentVersionWarning` o error al cargar `sentimiento_es.joblib` | Hay otra versión de scikit-learn. Instala la correcta (`pip install "scikit-learn>=1.9,<1.10"`) o vuelve a entrenar el modelo con `entrenar_sentimiento.py`. |
| `ModuleNotFoundError` (por ejemplo, `No module named 'streamlit'`) | El entorno virtual no está activado. Actívalo (paso 3) y, si hace falta, repite `pip install -r requirements.txt`. |
| «No existe el archivo …» | La ruta está mal o la terminal no está en la carpeta del proyecto. Entra con `cd` a la carpeta que tiene `analizador.py`. |
| «La columna «texto» no existe…» | Con un solo archivo, usa los nombres de columnas que muestra el mensaje. Si ese archivo es de una sola fuente, pásalo junto con el de la DMO. |
| «Ninguna fuente se llama «sectur»» | Revisa `--etiqueta_dmo`: con un archivo propio, es el nombre del archivo sin extensión. La terminal muestra las fuentes que encontró. |
| El tablero no se abre solo en el navegador | Copia la dirección que imprime la terminal (http://localhost:8501) en el navegador. |
| «Port 8501 is already in use» o el tablero abre otra corrida | Ya hay un tablero abierto en otra terminal. Ciérralo con `Ctrl+C`, o usa `--puerto 8502`. |
| Faltan muchos comentarios en los conteos | Se analizan sólo los del idioma elegido. Revisa `--idioma`. |
| La app en línea muestra un error o no se actualiza | En la app, «Manage app» › «Reboot app». Los registros de instalación están en ese mismo panel. |
| La app en línea pide iniciar sesión o dice que no tienes acceso | Es privada: el dueño tiene que invitar tu correo con «Share». |

## Verificación

`python verificar_requisitos.py` corre el script con datos que no ha visto: otras columnas, otras fuentes y archivos sueltos en xlsx, json, txt y tsv. Revisa:
- cada requisito del proyecto;
- la entrada con dos archivos, incluida la DMO más la base unificada sin duplicarla;
- que la terminal abra el tablero con los resultados;
- los dos tableros, BM25, la comparación con cada fuente y las conclusiones.

Los resultados y las pruebas de robustez están en `VERIFICACION.md`.

## Autor y contacto

**Alejandro Castillo Avalos**<br>
Estudiante de Ingeniería de Datos e Inteligencia Artificial · DICIS, Universidad de Guanajuato · Salamanca, Guanajuato, México

[![Correo](https://img.shields.io/badge/Correo-a.castilloavalos%40ugto.mx-0072B2)](mailto:a.castilloavalos@ugto.mx)
[![GitHub](https://img.shields.io/badge/GitHub-Castillo322-181717?logo=github&logoColor=white)](https://github.com/Castillo322)

Uno la ciencia de datos con la gestión de empresas: convierto datos de operación, ventas y opiniones de clientes en indicadores, tableros y automatizaciones que ayudan a decidir.

**Lo que hago**
- **Análisis de datos y aprendizaje automático** en Python: pandas, scikit-learn, procesamiento de lenguaje natural, redes neuronales y visión por computadora; Apache Spark para grandes volúmenes.
- **Visualización y tableros**: Streamlit, Plotly y Power BI, con paletas accesibles.
- **Automatización e integraciones**: n8n, Odoo, Mercado Libre y extracción de datos de documentos con IA.
- **Mejora continua**: KPIs, DMAIC, medición de tiempos y diseño de puestos.

**Experiencia**
- **Prácticas profesionales en IPower Electronics** (Salamanca, Gto., 2026): sistematización de procesos con DMAIC, KPIs y perfiles de puesto por área, y automatización del registro de solicitudes de cotización (correo → Odoo con IA).
- **Integración de inventario Mercado Libre → Odoo 18** con n8n: control de duplicados, OAuth2, actualización de existencias y alertas de error.
- **Docente de Inteligencia Artificial** en bachillerato (Modelo Dual).
- **Instructor de cursos** de medición de tiempos y DMAIC.

**Formación y certificaciones**
- Ingeniería de Datos e Inteligencia Artificial, DICIS, Universidad de Guanajuato.
- Licenciatura en Gestión Empresarial, Universidad de Guanajuato.
- Lean Six Sigma Yellow Belt, Lean Six Sigma Institute (LSSI).

**Abierto a oportunidades** en ciencia de datos, analítica de negocio, automatización de procesos e IA aplicada. Para proyectos, prácticas o empleo, escríbeme a [a.castilloavalos@ugto.mx](mailto:a.castilloavalos@ugto.mx).
