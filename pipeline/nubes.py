"""Paso 4, condición especial: nubes de palabras a partir de frecuencias (sin conexión).

Cuando una partición tiene menos comentarios que el umbral, no se modelan tópicos y se describen sus
palabras más frecuentes. La nube es la vista rápida; la lista con conteos exactos acompaña siempre a la nube,
porque el tamaño de letra no permite comparar frecuencias con precisión.
"""
import base64
import colorsys
import io

from matplotlib.colors import to_rgb
from wordcloud import WordCloud


def _color_por_tamano(color_hex, tam_max):
    """Palabras grandes con el color de la fuente (oscurecido para que se lea sobre blanco); pequeñas, más claras."""
    h, l, s = colorsys.rgb_to_hls(*to_rgb(color_hex))
    base = min(l, 0.38)

    def f(word, font_size, position, orientation, random_state=None, **kw):
        t = min(1.0, font_size / max(tam_max, 1))
        r, g, b = colorsys.hls_to_rgb(h, base + (1 - t) * 0.16, max(s, 0.45))
        return f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"
    return f


def nube(frecuencias, color="#440154", ancho=640, alto=360, semilla=42, fuente=None, max_palabras=40):
    """Devuelve una imagen PIL o None si no hay palabras. `frecuencias`: lista de (palabra, conteo)."""
    frec = {str(w): float(n) for w, n in frecuencias if n and str(w).strip()}
    if not frec:
        return None
    tam_max = int(alto * 0.33)
    wc = WordCloud(width=ancho, height=alto, background_color="white", mode="RGB", max_words=max_palabras,
                   prefer_horizontal=1.0, random_state=semilla, font_path=fuente, margin=6, relative_scaling=0.45,
                   min_font_size=11, max_font_size=tam_max, color_func=_color_por_tamano(color, tam_max))
    return wc.generate_from_frequencies(frec).to_image()


def nube_png(frecuencias, **kw):
    img = nube(frecuencias, **kw)
    if img is None:
        return None
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def nube_base64(frecuencias, **kw):
    png = nube_png(frecuencias, **kw)
    return None if png is None else base64.b64encode(png).decode("ascii")
