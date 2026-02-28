from google import genai
import os

class LLMManager:
    def __init__(self, api_key: str):
        # DIAGNÓSTICO: Verificamos si la clave llegó vacía
        if not api_key:
            print("❌ ERROR: El LLMManager recibió una clave VACÍA. Revisa tu archivo .env")
            self.client = None
            return

        print(f"Intentando conectar con: {api_key[:5]}...{api_key[-4:]}")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_id = "gemini-1.5-flash"
            print("✅ Cliente de Google GenAI instanciado.")
        except Exception as e:
            print(f"❌ Error al instanciar el cliente: {e}")
            self.client = None

    def consultar(self, prompt: str) -> str:
        if not self.client:
            return "Error: No hay cliente de IA configurado."
            
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            # Si aquí sale el error 400, es que la clave es rechazada por Google
            print(f"❌ Error en la llamada a Google AI: {e}")
            raise e