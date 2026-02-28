import google.generativeai as genai
import time
import re
import io

class LLMManager:
    def __init__(self, api_key: str, modelo: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(modelo)
        print(f"LLMManager: Conectado a {modelo}.")

    def _con_reintentos(self, fn, intentos=3):
        """Wrapper genérico de reintentos con backoff para cuota 429."""
        for i in range(intentos):
            try:
                return fn()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    segundos = re.search(r'(\d+\.?\d*)s', error_msg)
                    espera = float(segundos.group(1)) + 1 if segundos else 10
                    print(f"⏳ Límite alcanzado. Reintentando en {espera:.1f}s... ({i+1}/{intentos})")
                    time.sleep(espera)
                else:
                    print(f"❌ Error crítico en LLM: {e}")
                    break
        return "ERROR_LIMIT"

    def consultar(self, prompt: str, intentos=3) -> str:
        return self._con_reintentos(
            lambda: self.model.generate_content(prompt).text,
            intentos
        )

    def analizar_imagen(self, datos_imagen: bytes, prompt: str, intentos=3) -> str:
        """Envía imagen + prompt al modelo multimodal de Gemini."""
        import PIL.Image
        imagen_pil = PIL.Image.open(io.BytesIO(datos_imagen))
        return self._con_reintentos(
            lambda: self.model.generate_content([prompt, imagen_pil]).text,
            intentos
        )
