# Capa de Limpieza. Aplica Regex para quitar basura, un diccionario manual para errores comunes y RapidFuzz para
# corrección ortográfica de nombres de héroes. Es lo que hace que el bot sea "inteligente" aunque el usuario escriba mal.

import re
from rapidfuzz import process

# Diccionario de errores comunes (Nivel Mínimo - Obligatorio)
DICCIONARIO_ERRORES = {
    "ruter": "router",
    "internat": "internet",
    "espiderman": "Spider-Man",
    "spaiderman": "Spider-Man",
    "baman": "Batman",
    "batmn": "Batman",
    "avenger": "Avengers",
    "vengadores": "Avengers",
    "batman": "Batman",
    "guason": "Joker",
    "jovenes titanes": "Young Justice",
    "titanes": "Teen Titans",
    "ironman": "Iron Man",
    "vengador": "Avengers"
}

# Vocabulario para corrección aproximada (Nivel Ideal)
VOCABULARIO_CLAVE = [
    "Spider-Man", "Avengers", "Batman", "Justice League", 
    "Superman", "Young Justice", "Iron Man", "Hulk", 
    "Thor", "Guardians of the Galaxy", "Harley Quinn",
    "Invincible", "Ben 10", "Voltron", "Green Lantern"
]

def normalizar_texto(texto):
    """Normalización básica: minúsculas y limpieza de espacios."""
    if not texto: return ""
    texto = texto.lower()
    texto = " ".join(texto.split())
    return texto

def limpiar_caracteres(texto):
    """Nivel Ideal: Quitar caracteres especiales usando Regex."""
    # Mantener letras, números, espacios y tildes comunes
    texto = re.sub(r"[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-\!\?]", "", texto)
    return texto

def corregir_diccionario(texto):
    """Nivel Mínimo: Uso de diccionario fijo."""
    palabras = texto.split()
    corregidas = []
    for p in palabras:
        # Buscamos si la palabra (en minúsculas) está en nuestro diccionario
        if p.lower() in DICCIONARIO_ERRORES:
            corregidas.append(DICCIONARIO_ERRORES[p.lower()])
        else:
            corregidas.append(p)
    return " ".join(corregidas)

def corregir_fuzzy(texto):
    """Nivel Ideal: Corrección aproximada con RapidFuzz."""
    palabras = texto.split()
    resultado = []
    for palabra in palabras:
        # Bajamos a score de 70 para ser más permisivos con nombres propios
        if len(palabra) >= 3:
            match = process.extractOne(palabra, VOCABULARIO_CLAVE, score_cutoff=70)
            if match:
                resultado.append(match[0])
                continue
        resultado.append(palabra)
    return " ".join(resultado)

def preprocesar_input(texto):
    """Pipeline completo de preprocesado."""
    # 1. Normalización básica
    texto = normalizar_texto(texto)
    # 2. Limpieza Regex
    texto = limpiar_caracteres(texto)
    # 3. Diccionario manual
    texto = corregir_diccionario(texto)
    # 4. Fuzzy matching para nombres de héroes/series
    texto = corregir_fuzzy(texto)
    
    return texto

if __name__ == "__main__":
    # Prueba rápida
    test = "Quien es espiderman y los avenger?"
    print(f"Original: {test}")
    print(f"Procesado: {preprocesar_input(test)}")
