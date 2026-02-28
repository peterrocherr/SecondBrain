import json
import re
from content_extractor import ContentExtractor


class AIProcessor:
    def __init__(self, modelo_llm):
        self.modelo = modelo_llm

    # ------------------------------------------------------------------
    # PASO 1: Resolución lazy (imágenes, webs, YouTube → texto real)
    # ------------------------------------------------------------------
    def _resolver_pendientes(self, lista_inbox: list) -> list:
        """
        Convierte entradas lazy en texto real.
        Solo se ejecuta en /process, nunca en la captura.
        Es idempotente: notas ya resueltas no vuelven a procesarse.
        """
        resueltas = []
        for nota in lista_inbox:
            img_match = re.search(r'\[IMAGE_PENDING\]:\s*(\S+)', nota)
            if img_match:
                url = img_match.group(1).strip()
                print(f"🖼️  Analizando imagen: {url[:60]}...")
                res = ContentExtractor.extraer_imagen(url, self.modelo)
                resueltas.append(res if "⚠️" not in res else f"[IMAGE - sin analizar]: {url}")
                continue

            web_match = re.search(r'\[WEB_PENDING\]:\s*(\S+)', nota)
            if web_match:
                url = web_match.group(1).strip()
                print(f"🌐 Extrayendo web: {url[:60]}...")
                res = ContentExtractor.extraer_web(url)
                resueltas.append(res if "⚠️" not in res else f"[WEB - sin acceder]: {url}")
                continue

            yt_match = re.search(r'\[YT_PENDING\]:\s*(\S+)', nota)
            if yt_match:
                url = yt_match.group(1).strip()
                print(f"▶️  Transcripción YT: {url[:60]}...")
                res = ContentExtractor.extraer_youtube(url)
                resueltas.append(res if "⚠️" not in res else f"[YT - sin transcripción]: {url}")
                continue

            resueltas.append(nota)
        return resueltas

    # ------------------------------------------------------------------
    # PASO 2A: Detección de grupos temáticos (Opción A Kelea)
    # ------------------------------------------------------------------
    def detectar_grupos(self, lista_inbox: list) -> dict:
        """
        Resuelve el inbox y pide a la IA que detecte grupos temáticos.
        Devuelve:
            {
                "notas_resueltas": [...],   # notas ya sin pendientes
                "grupos": [
                    {"titulo": "Python y async", "indices": [0, 2, 4]},
                    {"titulo": "Recetas mediterráneas", "indices": [1, 3]},
                ]
            }
        Si solo hay un grupo, el llamador puede saltar el menú de selección.
        """
        if not lista_inbox:
            return None

        notas_resueltas = self._resolver_pendientes(lista_inbox)

        # Construimos el contexto numerado para que la IA devuelva índices
        contexto = "\n".join([f"[{i}] {n[:400]}" for i, n in enumerate(notas_resueltas)])

        prompt = f"""
        Eres un clasificador de notas personales. Analiza las siguientes notas numeradas
        y agrúpalas por tema o asunto principal.

        REGLAS ESTRICTAS:
        1. Cada nota pertenece a UN solo grupo.
        2. Usa entre 1 y 5 grupos. Si todo trata del mismo tema, devuelve 1 grupo.
        3. Los títulos de grupo deben ser cortos y descriptivos (máx. 5 palabras).
        4. Devuelve SOLO el JSON, sin texto adicional.

        NOTAS:
        {contexto}

        Responde ÚNICAMENTE con este JSON:
        {{
            "grupos": [
                {{"titulo": "Título del grupo", "indices": [0, 2, 4]}},
                {{"titulo": "Otro grupo", "indices": [1, 3]}}
            ]
        }}
        """

        try:
            respuesta = self.modelo.consultar(prompt)
            limpio = respuesta.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', limpio, re.DOTALL)
            if not match:
                return {"notas_resueltas": notas_resueltas, "grupos": [{"titulo": "Todo el inbox", "indices": list(range(len(notas_resueltas)))}]}

            datos = json.loads(match.group(0), strict=False)
            grupos = datos.get("grupos", [])

            # Validación defensiva: si algún índice está fuera de rango, lo descartamos
            n = len(notas_resueltas)
            grupos_limpios = []
            for g in grupos:
                indices_validos = [i for i in g.get("indices", []) if 0 <= i < n]
                if indices_validos:
                    grupos_limpios.append({"titulo": g["titulo"], "indices": indices_validos})

            if not grupos_limpios:
                grupos_limpios = [{"titulo": "Todo el inbox", "indices": list(range(n))}]

            return {"notas_resueltas": notas_resueltas, "grupos": grupos_limpios}

        except Exception as e:
            print(f"Error en detectar_grupos: {e}")
            # Fallback seguro: un único grupo con todo
            return {"notas_resueltas": notas_resueltas, "grupos": [{"titulo": "Todo el inbox", "indices": list(range(len(notas_resueltas)))}]}

    # ------------------------------------------------------------------
    # PASO 2B: Generar propuesta para un subconjunto de notas
    # ------------------------------------------------------------------
    def generar_propuesta(self, notas: list) -> dict:
        """
        Genera una propuesta de topic estructurado para una lista de notas.
        Las notas deben estar ya resueltas (sin pendientes).
        """
        if not notas:
            return None

        # _resolver_pendientes es idempotente: no hace nada si ya están resueltas
        notas = self._resolver_pendientes(notas)
        textos_unidos = "\n--- NUEVA NOTA ---\n".join(notas)

        prompt = f"""
        Eres un organizador de conocimiento personal estricto.
        TU MISIÓN: Crear una propuesta de conocimiento estructurado a partir de estas notas.

        REGLAS:
        1. NO uses información externa ni de conversaciones previas.
        2. Sé fiel al contenido de las notas.
        3. Si hay subtemas dentro del grupo, refléjalos en el resumen con secciones Markdown.

        NOTAS:
        {textos_unidos}

        Responde SOLO con este JSON:
        {{
            "tema": "Título claro y preciso",
            "resumen": "Resumen estructurado en Markdown",
            "fuentes": "lista de tipos: texto, web, imagen, pdf...",
            "fun_fact": "Un dato curioso o conexión interesante"
        }}
        """

        try:
            respuesta = self.modelo.consultar(prompt)
            limpio = respuesta.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', limpio, re.DOTALL)
            if not match:
                return None
            return json.loads(match.group(0), strict=False)
        except Exception as e:
            print(f"Error en generar_propuesta: {e}")
            return None
