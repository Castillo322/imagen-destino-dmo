"""
unificar_fuentes.py
-------------------
Une las 4 bases del caso CDMX en un solo CSV con columna de fuente,
tal como lo pide el Proyecto Final (parámetros 1-4 del CLI).

Fuentes:
  - sectur.csv      -> fuente = "sectur"       (DMO: imagen proyectada)
  - TripAdvisor.csv -> fuente = "tripadvisor"  (imagen percibida)
  - instaUGC.csv    -> fuente = "instagram"    (imagen percibida)
  - redditcdmx.csv  -> fuente = "reddit"       (imagen percibida)

Decisiones de unificación (documentadas en el Avance 1):
  * Se conserva la metadata útil de cada fuente en columnas opcionales
    (rating, fecha, clase_dmo, num_comentarios, tipo). El script final
    sólo necesita `texto` y `fuente`; el resto enriquece el tablero.
  * Reddit: cada publicación genera un registro "post" (título + cuerpo)
    y sus comentarios se separan en registros "comentario" (vienen
    concatenados con " - "). Se eliminan los avisos automáticos del bot
    de r/travel ("I am a bot ...") y los comentarios borrados/redactados.
  * TripAdvisor: la columna `target` es la calificación 1-5. Una fila
    trae texto en `target` (error de scraping) y 313 filas traen el error
    "Error: 'float' object has no attribute 'lower'" en `date`; se
    conservan con rating/fecha nulos y se marcan en `flag_calidad`.

Uso:
    python unificar_fuentes.py --dir CDMX --salida cdmx_unificado.csv
"""
import argparse
import re
from pathlib import Path

import pandas as pd

BOT_PATTERNS = [
    r"i am a bot", r"this action was performed automatically",
    r"are you asking for travel advice", r"weekly destination thread",
    r"mass deleted and anonymized", r"\[deleted\]", r"\[removed\]",
]
BOT_RE = re.compile("|".join(BOT_PATTERNS), flags=re.I)


def _buscar(directorio: Path, nombre: str) -> Path:
    """Encuentra el archivo aunque tenga prefijo (p. ej. 'a30fa1d0-TripAdvisor.csv')."""
    candidatos = sorted(directorio.glob(f"*{nombre}")) or sorted(directorio.glob(f"*{nombre}.gz"))
    if not candidatos:
        raise FileNotFoundError(f"No encontré {nombre} en {directorio}")
    return candidatos[0]


def cargar_sectur(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    return pd.DataFrame({
        "fuente": "sectur", "tipo": "pagina_guia", "texto": df["texto"],
        "clase_dmo": df["clase"],
    })


def cargar_tripadvisor(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    rating = pd.to_numeric(df["target"], errors="coerce")
    fecha = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
    flag = []
    for r, f in zip(rating, fecha):
        motivos = []
        if pd.isna(r):
            motivos.append("rating_invalido")
        if pd.isna(f):
            motivos.append("fecha_error_scraping")
        flag.append(";".join(motivos))
    return pd.DataFrame({
        "fuente": "tripadvisor", "tipo": "resena", "texto": df["texto"],
        "rating": rating, "fecha": fecha, "flag_calidad": flag,
    })


def cargar_instagram(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    return pd.DataFrame({"fuente": "instagram", "tipo": "post", "texto": df["description"]})


def cargar_reddit(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    filas = []
    for i, r in df.iterrows():
        cuerpo = r["text"] if isinstance(r["text"], str) else ""
        filas.append({
            "fuente": "reddit", "tipo": "post", "hilo_id": i,
            "texto": f"{r['title']}. {cuerpo}".strip(),
            "num_comentarios": r["num_comments"],
        })
        if isinstance(r["comments"], str):
            for c in r["comments"].split(" - "):
                c = re.sub(r"\s+", " ", c).strip()
                if len(c.split()) < 3 or BOT_RE.search(c):
                    continue
                filas.append({"fuente": "reddit", "tipo": "comentario", "hilo_id": i, "texto": c})
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser(description="Unifica las 4 bases CDMX en un solo CSV")
    ap.add_argument("--dir", default="CDMX", help="Carpeta con los 4 CSV")
    ap.add_argument("--salida", default="cdmx_unificado.csv")
    ap.add_argument("--sin-comentarios-reddit", action="store_true",
                    help="Sólo publicaciones de Reddit (sin comentarios)")
    a = ap.parse_args()
    d = Path(a.dir)

    partes = [
        cargar_sectur(_buscar(d, "sectur.csv")),
        cargar_tripadvisor(_buscar(d, "TripAdvisor.csv")),
        cargar_instagram(_buscar(d, "instaUGC.csv")),
        cargar_reddit(_buscar(d, "redditcdmx.csv")),
    ]
    df = pd.concat(partes, ignore_index=True)
    if a.sin_comentarios_reddit:
        df = df[~((df.fuente == "reddit") & (df.tipo == "comentario"))]

    df["texto"] = df["texto"].astype(str).str.strip()
    df = df[df["texto"].str.len() > 0].reset_index(drop=True)
    df.insert(0, "id", [f"{f[:2].upper()}{i:06d}" for i, f in enumerate(df["fuente"])])
    df["flag_calidad"] = df.get("flag_calidad", "").fillna("")
    columnas = ["id", "fuente", "tipo", "texto", "rating", "fecha", "clase_dmo",
                "num_comentarios", "hilo_id", "flag_calidad"]
    df = df[columnas]
    df.to_csv(a.salida, index=False, encoding="utf-8")
    print(f"Guardado {a.salida}: {len(df):,} registros")
    print(df.groupby(["fuente", "tipo"]).size().to_string())


if __name__ == "__main__":
    main()
