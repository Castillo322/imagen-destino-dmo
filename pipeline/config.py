"""Valores por defecto y constantes compartidas por el pipeline."""

# Paletas aptas para daltonismo: Okabe-Ito (categórica) y las de matplotlib perceptualmente uniformes.
PALETAS_ACCESIBLES = ["okabe_ito", "viridis", "cividis", "plasma", "inferno", "magma"]

# Concepto sintético "precio / valor / costo" expresado en cada idioma soportado.
CONCEPTO_POR_IDIOMA = {
    "es": "precio valor costo",
    "en": "price value cost",
    "fr": "prix valeur coût",
    "pt": "preço valor custo",
    "it": "prezzo valore costo",
    "de": "preis wert kosten",
}

SEMILLA = 42
CONTAMINACION_OUTLIERS = 0.03     # proporción esperada de comentarios atípicos por fuente
UMBRAL_TOPICOS = 30               # partición con menos comentarios -> frecuencias en lugar de tópicos
MAX_POR_FUENTE = 2000             # tope por fuente al ajustar los modelos (evita que una fuente domine)
K_TOPICOS = range(5, 16)          # número de tópicos candidatos; se elige por coherencia ponderada x diversidad
MAX_POR_FUENTE_TOPICOS = 1000     # tope por fuente al ajustar los modelos de tópicos
PALABRAS_POR_TOPICO = 10
UMBRAL_BRECHA_PP = 5.0            # diferencia mínima (puntos porcentuales) para llamar brecha a un tema
PERCENTIL_CONCEPTO = 95           # similitud mínima (percentil) para considerar un comentario ligado al concepto
MAX_PUNTOS_MAPA_POR_FUENTE = 1200 # muestra estratificada para el mapa de dispersión
