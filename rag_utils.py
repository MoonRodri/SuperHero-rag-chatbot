import json
import os
import faiss # Facebook AI Similarity Search: Encontrar informacion relevante en segundos
import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_DIR = "index"
INDEX_FILE = os.path.join(INDEX_DIR, "faiss.index")
CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.json")
# Modelo para convertir texto en vectores
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

embedding_model = SentenceTransformer(MODEL_NAME)

def load_data(json_dir="json"):
    all_docs = []
    if not os.path.exists(json_dir):
        print(f"Error: No existe el directorio {json_dir}")
        return []

    json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
    print(f"Archivos encontrados: {json_files}")

    for file in json_files:
        path = os.path.join(json_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Cargando {len(data)} definiciones de {file}...")
            for item in data:
                text_to_embed = f"{item['titulo']} ({item['año']}) | Universo: {item['universo']} | {item['descripcion']}"
                all_docs.append({
                    "titulo": item['titulo'],
                    "content": item['descripcion'],
                    "embedding_text": text_to_embed,
                    "metadata": item,
                    "source_file": file
                })
    return all_docs

def build_index():
    print("--- Iniciando construcción del índice ---")
    docs = load_data()
    if not docs:
        print("No hay datos para indexar.")
        return

    texts = [d["embedding_text"] for d in docs]
    
    print(f"Generando embeddings para un total de {len(texts)} series...")
    embeddings = embedding_model.encode(texts, convert_to_numpy=True)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    if not os.path.exists(INDEX_DIR):
        os.makedirs(INDEX_DIR)
        
    faiss.write_index(index, INDEX_FILE)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    
    print(f"Índice creado correctamente con {len(docs)} vectores.")

def load_index():
    index = faiss.read_index(INDEX_FILE)
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    return index, chunks

def search(query, index, chunks, top_k=3):
    query_vector = embedding_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vector, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(chunks):
            res = chunks[idx]
            res["score"] = float(distances[0][i])
            results.append(res)
    return results

if __name__ == "__main__":
    build_index()
