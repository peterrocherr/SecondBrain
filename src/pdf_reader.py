import io
import requests
from pypdf import PdfReader

class PDFReader:
    @staticmethod
    def extraer_texto(media_url: str) -> str:
        try:
            # Descargamos el archivo desde los servidores de Twilio
            respuesta = requests.get(media_url, timeout=10)
            respuesta.raise_for_status()
            
            # Lo abrimos directamente en la memoria RAM
            archivo_memoria = io.BytesIO(respuesta.content)
            lector = PdfReader(archivo_memoria)
            texto_pdf = ""
            
            # Leemos un máximo de 5 páginas para no reventar el límite de Gemini
            num_paginas = min(len(lector.pages), 5) 
            for i in range(num_paginas):
                pagina = lector.pages[i].extract_text()
                if pagina:
                    texto_pdf += pagina + "\n"
                    
            return f"\n\n--- Contenido del Documento PDF ---\n{texto_pdf[:6000]}"
            
        except Exception as e:
            print(f"⚠️ Error leyendo PDF: {e}")
            return "\n\n[Nota: No se pudo extraer el texto del PDF adjunto]"