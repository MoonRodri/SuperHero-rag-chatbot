from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass
from typing import Any

from flask import Flask, jsonify, render_template, request

from app.config import Config
from app.llm.llm_service import LLMConfig, LLMService
from preprocesado import preprocesar_input
from rag_utils import load_index, search

# =========================================================
# LÓGICA DE AGENTES: Orquestrador de agente, son 2
# =========================================================

class SuperheroRuleAgent:
    """Agente que responde basado en reglas fijas (Python) sin usar el LLM."""
    def __init__(self, chunks):
        self.chunks = chunks

    def run(self, message: str) -> dict[str, Any] | None:
        msg = message.upper().strip()
        
        # Regla: Listar por Universo
        if "LISTA" in msg or "LISTAR" in msg:
            target = "MARVEL" if "MARVEL" in msg else "DC" if "DC" in msg else "INDEPENDIENTE" if "INDIE" in msg else None
            if target:
                series = [c['titulo'] for c in self.chunks if c['metadata']['universo'].upper() == target]
                return {
                    "reply": f"He encontrado {len(series)} series de {target} en la base de datos:\n" + ", ".join(series),
                    "info": f"Comando LISTA detectado para {target}."
                }
        
        # Regla: Contar
        if "CUANTA" in msg or "CONTAR" in msg or "TOTAL" in msg:
            return {
                "reply": f"Actualmente tengo acceso a {len(self.chunks)} series animadas en mis archivos.",
                "info": "Comando de conteo detectado."
            }

        return None

class SuperheroRAGAgent:
    """Agente que usa el pipeline RAG (Preprocesado + FAISS + LLM)."""
    def __init__(self, index, chunks, llm_service: LLMService):
        self.index = index
        self.chunks = chunks
        self.llm_service = llm_service

    def run(self, message: str) -> dict[str, Any]:
        # 1. PREPROCESADO
        msg_limpio = preprocesar_input(message)
        
        # 2. RAG (FAISS)
        docs = search(msg_limpio, self.index, self.chunks, top_k=3)
        
        # DEBUG: Ver puntuaciones en consola
        print(f"\n--- BÚSQUEDA RAG ---")
        print(f"Query limpia: '{msg_limpio}'")
        for d in docs:
            print(f"- {d['titulo']}: Score {d['score']:.4f}")

        # Umbral equilibrado a 1.3
        contexto_valido = [d for d in docs if d['score'] < 1.3]
        contexto_text = "\n".join([f"- {d['titulo']}: {d['content']}" for d in contexto_valido])
        
        if not contexto_valido:
            return self._msg_escalado(f"Similitud insuficiente (Score > 1.3)")

        # 3. GENERACIÓN (LLM)
        prompt = f"""Eres el Archivista jefe de S.H.I.E.L.D.
Tu misión es informar de forma precisa sobre series de superhéroes (2010-2020).

CONTEXTO DE ARCHIVOS:
{contexto_text}

PREGUNTA DEL AGENTE: {msg_limpio}

REGLAS DE ACTUACIÓN:
1. Responde basándote ÚNICAMENTE en el contexto de arriba.
2. Si te preguntan por nombres reales o identidades, busca nombres asociados a los títulos en el texto.
3. Sé directo: No analices, no digas "según el contexto". Responde como un humano experto.
4. Si la respuesta NO está en el contexto o es sobre un tema ajeno, responde: DOMINIO_DESCONOCIDO.
"""
        respuesta = self.llm_service.ask(prompt)
        
        # 4. LÓGICA DE ESCALADO DINÁMICA
        # Extraemos palabras con mayúscula (nombres propios potenciales) que no estén al inicio
        entidades_pregunta = re.findall(r'(?<!^)(?<!\. )[A-Z][a-z]+', message)
        
        for ent in entidades_pregunta:
            if len(ent) > 3 and ent.lower() not in contexto_text.lower():
                # Si el preprocesado lo cambió, no escalamos
                if ent.lower() not in msg_limpio.lower():
                    return self._msg_escalado(f"Nombre '{ent}' fuera de base de datos.")

        if "dominio_desconocido" in respuesta.lower() or len(respuesta.strip()) < 5:
            return self._msg_escalado("Información no localizada en los archivos clasificados.")
            
        return {
            "reply": respuesta,
            "sources": [d['titulo'] for d in contexto_valido],
            "preprocesado": msg_limpio,
            "info": "Consulta procesada exitosamente."
        }

    def _msg_escalado(self, motivo):
        return {
            "reply": "Lo lamento, pero esa información no consta en los Archivos Clasificados de S.H.I.E.L.D. (2010-2020). Te paso con el Archivista Humano en Jefe para que resuelva tu duda.",
            "escalado": True,
            "info": f"Escalado activado: {motivo}"
        }

# =========================================================
# APLICACIÓN FLASK
# =========================================================

def create_app():
    app = Flask(__name__)
    
    # Cargar base de datos RAG
    idx, chks = load_index()
    
    # Configurar Servicio LLM (lee del .env)
    llm_config = LLMConfig(
        provider=Config.LLM_PROVIDER,
        base_url=Config.LLM_BASE_URL,
        api_key=Config.LLM_API_KEY,
        model=Config.LLM_MODEL,
        timeout=Config.LLM_TIMEOUT,
        max_tokens=Config.LLM_MAX_TOKENS
    )
    llm_service = LLMService(llm_config)
    
    # Instanciar Agentes
    rule_agent = SuperheroRuleAgent(chks)
    rag_agent = SuperheroRAGAgent(idx, chks, llm_service)

    @app.get("/")
    def index():
        return render_template("index.html", model_name=Config.LLM_MODEL)

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "").strip()

        if not message:
            return jsonify({"reply": "Por favor, escribe algo, soldado."}), 400

        # Paso 1: Intentar Agente de Reglas
        rule_result = rule_agent.run(message)
        if rule_result:
            return jsonify({
                "agent": "rules",
                "reply": rule_result["reply"],
                "rule_info": rule_result["info"],
                "rag_info": "No fue necesario activar la IA."
            })

        # Paso 2: Activar Agente RAG
        rag_result = rag_agent.run(message)
        return jsonify({
            "agent": "rag",
            "reply": rag_result["reply"],
            "rule_info": "Reglas no aplicables a esta consulta.",
            "rag_info": rag_result["info"],
            "sources": rag_result.get("sources", []),
            "preprocesado": rag_result.get("preprocesado")
        })

    return app

if __name__ == "__main__":
    print("S.H.I.E.L.D. Web Terminal iniciando en puerto 5050...")
    app = create_app()
    app.run(port=5050, debug=True)
