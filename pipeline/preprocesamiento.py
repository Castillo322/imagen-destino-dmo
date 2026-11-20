"""Paso 1. Limpieza, detección de idioma, tokenización, stopwords y lematización.

Todo corre offline:
  * idioma: langdetect (semilla fija)
  * stopwords: stopwordsiso (listas ISO por idioma, incluidas en el paquete)
  * lematización: simplemma (diccionarios por idioma incluidos en el paquete)
La etiqueta de fuente nunca se toca: cada función recibe y devuelve columnas nuevas.
"""
import re
import unicodedata
from collections import Counter, defaultdict

import emoji
import simplemma
import stopwordsiso
from langdetect import DetectorFactory, detect_langs

DetectorFactory.seed = 0

URL_RE = re.compile(r"(https?://\S+|https?\s*:\s*\S+|www\.\S+)", re.I)
MENCION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#(\w+)")
TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # sólo letras (descarta números y signos)
# restos de enlaces que llegan sin puntuación (p. ej. "https youtu be ...")
RESTOS_WEB = {"http", "https", "www", "com", "html", "amp", "youtu", "utm", "jpg", "png", "gif"}
# enlaces que llegaron sin puntuación: "https www reddit com r travel comments 1na850q"
_DOMINIOS = {"com", "org", "net", "gov", "gob", "edu", "mx", "co", "uk", "ie", "jp", "br", "io", "gl", "be", "it", "ly",
             "info", "us", "es", "de", "fr", "ca", "au", "tv"}
_RUTA = {"www", "html", "htm", "php", "amp", "wiki", "watch", "v", "si", "r", "comments", "s", "p", "a", "gallery", "search",
         "q", "index", "gclid", "width", "png", "jpg", "preview", "redd", "m", "en", "es", "us", "feature", "share", "shorts",
         "status", "reel", "reels", "post", "posts", "app", "goo", "maps"}
_ENLACE_SUELTO = re.compile(r"(?<![\w:/])https?(?![\w:/])", re.I)


def _parece_id(w: str) -> bool:
    return any(c.isdigit() for c in w) or "_" in w or re.search(r"[a-z][A-Z]", w) is not None


def _parece_ruta(w: str) -> bool:
    return w.lower() in _RUTA or w.lower() in _DOMINIOS or _parece_id(w)


def quitar_enlaces_sin_puntuacion(t: str) -> str:
    """Quita «http(s) dominio ... tld ruta» cuando el enlace llegó con los signos convertidos en espacios."""
    if not _ENLACE_SUELTO.search(t):
        return t
    toks, out, i = t.split(), [], 0
    while i < len(toks):
        if toks[i].lower() in ("http", "https"):
            # dominio: el primer sufijo (com, gob, mx...) después del nombre, más los sufijos que le siguen (gob mx, co uk)
            fin = next((k for k in range(i + 2, min(i + 7, len(toks))) if toks[k].lower() in _DOMINIOS), None)
            while fin is not None and fin + 1 < len(toks) and toks[fin + 1].lower() in _DOMINIOS:
                fin += 1
            if fin is None:
                i += 1
                continue
            j = fin + 1
            while j < len(toks):
                if _parece_ruta(toks[j]):
                    j += 1
                elif j + 1 < len(toks) and (_parece_id(toks[j + 1]) or toks[j + 1].lower() in ("comments", "watch", "wiki", "gallery", "search")):
                    j += 2
                else:
                    break
            i = j
            continue
        out.append(toks[i])
        i += 1
    return " ".join(out)


def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def detectar_idioma(texto: str, por_defecto: str) -> str:
    """Idioma del comentario. Si langdetect duda (prob < 0.70) o falla, se asume el idioma objetivo."""
    try:
        mejor = detect_langs(str(texto)[:1000])[0]
        return mejor.lang if mejor.prob >= 0.70 else por_defecto
    except Exception:
        return por_defecto


def limpiar(texto: str) -> str:
    """Minúsculas, sin URLs, menciones, emojis, números ni signos. Los hashtags se vuelven palabras."""
    t = str(texto)
    t = URL_RE.sub(" ", t)
    t = quitar_enlaces_sin_puntuacion(t)
    t = MENCION_RE.sub(" ", t)
    t = HASHTAG_RE.sub(r" \1 ", t)
    t = emoji.replace_emoji(t, replace=" ")
    t = t.lower()
    t = " ".join(TOKEN_RE.findall(t))
    return t


# Palabras funcionales de otro idioma que se cuelan en comentarios mezclados (p. ej. un comentario en español con
# frases en inglés): no aportan tema y, sin quitarlas, aparecían como «palabras distintivas» de una fuente.
PALABRAS_FUNCION_EN = {"the", "and", "you", "not", "did", "is", "are", "was", "were", "it", "its", "of", "to", "in", "that",
                       "this", "for", "with", "be", "been", "have", "has", "my", "we", "they", "their", "your", "but", "or",
                       "what", "if", "just", "do", "does", "don", "i", "im", "at", "on", "by", "an", "as", "from", "would",
                       "there", "will", "about", "it's", "dont", "can", "so", "he", "she", "them", "our", "us", "which", "who"}
PALABRAS_FUNCION_ES = {"de", "la", "que", "el", "en", "los", "las", "del", "por", "para", "con", "una", "es", "muy", "pero",
                       "mas", "lo", "se", "su", "al", "como", "y", "un", "esta", "este", "le", "les", "sus", "ya", "hay"}


class Preprocesador:
    """Tokeniza, quita stopwords y lematiza en el idioma objetivo."""

    def __init__(self, idioma: str, excluir=(), conservar=()):
        self.idioma = idioma
        try:
            base = stopwordsiso.stopwords(idioma)
        except Exception:
            base = set()
        if not base:
            raise ValueError(f"No hay lista de stopwords para el idioma '{idioma}'.")
        self.stop = ({sin_acentos(w.lower()) for w in base} | {sin_acentos(w.lower().strip()) for w in excluir if w.strip()}
                     | RESTOS_WEB | (PALABRAS_FUNCION_ES if idioma == "en" else PALABRAS_FUNCION_EN))
        # palabras del concepto de interés: nunca se tratan como stopwords (p. ej. «valor» está en la lista ISO)
        self.stop -= {sin_acentos(w.lower().strip()) for w in conservar if w.strip()}
        # forma visible: clave sin acentos -> forma con acentos más frecuente en el corpus
        self._formas = defaultdict(Counter)

    def _lema(self, w: str) -> str:
        try:
            lema = simplemma.lemmatize(w, lang=self.idioma)
        except Exception:
            return w
        # el lematizador a veces devuelve abreviaturas con signos («rpm» -> «r.p.m.»): se quitan
        return re.sub(r"[^\w]+", "", lema) or w

    @staticmethod
    def _quitar_repeticiones(tokens):
        """Elimina rachas de un mismo token repetido 3+ veces seguidas (artefactos del texto)."""
        salida, i = [], 0
        while i < len(tokens):
            j = i
            while j + 1 < len(tokens) and tokens[j + 1] == tokens[i]:
                j += 1
            if j - i + 1 < 3:
                salida.extend(tokens[i:j + 1])
            i = j + 1
        return salida

    def tokens(self, texto_limpio: str):
        crudos = self._quitar_repeticiones(texto_limpio.split())
        salida = []
        for w in crudos:
            if len(w) < 3 or sin_acentos(w) in self.stop:
                continue
            lema = self._lema(w).lower()
            clave = sin_acentos(lema)
            if len(clave) < 3 or clave in self.stop:
                continue
            self._formas[clave][lema] += 1
            salida.append(clave)
        return salida

    def formas_visibles(self) -> dict:
        """Para mostrar palabras con acentos aunque el análisis use la forma sin acentos."""
        return {k: c.most_common(1)[0][0] for k, c in self._formas.items()}


def preprocesar(df, col_texto: str, idioma: str, excluir=(), cache=None, conservar=()):
    """Agrega: idioma_detectado, en_idioma_objetivo, texto_limpio, lemas (str), n_tokens.

    `cache` (opcional): archivo parquet donde se guarda el idioma detectado por texto, para que
    las corridas siguientes sobre el mismo CSV no repitan la detección (es el paso más lento).
    """
    import hashlib
    import pandas as pd
    df = df.copy()
    claves = df[col_texto].map(lambda t: hashlib.md5(str(t).encode("utf-8")).hexdigest())
    previo = {}
    if cache is not None and cache.exists():
        c = pd.read_parquet(cache)
        previo = dict(zip(c.clave, c.idioma))
    df["idioma_detectado"] = [previo.get(k) or detectar_idioma(t, idioma) for k, t in zip(claves, df[col_texto])]
    if cache is not None:
        pd.DataFrame({"clave": claves, "idioma": df["idioma_detectado"]}).drop_duplicates("clave").to_parquet(cache, index=False)
    df["en_idioma_objetivo"] = df["idioma_detectado"] == idioma
    df["texto_limpio"] = df[col_texto].map(limpiar)
    pre = Preprocesador(idioma, excluir, conservar)
    toks = [pre.tokens(t) if ok else [] for t, ok in zip(df["texto_limpio"], df["en_idioma_objetivo"])]
    df["lemas"] = [" ".join(t) for t in toks]
    df["n_tokens"] = [len(t) for t in toks]
    return df, pre.formas_visibles()
