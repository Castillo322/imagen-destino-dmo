"""Lectura de cualquier archivo de texto tabular y armado de la base unificada.

Formatos: .csv, .tsv, .txt (un comentario por línea, o tabla si tiene separador), .xlsx, .xls,
.json, .jsonl y .parquet. Cada archivo puede ser una fuente distinta (por ejemplo, el archivo de
la DMO y uno por cada plataforma) o una sola tabla que ya trae una columna de fuente.
Todo corre sin conexión.
"""
import csv
import gzip
import io
import json
import re
from pathlib import Path

import pandas as pd

FORMATOS = ("csv", "tsv", "txt", "xlsx", "xls", "json", "jsonl", "parquet")
# avisos automáticos y comentarios borrados, comunes en foros
_RUIDO = re.compile(r"i am a bot|this action was performed automatically|\[deleted\]|\[removed\]|"
                    r"mass deleted and anonymized", re.I)


def _bytes(origen):
    if isinstance(origen, (str, Path)):
        return Path(origen).read_bytes()
    if hasattr(origen, "getvalue"):
        return origen.getvalue()
    if hasattr(origen, "read"):
        return origen.read()
    return bytes(origen)


def _decodificar(datos: bytes) -> str:
    for cod in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return datos.decode(cod)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


def _tabla_texto(texto: str, separador=None) -> pd.DataFrame:
    if separador is None:
        muestra = texto[:20000]
        try:
            separador = csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
        except csv.Error:
            separador = ","
    return pd.read_csv(io.StringIO(texto), sep=separador, engine="python" if separador not in (",", "\t", ";") else "c",
                       on_bad_lines="skip")


def leer_archivo(origen, nombre=None) -> pd.DataFrame:
    """Devuelve una tabla con lo que traiga el archivo. `origen`: ruta, bytes o archivo subido."""
    nombre = str(nombre or origen)
    datos = _bytes(origen)
    if nombre.lower().endswith(".gz") or datos[:2] == b"\x1f\x8b":  # comprimido con gzip (p. ej. datos.csv.gz)
        datos = gzip.decompress(datos)
        nombre = nombre[:-3] if nombre.lower().endswith(".gz") else nombre
    ext = Path(nombre).suffix.lower().lstrip(".")
    if ext not in FORMATOS:
        raise ValueError(f"Formato «.{ext}» no soportado. Usa uno de: {', '.join(FORMATOS)} (también comprimidos con .gz).")
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(datos))
    elif ext == "parquet":
        df = pd.read_parquet(io.BytesIO(datos))
    elif ext == "jsonl":
        df = pd.read_json(io.StringIO(_decodificar(datos)), lines=True)
    elif ext == "json":
        obj = json.loads(_decodificar(datos))
        if isinstance(obj, dict):
            # {"comentarios": [...]} o {"col": [...], ...}
            listas = [v for v in obj.values() if isinstance(v, list)]
            obj = listas[0] if len(listas) == 1 and not all(isinstance(v, list) for v in obj.values()) else obj
        if isinstance(obj, list) and obj and all(isinstance(x, str) for x in obj):
            df = pd.DataFrame({"texto": obj})
        else:
            df = pd.json_normalize(obj) if isinstance(obj, list) else pd.DataFrame(obj)
    elif ext == "tsv":
        df = _tabla_texto(_decodificar(datos), "\t")
    elif ext == "csv":
        df = _tabla_texto(_decodificar(datos))
    else:  # txt: tabla si las líneas comparten separador; si no, un comentario por línea
        texto = _decodificar(datos)
        lineas = [l for l in texto.splitlines() if l.strip()]
        try:
            dialecto = csv.Sniffer().sniff("\n".join(lineas[:50]), delimiters=",;\t|")
            df = _tabla_texto(texto, dialecto.delimiter)
            if df.shape[1] < 2:
                raise csv.Error
        except (csv.Error, pd.errors.ParserError):
            df = pd.DataFrame({"texto": lineas})
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if not c.lower().startswith("unnamed")] or df.columns]
    return df.dropna(axis=1, how="all")


def columnas_de_texto(df: pd.DataFrame):
    """Columnas candidatas a texto, de la más probable a la menos (por longitud media)."""
    cand = []
    for c in df.columns:
        s = df[c].dropna()
        if s.empty or not (s.dtype == object or str(s.dtype).startswith("str") or str(s.dtype) == "string"):
            continue
        s = s.astype(str)
        largo = s.str.len().mean()
        if s.str.fullmatch(r"[\d\s/:.\-]+").mean() > 0.8:  # fechas o números
            continue
        cand.append((largo, c))
    return [c for _, c in sorted(cand, reverse=True)]


def sugerir_columnas(df: pd.DataFrame, separador=" - "):
    """Propuesta automática: (columnas de texto a unir, columna con varios comentarios por celda o None).

    Se descartan columnas categóricas cortas (p. ej. una «clase» con pocos valores distintos). Una columna
    cuya celda típica trae dos o más veces el separador se trata como lista de comentarios (respuestas de un foro).
    """
    cand = columnas_de_texto(df)
    if not cand:
        return [], None
    lista = None
    for c in cand:
        s = df[c].dropna().astype(str)
        if len(s) and s.str.count(re.escape(separador)).median() >= 2:
            lista = c
            break
    largo = {c: df[c].dropna().astype(str).str.len().mean() for c in cand}
    textos = []
    for c in cand:
        if c == lista:
            continue
        s = df[c].dropna().astype(str)
        categorica = s.nunique() <= max(20, 0.05 * len(s)) and largo[c] < 40
        if not categorica and largo[c] >= 15:
            textos.append(c)
    if not textos and not lista:
        textos = cand[:1]
    orden = list(df.columns)
    return sorted(textos, key=orden.index), lista


def sugerir_dmo(nombres):
    """El archivo que parece de la DMO (por su nombre); si ninguno, el primero."""
    for n in nombres:
        if re.search(r"dmo|sectur|secretar|turismo|oficial|visit|tourism|gobierno|gob", str(n), re.I):
            return n
    return nombres[0] if nombres else None


def armar_fuente(df: pd.DataFrame, columnas_texto, nombre_fuente: str, columna_lista=None, separador=" - ") -> pd.DataFrame:
    """Una fila por comentario con columnas `texto` y `fuente`.

    Varias columnas de texto se unen (p. ej. título y cuerpo). `columna_lista` es una columna que trae
    varios comentarios en una misma celda (p. ej. respuestas de un foro) separados por `separador`;
    cada uno se vuelve un registro aparte.
    """
    columnas_texto = [c for c in (columnas_texto or []) if c in df.columns]
    partes = []
    if columnas_texto:
        t = df[columnas_texto].astype("string").fillna("").agg(". ".join, axis=1).str.strip(". ")
        partes.append(pd.DataFrame({"texto": t, "tipo": "texto"}))
    if columna_lista and columna_lista in df.columns:
        sueltos = df[columna_lista].dropna().astype(str).str.split(re.escape(separador)).explode()
        sueltos = sueltos.str.replace(r"\s+", " ", regex=True).str.strip()
        sueltos = sueltos[sueltos.str.split().str.len() >= 3]  # fragmentos sueltos que dejó el separador
        partes.append(pd.DataFrame({"texto": sueltos, "tipo": "comentario"}))
    if not partes:
        raise ValueError(f"Elige al menos una columna de texto para «{nombre_fuente}».")
    out = pd.concat(partes, ignore_index=True)
    out = out[out.texto.str.len().fillna(0) > 0]
    out = out[~out.texto.str.contains(_RUIDO, na=False)]
    out.insert(0, "fuente", str(nombre_fuente).strip())
    return out.reset_index(drop=True)


_CONOCIDAS = ((r"insta", "instagram"), (r"reddit", "reddit"), (r"trip[\s_-]*advisor", "tripadvisor"), (r"sectur", "sectur"))


def nombre_sugerido(nombre_archivo) -> str:
    """Nombre de la fuente a partir del archivo; reconoce las fuentes conocidas («instaUGC.csv» -> instagram,
    «redditcdmx.csv» -> reddit, «TripAdvisor.csv.gz» -> tripadvisor). Cualquier otro: el nombre del archivo."""
    base = nombre_de_archivo(nombre_archivo)
    for patron, nom in _CONOCIDAS:
        if re.search(patron, base, re.I):
            return nom
    return base


def nombre_de_archivo(nombre: str) -> str:
    """«a30fa1d0-TripAdvisor.csv» -> «TripAdvisor»: quita la extensión y prefijos de identificador."""
    base = Path(str(nombre)).name
    base = re.sub(r"\.gz$", "", base, flags=re.I)
    base = Path(base).stem
    base = re.sub(r"^[0-9a-f]{6,}[-_]", "", base)
    return base.strip() or "fuente"
