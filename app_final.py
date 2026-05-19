import json
import requests
from flask import Flask, request, jsonify
from preprocesado import preprocesar_input
from rag_utils import load_index, search

app = Flask(__name__)

# Configuración
LLM_API = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "llama-3.2-3b-instruct"
TOP_K = 3

# Cargamos el índice al iniciar
try:
    index, chunks = load_index()
    print("RAG cargado correctamente.")
except:
    print("ERROR: No se encuentra el índice. Ejecuta build_index.py primero.")
    index, chunks = None, None

def es_respuesta_valida(respuesta, contexto_recuperado):
    """
    Lógica de decisión (decidir cuándo escalar).
    Si no hay contexto o el modelo admite no saber, escalamos.
    """
    resp_lower = respuesta.lower()
    
    # Si no se recuperó contexto relevante (score alto o lista vacía)
    if not contexto_recuperado:
        return False
        
    # Si el modelo detecta que no tiene la info
    frases_fallo = [
        "no tengo información", 
        "no aparece en las definiciones",
        "no puedo responder",
        "no sé",
        "información no disponible",
        "i don't have",
        "no constan en los archivos"
    ]
    
    for frase in frases_fallo:
        if frase in resp_lower:
            return False
            
    #  Validación de longitud mínima para evitar respuestas vacías
    if len(respuesta.strip()) < 10:
        return False
        
    return True

def escalar_a_humano(pregunta_original):
    return {
        "respuesta": "Lo lamento, pero esa información no consta en nuestros archivos de la Liga de la Justicia (2010-2020). Te paso con el Archivista Humano en Jefe para que resuelva tu duda.",
        "escalado": True
    }

@app.route('/chat', methods=['POST'])
def chat():
    # Usamos force=True para que intente leer JSON aunque el Content-Type no sea perfecto
    data = request.get_json(force=True, silent=True)
    
    if data is None:
        print("DEBUG: No se recibio JSON o esta mal formado")
        return jsonify({"error": "Cuerpo de peticion invalido (no es JSON)"}), 400

    pregunta_usuario = data.get("pregunta", "")
    print(f"DEBUG: Pregunta recibida: '{pregunta_usuario}'")
    
    if not pregunta_usuario:
        return jsonify({"error": "No has enviado ninguna pregunta"}), 400

    # PREPROCESADO (Nivel Mínimo e Ideal)
    pregunta_limpia = preprocesar_input(pregunta_usuario)
    print(f"Pregunta original: {pregunta_usuario}")
    print(f"Pregunta procesada: {pregunta_limpia}")

    # ECUPERACIÓN (RAG)
    contexto_docs = search(pregunta_limpia, index, chunks, top_k=TOP_K)
    
    # Filtrar contexto por similitud (si la distancia es muy grande, ignorar)
    # En FAISS L2 menor distancia es mejor. Umbral de ejemplo: 1.5
    contexto_valido = [d for d in contexto_docs if d['score'] < 1.5]
    
    contexto_text = "\n".join([f"- {d['titulo']}: {d['content']}" for d in contexto_valido])

    # GENERACIÓN
    prompt = f"""Eres un Asistente Experto de la Biblioteca de Héroes Occidentales (2010-2020).
Tu misión es informar sobre series animadas basadas SOLO en el contexto proporcionado.

Contexto recuperado:
{contexto_text}

Pregunta del usuario: {pregunta_limpia}

Instrucciones:
- Responde de forma amable y directa.
- Si la información no está en el contexto o el usuario pregunta algo ajeno a series de superhéroes, responde exactamente: "No tengo información sobre esto en mis archivos".
- No inventes series ni detalles.

Respuesta:"""

    try:
        response = requests.post(LLM_API, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.2
        }, timeout=30)
        
        resultado_llm = response.json()['choices'][0]['message']['content']
        
        # LÓGICA DE DECISIÓN (Escalado)
        if es_respuesta_valida(resultado_llm, contexto_valido):
            return jsonify({
                "respuesta": resultado_llm,
                "escalado": False,
                "fuentes": [d['titulo'] for d in contexto_valido],
                "preprocesado": pregunta_limpia
            })
        else:
            return jsonify(escalar_a_humano(pregunta_usuario))

    except Exception as e:
        return jsonify({"error": f"Error conectando con LM Studio: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=5001, debug=True)
