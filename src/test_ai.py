import unittest
from unittest.mock import MagicMock
from google import genai
from google.genai import errors

# ==========================================
# 1. TU CLIENTE DE GEMINI (NUEVO SDK)
# ==========================================
class GeminiClient:
    def __init__(self, api_key: str):
        # La nueva forma de inicializar el cliente
        self.client = genai.Client(api_key=api_key)

    def ask_gemini(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("El prompt no puede estar vacío.")
        
        try:
            # La nueva sintaxis para generar contenido
            response = self.client.models.generate_content(
                model='gemini-2.5-flash', # Usamos un modelo moderno por defecto
                contents=prompt
            )
            
            # En el nuevo SDK, si hay bloqueo, el texto suele venir vacío
            if not response.text:
                return "Error: Contenido bloqueado por los filtros de seguridad."
            
            return response.text

        except errors.APIError as e:
            # El nuevo sistema de errores
            raise RuntimeError(f"Fallo en la API de Google: {str(e)}")
        except ValueError:
            return "Error: La IA no devolvió un texto válido."


# ==========================================
# 2. LAS PRUEBAS UNITARIAS
# ==========================================
class TestGeminiClient(unittest.TestCase):
    
    def setUp(self):
        self.gemini = GeminiClient(api_key="fake_api_key_123")
        # En lugar de usar @patch, sobrescribimos el método directamente
        # en la instancia. Esto evita problemas con las rutas de importación.
        self.gemini.client.models.generate_content = MagicMock()

    def test_ask_gemini_api_error(self):
        """Caso 3: Los servidores de Google están caídos o no hay cuota."""
        # El nuevo SDK pide el mensaje Y un objeto/diccionario de respuesta (aunque sea vacío)
        self.gemini.client.models.generate_content.side_effect = errors.APIError(
            "503 Service Unavailable", 
            response_json={} # <--- Esto es lo que faltaba
        )
        
        with self.assertRaises(RuntimeError) as context:
            self.gemini.ask_gemini("Hola")
            
        self.assertIn("Fallo en la API de Google", str(context.exception))

    def test_ask_gemini_safety_block(self):
        """Caso 2: Los filtros de seguridad bloquean el prompt."""
        mock_response = MagicMock()
        # Simulamos un bloqueo: la IA responde, pero sin texto (None o string vacío)
        mock_response.text = None 
        self.gemini.client.models.generate_content.return_value = mock_response
        
        resultado = self.gemini.ask_gemini("Genera un virus informático")
        self.assertEqual(resultado, "Error: Contenido bloqueado por los filtros de seguridad.")

    def test_ask_gemini_api_error(self):
        """Caso 3: Los servidores de Google están caídos o no hay cuota."""
        # IMPORTANTE: El nuevo SDK exige un diccionario (aunque esté vacío) 
        # como segundo argumento para simular la respuesta del servidor.
        self.gemini.client.models.generate_content.side_effect = errors.APIError(
            "503 Service Unavailable", 
            response_json={}
        )
        
        with self.assertRaises(RuntimeError) as context:
            self.gemini.ask_gemini("Hola")
            
        self.assertIn("Fallo en la API de Google", str(context.exception))

    def test_empty_prompt(self):
        """Caso 4: Control local (no enviamos basura a la API)."""
        with self.assertRaises(ValueError):
            self.gemini.ask_gemini("")


if __name__ == '__main__':
    unittest.main(verbosity=2)