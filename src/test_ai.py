from google import genai

client = genai.Client(api_key="TU_CLAVE_AQUI")

try:
    response = client.models.generate_content(
        model="gemini-1.5-flash", 
        contents="¿Estás ahí? Responde solo con 'SÍ'"
    )
    print(f"Respuesta: {response.text}")
except Exception as e:
    print(f"Error: {e}")