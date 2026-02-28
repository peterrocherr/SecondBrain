import json
import re

class AIProcessor:
    def __init__(self, modelo_llm):
        self.modelo = modelo_llm 

    def generar_propuesta(self, lista_inbox: list) -> dict:
        if not lista_inbox:
            return None

        # Unimos las notas asegurando que no haya basura
        textos_unidos = "\n--- NUEVA NOTA ---\n".join(lista_inbox)
        
        # PROMPT BLINDADO: Obligamos a la IA a ser fiel al texto
        prompt = f"""
        Eres un organizador de información estricto. 
        TU MISIÓN: Analizar ÚNICAMENTE las notas que te proporciono a continuación.
        
        REGLAS CRÍTICAS:
        1. NO uses información de conversaciones previas.
        2. NO asumas por nombres de canales de YouTube si no aparecen en el texto.
        3. Si las notas hablan de un tema, el resumen DEBE ser del tema.
        
        NOTAS A PROCESAR:
        {textos_unidos}

        Responde exclusivamente con un JSON estricto:
        {{
            "tema": "Título preciso del contenido",
            "resumen": "Resumen fiel a las notas en Markdown",
            "fuentes": "etiquetas",
            "fun_fact": "Un dato curioso extraído o relacionado con este tema específico"
        }}
        """

        try:
            # Aquí llamamos a tu LLMManager
            respuesta_cruda = self.modelo.consultar(prompt)
            
            # Limpieza de la respuesta para evitar el error de JSON
            limpio = respuesta_cruda.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', limpio, re.DOTALL)
            
            if not match: return None
            
            # Usamos strict=False para evitar el error de los escapes "\" que te dio antes
            datos = json.loads(match.group(0), strict=False)
            return datos
            
        except Exception as e:
            print(f"Error en AIProcessor: {e}")
            return None