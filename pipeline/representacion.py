"""Representación vectorial común a todo el pipeline: TF-IDF + LSA (TruncatedSVD).

El espacio se ajusta con una muestra balanceada por fuente (tope `max_por_fuente`) para que
la fuente más grande no defina por sí sola el vocabulario ni las dimensiones latentes, y luego
se aplica a todos los comentarios.
"""
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


def muestra_balanceada(fuentes, max_por_fuente, semilla):
    idx = []
    fuentes = np.asarray(fuentes)
    for f in np.unique(fuentes):
        pos = np.flatnonzero(fuentes == f)
        if len(pos) > max_por_fuente:
            # un generador por fuente: la muestra de una fuente no depende del nombre ni del número de las demás
            pos = np.random.default_rng([semilla, len(pos)]).choice(pos, max_por_fuente, replace=False)
        idx.extend(pos.tolist())
    return np.sort(np.array(idx, dtype=int))


def nuevo_vectorizador(n_docs, ngramas=(1, 1)):
    return TfidfVectorizer(tokenizer=str.split, preprocessor=None, lowercase=False, token_pattern=None,
                           ngram_range=ngramas, min_df=2 if n_docs < 500 else 3, max_df=0.5, sublinear_tf=True)


class EspacioLSA:
    def __init__(self, dimensiones=100, semilla=42):
        self.dimensiones, self.semilla = dimensiones, semilla

    def ajustar(self, lemas, fuentes, max_por_fuente):
        lemas = np.asarray(lemas, dtype=object)
        idx = muestra_balanceada(fuentes, max_por_fuente, self.semilla)
        self.vec = nuevo_vectorizador(len(idx))
        Xs = self.vec.fit_transform(lemas[idx])
        k = max(2, min(self.dimensiones, Xs.shape[1] - 1, Xs.shape[0] - 1))
        self.svd = TruncatedSVD(k, random_state=self.semilla).fit(Xs)
        self.X = self.vec.transform(lemas)              # TF-IDF de todos los comentarios
        self.Z = normalize(self.svd.transform(self.X))  # vectores LSA normalizados
        return self

    def proyectar_texto(self, lemas_consulta: str):
        """Proyecta una consulta (lemas) al espacio latente ("folding-in")."""
        q = self.svd.transform(self.vec.transform([lemas_consulta]))
        return normalize(q)[0]

    def terminos_cercanos(self, vector, formas, k=20):
        """Términos del vocabulario más cercanos a un vector latente (evidencia del concepto)."""
        T = normalize(self.svd.components_.T * self.svd.singular_values_)
        sims = T @ vector
        orden = np.argsort(sims)[::-1][:k]
        vocab = self.vec.get_feature_names_out()
        return [(formas.get(vocab[i], vocab[i]), round(float(sims[i]), 3)) for i in orden]
