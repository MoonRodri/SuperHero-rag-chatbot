import requests
import json

URL = "http://127.0.0.1:5001/chat"

print("--- Chatbot de Superhéroes (2010-2020) ---")
print("Escribe 'salir' para terminar.\n")

while True:
    pregunta = input("Pregunta: ")
    if pregunta.lower() == "salir":
        break
    
    try:
        response = requests.post(URL, json={"pregunta": pregunta}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("\nRespuesta:")
            print(data.get("respuesta"))
            
            if data.get("escalado"):
                print("\n[SISTEMA]: El bot ha detectado que no tiene información y ha ESCALADO a un humano.")
            else:
                print(f"\nFuentes: {', '.join(data.get('fuentes', []))}")
                print(f"Input Limpio: {data.get('preprocesado')}")
        else:
            print(f"\nError {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"\nError de conexión: {str(e)}")
    
    print("\n" + "-"*40 + "\n")
