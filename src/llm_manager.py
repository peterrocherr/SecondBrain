import google.generativeai as genai

class LLMManager:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("LLMManager: Conectado a Gemini.")

    def consultar(self, prompt: str) -> str:
        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            print(f"❌ Error en LLM: {e}")
            raise e