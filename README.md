# Imagen del destino: proyectada (DMO) vs. percibida

Compara la imagen de un destino que proyecta su organización de marketing (DMO) con la que perciben los visitantes en otras fuentes (reseñas, redes sociales, foros). El caso de estudio es la Ciudad de México: **Sectur CDMX** (DMO) frente a **TripAdvisor**, **Instagram** y **Reddit**.

Responde la pregunta del proyecto: **¿la imagen que proyecta la DMO coincide con la que perciben los visitantes? ¿En qué temas hay brechas y qué debería ajustar la DMO en su comunicación?** La respuesta, con las decisiones para la DMO y su evidencia, sale sola en la primera pestaña del tablero.

Funciona con **cualquier conjunto de archivos**. En el tablero basta con subir el archivo de los visitantes (Sectur CDMX ya viene cargada como DMO) y presionar «Analizar». También se puede quitar Sectur y subir dos o más archivos: uno de la DMO y uno o más de visitantes, en CSV, TSV, TXT, Excel (xlsx, xls), JSON, JSONL o Parquet. El número de temas lo determina el propio análisis.

Proyecto final de Visualización de Datos. Alejandro Castillo Avalos, Ingeniería de Datos e Inteligencia Artificial, DICIS, Universidad de Guanajuato.

## Contenido

1. [Qué incluye](#qué-incluye)
2. [Requisitos: Python y librerías](#requisitos-python-y-librerías)
3. [Instalación paso a paso](#instalación-paso-a-paso)
4. [Usar el tablero](#usar-el-tablero)
5. [Publicar el tablero en internet (Streamlit Community Cloud)](#publicar-el-tablero-en-internet-streamlit-community-cloud)
6. [Actualizar el repositorio desde la página de GitHub](#actualizar-el-repositorio-desde-la-página-de-github)
7. [Uso desde la terminal](#uso-desde-la-terminal)
8. [Qué hace cada paso](#qué-hace-cada-paso)
9. [Estructura del repositorio](#estructura-del-repositorio)
10. [Problemas comunes](#problemas-comunes)
11. [Verificación](#verificación)

## Qué incluye

Dos piezas que usan exactamente el mismo código (`pipeline/analisis.py`), así que dicen lo mismo:

- **`app.py`**: el tablero web de Streamlit. Tiene dos modos:
  - **«Subir mis archivos»**: se suben los archivos, se presiona «Analizar» y el tablero corre los 8 pasos del análisis.
  - **«Ejemplo: Ciudad de México»**: muestra al instante el análisis ya hecho del caso, guardado en `salidas/`.
- **`analizador.py`**: el mismo análisis desde la terminal. Escribe los resultados en `salidas/`.

Todo corre en la computadora, sin conexión: no se usa ninguna API externa ni se envía ningún texto a otro servicio. El resultado no depende del orden en que se suban los archivos, de su nombre ni del orden de sus filas.

El tablero en línea es https://imagen-destino-cdmx.streamlit.app. Es privado: sólo entran las cuentas invitadas (ver [Publicar el tablero](#publicar-el-tablero-en-internet-streamlit-community-cloud)).

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
| `streamlit` | 1.67.0 | 1.50 | El tablero web |
| `langdetect` | 1.0.9 | 1.0.9 | Detectar el idioma de cada comentario |
| `stopwordsiso` | 0.7.1 | 0.6.1 | Palabras vacías («de», «la», «que») de muchos idiomas |
| `simplemma` | 2.0.0 | 1.0 | Lematizar («tacos» → «taco», «cuesta» → «costar») |
| `emoji` | 2.16.0 | 2.8 | Quitar emojis |
| `vaderSentiment` | 3.3.2 | 3.3.2 | Tono en inglés |
| `wordcloud` | 1.9.6 | 1.9.3 | Nubes de palabras |
| `openpyxl` | 3.1.5 | 3.1 | Leer archivos `.xlsx` subidos |
| `xlrd` | 2.0.2 | 2.0 | Leer archivos `.xls` subidos |

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

Un entorno virtual guarda las librerías del proyecto aparte de las del sistema. Abre la terminal **dentro de la carpeta del proyecto** (la que tiene `app.py`) y ejecuta:

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

Al activarlo, la línea de la terminal empieza con `(.venv)`. Cada vez que abras una terminal nueva para usar el proyecto, vuelve a activarlo con la segunda línea.

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

### 5. Abre el tablero

```bash
streamlit run app.py
```

Se abre solo en el navegador en http://localhost:8501. Si no se abre, copia esa dirección en el navegador. Para cerrarlo, en la terminal presiona `Ctrl+C`.

## Usar el tablero

### Analizar archivos nuevos (modo «Subir mis archivos»)

1. En la barra lateral, deja marcado **«Subir mis archivos»**.
2. La casilla **«Comparar contra Sectur CDMX (ya cargada)»** está activada: Sectur ya está cargada como DMO (`datos/originales/sectur.csv`).
3. En **«Archivos»**, arrastra el archivo con lo que publican los visitantes, o varios, uno por fuente.
4. Arriba del botón aparece una línea que resume qué se va a comparar, por ejemplo: «Se va a comparar la DMO, Sectur (487 textos), con TripAdvisor (22,128)… · idioma: español».
5. Presiona **«Analizar»**. Una barra muestra el avance; con las 4 bases tarda unos 3 minutos.
6. Aparecen las nueve pestañas, la primera con las conclusiones. El reporte HTML se descarga con el botón de la barra lateral.

**Cómo deben venir los archivos.** Una fila por comentario y una columna con el texto. El nombre del archivo se usa como nombre de la fuente; reconoce solo Instagram, Reddit y TripAdvisor. Se aceptan CSV, TSV, TXT, Excel (`.xlsx`, `.xls`), JSON, JSONL y Parquet, también comprimidos con `.gz`, de hasta 200 MB cada uno. Las demás columnas (fecha, calificación, etc.) se ignoran. Si una celda trae varios comentarios juntos separados por « - », como las respuestas de un hilo de Reddit, se separan solos.

**Todo lo demás es automático.** Las columnas de texto, el idioma (el más frecuente en los archivos), el número de temas y los demás parámetros se detectan solos. Si se quiere cambiar algo, está en el desplegable **«Ajustes (opcional)»**:

- Por cada archivo: el nombre de la fuente, las columnas de texto, la columna con varios comentarios por celda y su separador.
- Cuál es la DMO.
- El idioma.
- El título.
- Las palabras a ignorar. Con Sectur vienen ya: `mexico, ciudad, cdmx, df, city`, porque el nombre del destino aparece en todo y no distingue temas.
- El número de temas (0 = lo elige el análisis).
- El % de atípicos a separar (3 % por defecto).
- La idea a rastrear («precio valor costo»).

**Usar otra DMO.** Quita la casilla de Sectur y sube dos o más archivos: el de la DMO y los de visitantes. Si todas las fuentes vienen en un solo archivo con una columna que dice la fuente, súbelo solo y activa en «Ajustes» el interruptor «Mi archivo trae varias fuentes en una columna». Los comentarios en un idioma distinto al elegido se dejan fuera; para analizarlos, vuelve a correr con ese idioma.

**Reproducir el caso CDMX.** Sube `TripAdvisor.csv.gz`, `instaUGC.csv` y `redditcdmx.csv` de `datos/originales/` (Sectur ya está cargada) y presiona «Analizar». El resultado es idéntico al del modo ejemplo.

### Ver el análisis ya hecho (modo «Ejemplo: Ciudad de México»)

En la barra lateral, elige **«Ejemplo: Ciudad de México»**. Abre al instante los resultados guardados en `salidas/`. Hay dos: en español (el principal) y en inglés (exploratorio, porque la DMO tiene pocos textos en inglés).

### Las nueve pestañas

- **Conclusiones**: responde la pregunta del proyecto con una respuesta corta, indicadores y **decisiones para la DMO** ordenadas por prioridad, cada una con su evidencia. Los tipos de decisión son: replantear, incorporar, atender, informar, ajustar enfoque o tono, canal, vigilar y mantener. Se generan solas, con las mismas reglas, para cualquier conjunto de archivos (`pipeline/conclusiones.py`). Los umbrales se muestran en la pestaña. Las conclusiones también van en el reporte HTML, en la terminal y se descargan como texto.
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
- **Precio, valor y costo**: cercanía semántica con la idea y, como complemento, mención literal con BM25.
- **Comentarios atípicos**: unigramas, bigramas y trigramas de toda la base y de cada fuente.

Paletas aptas para daltonismo, en la barra lateral:
- **Okabe-Ito** (por defecto): colores muy distintos entre sí. Se amplía con la paleta «muted» de Paul Tol cuando hay más de 8 categorías.
- viridis, cividis, plasma, inferno y magma.

Cada fuente conserva siempre el mismo color y la misma forma; la DMO es siempre el cuadrado.

## Publicar el tablero en internet (Streamlit Community Cloud)

Así se publicó https://imagen-destino-cdmx.streamlit.app. Es gratis y no necesita servidor propio: Streamlit lee el repositorio de GitHub y corre `app.py`.

1. Entra a https://share.streamlit.io e inicia sesión **con la cuenta de GitHub dueña del repositorio**. La primera vez, autoriza a Streamlit a ver tus repositorios, incluidos los privados.
2. Presiona **«Create app»** y elige desplegar una app que ya está en GitHub.
3. Llena el formulario:
   - **Repository:** `Castillo322/imagen-destino-dmo`
   - **Branch:** `main`
   - **Main file path:** `app.py`. Escríbelo completo; el autocompletado puede proponer otro archivo, como `entrenar_sentimiento.py`.
   - **App URL:** el nombre de la dirección, por ejemplo `imagen-destino-cdmx`.
4. Abre **«Advanced settings»** y en **Python version** elige **3.13**. No hace falta agregar *secrets*: el proyecto no usa contraseñas ni APIs.
5. Presiona **«Deploy»**. La primera vez instala las librerías de `requirements.txt` y tarda unos minutos. Cuando termina, aparece el tablero.

**Quién puede entrar.** Como el repositorio es privado, la app también lo es: sólo la ven las cuentas invitadas. Para invitar a alguien, abre la app, presiona **«Share»** (arriba a la derecha) y escribe su correo. Esa persona recibe un correo y entra con la cuenta de ese correo. En el mismo menú está la opción para hacerla pública, que permite entrar a cualquiera con el enlace. El repositorio es privado porque `datos/` y `salidas/` contienen publicaciones reales.

**Actualizaciones.** Cada vez que se sube un cambio a la rama `main` de GitHub, la app se actualiza sola en uno o dos minutos. Si no se actualiza, en la app abre **«Manage app»** (abajo a la derecha) y usa **«Reboot app»**. Si la app pasa un tiempo sin visitas, se «duerme»: al abrirla aparece un botón para despertarla y tarda un poco en volver.

## Actualizar el repositorio desde la página de GitHub

No hace falta saber git: todo se puede hacer desde la página del repositorio.

- **Subir o reemplazar archivos:** **«Add file» › «Upload files»**. Arrastra los archivos o carpetas; un archivo con el mismo nombre y ubicación se reemplaza. Para una subcarpeta, arrastra la carpeta completa o entra primero a esa carpeta en GitHub. Escribe una descripción y presiona **«Commit changes»**.
- **Borrar un archivo:** ábrelo, presiona **«…»** (arriba a la derecha) › **«Delete file»** › **«Commit changes»**. Queda en el historial, así que se puede recuperar.
- **Límite de la página:** 25 MB por archivo. Por eso los archivos más pesados van comprimidos con gzip:
  - `datos/cdmx_unificado.csv.gz`
  - `datos/originales/TripAdvisor.csv.gz`
  - `salidas/*/reporte.html.gz`

  El script y el tablero los leen así, sin descomprimirlos.
- **No subas** la carpeta `.venv/`, carpetas `__pycache__/`, archivos `.DS_Store` de macOS ni ZIP del proyecto: no hacen falta y GitHub no descomprime los ZIP.

## Uso desde la terminal

Con el entorno virtual activado y dentro de la carpeta del proyecto. El script pide 7 parámetros obligatorios:

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

En Windows, escribe el comando en una sola línea (sin `\`) o cambia `\` por `^` en el Símbolo del sistema o por `` ` `` en PowerShell.

| # | Parámetro | Qué es |
|---|-----------|--------|
| 1 | `--csv` | Un archivo unificado (una fila por comentario) **o varios archivos, uno por fuente**. Formatos: csv, tsv, txt, xlsx, xls, json, jsonl, parquet (también `.gz`) |
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

El script no supone nombres ni número de fuentes: los toma del archivo. Por ejemplo, con el CSV de ejemplo, que usa otros nombres de columnas:

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

Al terminar imprime:
- cuántos temas encontró;
- las conclusiones para la DMO;
- el resumen de brechas;
- la comparación de la DMO con cada fuente.

Para el corpus en inglés (sobre todo Reddit):

```bash
python analizador.py --csv datos/cdmx_unificado.csv.gz --columna_texto texto --columna_fuente fuente \
  --etiqueta_dmo sectur --idioma en --titulo "Imagen de la Ciudad de México" --paleta viridis \
  --excluir "mexico,city,cdmx,mexican"
```

### Salidas

En `salidas/<titulo>_<idioma>/`:

- `corpus_procesado.parquet`: una fila por comentario. Para cada uno guarda:
  - su fuente y su texto original;
  - los lemas (el texto ya limpio y lematizado);
  - si es atípico, su tono y su tema;
  - su cercanía con el concepto y su puntaje BM25 del concepto;
  - sus coordenadas en el mapa.
- `resultados.json`: todos los resultados agregados, incluidas las conclusiones. Es lo que lee el tablero.
- `reporte.html`: reporte interactivo autocontenido (funciona sin conexión). En el repositorio va comprimido (`reporte.html.gz`); desde el tablero se descarga ya descomprimido.

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
     - el parecido global (coseno de centroides LSA);
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
app.py                     tablero de Streamlit
analizador.py              el mismo análisis desde la terminal (CLI)
requirements.txt           librerías que se instalan con pip
README.md                  este archivo
VERIFICACION.md            qué se comprobó y cómo (requisitos y robustez)
verificar_requisitos.py    prueba cada requisito con datos nuevos
entrenar_sentimiento.py    entrena el modelo de tono en español
unificar_fuentes.py        une las 4 bases originales en datos/cdmx_unificado.csv.gz
.gitignore                 archivos que git no debe subir
.streamlit/config.toml     colores y ajustes del tablero
pipeline/                  el análisis, un módulo por paso:
  analisis.py                encadena los 8 pasos (lo usan app.py y analizador.py)
  lectura.py                 lee cualquier formato y propone columnas
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
  originales/                las 4 bases tal como se entregaron (sectur.csv es la DMO que usa el tablero)
  cdmx_unificado.csv.gz      las 4 bases unidas en un archivo
  ejemplo.csv                CSV chico y anonimizado para pruebas
modelos/                     modelo de tono en español y sus métricas
salidas/                     resultados del ejemplo CDMX (español e inglés); los lee el tablero
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
| «Port 8501 is already in use» | Ya hay un tablero abierto. Ciérralo, o usa otro puerto: `streamlit run app.py --server.port 8502`. |
| El tablero dice que se necesitan al menos dos fuentes | Deja activada «Comparar contra Sectur CDMX», sube otro archivo o, si tu archivo trae varias fuentes en una columna, indícalo en «Ajustes». |
| Faltan muchos comentarios en los conteos | Se analizan sólo los del idioma elegido. Revisa el idioma en «Ajustes». |
| La app en línea muestra un error o no se actualiza | En la app, «Manage app» › «Reboot app». Los registros de instalación están en ese mismo panel. |
| La app en línea pide iniciar sesión o dice que no tienes acceso | Es privada: el dueño tiene que invitar tu correo con «Share». |

## Verificación

`python verificar_requisitos.py` corre el script con datos que no ha visto: otras columnas, otras fuentes y archivos sueltos en xlsx, json, txt y tsv. Revisa cada requisito del proyecto, incluidos el tablero, BM25, la comparación con cada fuente y las conclusiones: 43 comprobaciones, todas correctas. Los resultados y las pruebas de robustez están en `VERIFICACION.md`.
