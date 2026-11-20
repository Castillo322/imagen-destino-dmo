"""BM25 (Okapi): relevancia de cada comentario para una consulta de palabras.

Se usa para recuperar evidencia cualitativa (los comentarios de cada fuente que mejor representan un
tema o un concepto) y para el buscador del tablero. A diferencia de TF-IDF, BM25 satura la frecuencia
de una palabra (k1) y corrige por la longitud del comentario (b), así los textos muy largos no ganan
sólo por repetir palabras (Robertson y Zaragoza, 2009).
"""
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer


class BM25:
    def __init__(self, documentos, k1=1.5, b=0.75):
        """`documentos`: lemas separados por espacio, uno por comentario."""
        self.k1, self.b = k1, b
        docs = ["" if d is None else str(d) for d in documentos]
        self.cv = CountVectorizer(tokenizer=str.split, lowercase=False, token_pattern=None)
        try:
            self.X = self.cv.fit_transform(docs).tocsc()
        except ValueError:  # vocabulario vacío
            self.X = None
            return
        self.voc = self.cv.vocabulary_
        largo = np.asarray(self.X.sum(1)).ravel()
        self.norma = k1 * (1 - b + b * largo / max(largo.mean(), 1e-9))
        n = self.X.shape[0]
        df = np.diff(self.X.indptr)
        self.idf = np.log((n - df + 0.5) / (df + 0.5) + 1.0)  # versión sin valores negativos

    def puntajes(self, consulta):
        """Puntaje BM25 de cada documento para la consulta (lemas separados por espacio o lista)."""
        if self.X is None:
            return np.zeros(0)
        terminos = consulta.split() if isinstance(consulta, str) else list(consulta)
        out = np.zeros(self.X.shape[0])
        for t in dict.fromkeys(terminos):
            j = self.voc.get(t)
            if j is None:
                continue
            col = self.X.getcol(j)
            filas, tf = col.indices, col.data.astype(float)
            out[filas] += self.idf[j] * tf * (self.k1 + 1) / (tf + self.norma[filas])
        return out

    def mejores(self, consulta, k=5, mascara=None):
        """Índices (posiciones) de los `k` documentos con mayor puntaje > 0, opcionalmente dentro de `mascara`."""
        s = self.puntajes(consulta)
        if mascara is not None:
            s = np.where(mascara, s, 0)
        orden = np.argsort(-s)[:k]
        return [int(i) for i in orden if s[i] > 0]
