import re
import requests
from bs4 import BeautifulSoup

class WebReader:
    @staticmethod
    def extraer_texto(texto_crudo: str) -> str:
        urls = re.findall(r'(https?://[^\s]+)', texto_crudo)
        contenido_web = ""
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                res = requests.get(url, headers=headers, timeout=5)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'html.parser')
                texto_pagina = " ".join([p.get_text() for p in soup.find_all('p')])
                contenido_web += f"\n\n--- Extraído de {url} ---\n{texto_pagina[:3000]}"
            except Exception as e:
                print(f"⚠️ Aviso: No se pudo leer la URL {url}. Razón: {e}")
                contenido_web += f"\n\n[Nota: No pude acceder al contenido de {url} porque está protegida o caída]"
        return texto_crudo + contenido_web