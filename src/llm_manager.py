import google.generativeai as genai
import time
import re

class LLMManager:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # DEFINIMOS AQUÍ MODELO
        self.model = genai.GenerativeModel("gemini-3-flash-preview")
        print("LLMManager: Conectado a LLM.")

    def consultar(self, prompt: str, intentos=3) -> str:
        for i in range(intentos):
            try:
                return self.model.generate_content(prompt).text
            except Exception as e:
                error_msg = str(e)
                # Si es un error de cuota (429), extraemos el tiempo de espera
                if "429" in error_msg or "quota" in error_msg.lower():
                    # Intentamos buscar cuántos segundos dice Google que esperemos
                    segundos = re.search(r'(\d+\.?\d*)s', error_msg)
                    tiempo_espera = float(segundos.group(1)) + 1 if segundos else 10
                    
                    print(f"⏳ Límite alcanzado. Reintentando en {tiempo_espera}s... (Intento {i+1}/{intentos})")
                    time.sleep(tiempo_espera)
                else:
                    print(f"❌ Error crítico en LLM: {e}")
                    break
        
        return "ERROR_LIMIT"