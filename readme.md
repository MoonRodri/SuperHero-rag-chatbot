# Proyecto Final

Chatbot experto en series animadas de superhéroes (2010-2020) con preprocesado y escalado.

## Archivos
- `app/`: Arquitectura modular (Configuración y Servicio LLM).
- `json/`: Archivos de datos (marvel_2010s.json, dc_2010s.json e indie_2010s.json).
- `preprocesado.py`: Pipeline de limpieza (Regex, Diccionario y RapidFuzz).
- `rag_utils.py`: Genera el índice FAISS y gestiona la búsqueda.
- `agente_superheroes_app.py`: Servidor Web con arquitectura de agentes (Recomendado).
- `app_final.py`: Servidor clásico de consola (Legacy).
- `cliente.py`: Cliente de consola.
- `templates/` y `static/`: Interfaz web del terminal de S.H.I.E.L.D.

## Ejecución
1. Iniciar LM Studio (Server en puerto 1234 con modelo Llama 3.2 3B).
2. Activar venv:
```powershell
.\venv\Scripts\activate
```
3. Crear el índice:
```powershell
python rag_utils.py
```
4. Lanzar el servidor web:
```powershell
python agente_superheroes_app.py
```
Luego ir a `http://127.0.0.1:5050` en el navegador.

