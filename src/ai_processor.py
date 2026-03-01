import json
import re
import time
from content_extractor import ContentExtractor


class AIProcessor:
    def __init__(self, modelo_llm):
        self.modelo = modelo_llm

    # ------------------------------------------------------------------
    # PASO 1: Resolución lazy (siempre 1 llamada por pendiente)
    # ------------------------------------------------------------------
    def _resolver_pendientes(self, lista_inbox: list) -> list:
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
    # PASO 2: Detección de grupos + propuesta en UNA SOLA llamada
    # ------------------------------------------------------------------
    def detectar_grupos(self, lista_inbox: list) -> dict:
        """
        Resuelve pendientes y en UNA llamada al LLM:
        - Si todas las notas tratan del mismo tema → devuelve 1 grupo con propuesta completa
        - Si hay temas distintos → devuelve los grupos para que el usuario elija

        Esto reduce el flujo de 3 llamadas LLM a máximo 2 (resolución + análisis).
        """
        if not lista_inbox:
            return None

        notas_resueltas = self._resolver_pendientes(lista_inbox)
        contexto = "\n".join([f"[{i}] {n[:400]}" for i, n in enumerate(notas_resueltas)])
        n = len(notas_resueltas)

        prompt = f"""
        Eres un organizador de conocimiento personal. Analiza estas notas numeradas.

        TAREA:
        1. Determina si todas las notas tratan del mismo tema o de temas distintos.
        2a. Si es UN SOLO TEMA: devuelve modo "single" con la propuesta completa.
        2b. Si hay TEMAS DISTINTOS (máx. 5 grupos): devuelve modo "multi" con los grupos.

        NOTAS:
        {contexto}

        Responde SOLO con uno de estos dos JSON:

        Modo un tema:
        {{
            "modo": "single",
            "tema": "Título claro",
            "resumen": "Resumen en Markdown",
            "fuentes": "tipos de contenido",
            "fun_fact": "dato curioso"
        }}

        Modo varios temas:
        {{
            "modo": "multi",
            "grupos": [
                {{"titulo": "Nombre del grupo", "indices": [0, 2]}},
                {{"titulo": "Otro grupo", "indices": [1]}}
            ]
        }}
        """

        try:
            respuesta = self.modelo.consultar(prompt)
            limpio = respuesta.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', limpio, re.DOTALL)
            if not match:
                raise ValueError("Sin JSON en respuesta")

            datos = json.loads(match.group(0), strict=False)
            modo = datos.get("modo")

            if modo == "single":
                # Ya tenemos la propuesta, no hace falta otra llamada
                propuesta = {k: datos[k] for k in ["tema", "resumen", "fuentes", "fun_fact"] if k in datos}
                if isinstance(propuesta.get("fuentes"), list):
                    propuesta["fuentes"] = ", ".join(propuesta["fuentes"])
                return {
                    "notas_resueltas": notas_resueltas,
                    "grupos": [{"titulo": datos.get("tema", "Todo el inbox"), "indices": list(range(n))}],
                    "propuesta_directa": propuesta  # Ahorramos la 3ª llamada
                }

            elif modo == "multi":
                grupos = datos.get("grupos", [])
                grupos_limpios = []
                for g in grupos:
                    indices_validos = [i for i in g.get("indices", []) if 0 <= i < n]
                    if indices_validos:
                        grupos_limpios.append({"titulo": g["titulo"], "indices": indices_validos})

                if not grupos_limpios:
                    raise ValueError("Grupos vacíos")

                return {"notas_resueltas": notas_resueltas, "grupos": grupos_limpios}

        except Exception as e:
            print(f"Error en detectar_grupos: {e}")

        # Fallback: un grupo, sin propuesta directa
        return {
            "notas_resueltas": notas_resueltas,
            "grupos": [{"titulo": "Todo el inbox", "indices": list(range(n))}]
        }

    # ------------------------------------------------------------------
    # PASO 3: Generar propuesta para un subconjunto (solo si modo multi)
    # ------------------------------------------------------------------
    def generar_propuesta(self, notas: list) -> dict:
        """
        Solo se llama cuando el usuario elige un grupo en modo multi.
        En modo single, la propuesta ya viene incluida en detectar_grupos.
        """
        if not notas:
            return None

        notas = self._resolver_pendientes(notas)
        textos_unidos = "\n--- NUEVA NOTA ---\n".join(notas)

        prompt = f"""
        Eres un organizador de conocimiento personal estricto.
        Crea una propuesta estructurada a partir de estas notas.

        REGLAS:
        1. NO uses información externa.
        2. Sé fiel al contenido de las notas.
        3. Si hay subtemas, refléjalos con secciones Markdown.

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
            datos = json.loads(match.group(0), strict=False)
            # Normalizar fuentes a string siempre
            if isinstance(datos.get("fuentes"), list):
                datos["fuentes"] = ", ".join(datos["fuentes"])
            return datos
        except Exception as e:
            print(f"Error en generar_propuesta: {e}")
            return None
