import traceback
from collections import deque
from content_extractor import ContentExtractor
from command_processor import CommandProcessor
from state_processor import StateProcessor

class MessageRouter:
    def __init__(self, saver, streak_manager, quizzer, reminders, textos, motor, inbox, ai, estado, llm=None):
        self.motor = motor
        self.inbox = inbox
        self.textos = textos
        self.estado = estado
        self.commands = CommandProcessor(saver, inbox, ai, quizzer, reminders, motor, estado, textos, streak_manager)
        self.states = StateProcessor(saver, inbox, streak_manager, motor, estado, ai=ai)
        self.valid_commands = ["/process", "/weekly", "/remember", "/remind", "/interval", "/list", "/quiz", "/remove", "/help", "/rectify", "/export"]
        self.processed_sids = deque(maxlen=200)  # FIFO, evicts oldest automatically
        self.llm = llm

    def procesar_mensaje(self, remitente, texto, num_media, media_url, media_type, message_sid):
        # 1. Evitar duplicados por reintentos de Twilio
        if message_sid in self.processed_sids:  # O(n) but fine for 200 items
            return
        self.processed_sids.append(message_sid)

        try:
            texto = (texto or "").strip()
            extra_content = ""
            cantidad_media = int(num_media or 0)

            # 2. Procesar Links en el texto
            if "http" in texto:
                extra_content += self._gestionar_links(remitente, texto)

            # 3. Procesar Adjuntos Directos
            if cantidad_media > 0 and media_url:
                extra_content += self._gestionar_adjuntos(remitente, media_url, media_type)

            texto_final = (texto + extra_content).strip()
            if not texto_final: return

            # 4. Comandos y Estados
            # Primera palabra normalizada: maneja "Yes!", "Sí.", "No gracias" y comandos /cmd
            comando_base = texto_final.split()[0].lower().rstrip(".,!?¿¡") if texto_final else ""

            if self.estado.estados.get(remitente) and self.states.procesar_estado(remitente, comando_base):
                return

            if texto_final.startswith("/"):
                if comando_base in self.valid_commands:
                    self.commands.ejecutar(remitente, comando_base, texto_final)
                return

            # 5. Guardar Nota
            if self.inbox.guardar_nota(texto_final, usuario=remitente):
                count = self.inbox.contar_pendientes(remitente)
                tipo_info = self.inbox.resumen_por_tipo(remitente)
                self.motor.enviar_mensaje(remitente, f"📥 Guardado ({count} pendientes)\n{tipo_info}")

        except Exception as e:
            print(f"❌ Error en Router: {e}\n{traceback.format_exc()}")

    def _gestionar_links(self, remitente, texto):
        u = texto.lower()
        if u.endswith(".pdf"):
            res = ContentExtractor.extraer_pdf(texto)          # PDFs: extracción local rápida, OK síncrono
        elif u.endswith((".mp4", ".mov")):
            res = ContentExtractor.extraer_video(texto)        # Vídeos locales: OK síncrono
        elif "youtube.com" in u or "youtu.be" in u:
            # YouTube: lazy igual que webs, la transcripción puede tardar
            import re as _re
            urls = _re.findall(r'(https?://\S+)', texto)
            res = "\n" + "\n".join([f"[YT_PENDING]: {url}" for url in urls]) if urls else ""
        else:
            # Webs externas: LAZY, se resuelven en /process igual que imágenes
            import re
            urls = re.findall(r'(https?://\S+)', texto)
            res = "\n" + "\n".join([f"[WEB_PENDING]: {url}" for url in urls]) if urls else ""
        return self._limpiar(res, remitente)

    def _gestionar_adjuntos(self, remitente, url, m_type):
        if m_type == "application/pdf": res = ContentExtractor.extraer_pdf(url)
        elif m_type.startswith("audio/"): res = ContentExtractor.transcribir_audio(url)
        elif m_type.startswith("video/"): res = ContentExtractor.extraer_video(url)
        elif m_type.startswith("image/"):
            # CAPTURA SIN FRICCIÓN: guardamos la referencia en el inbox.
            # Gemini la analizará cuando el usuario ejecute /process.
            res = f"\n[IMAGE_PENDING]: {url}"
        else: res = ""
        return self._limpiar(res, remitente)

    def _limpiar(self, res, remitente=None):
        if "⚠️ VIDEO_SIN_AUDIO" in res:
            if remitente:
                self.motor.enviar_mensaje(remitente, "🎬 El vídeo no tiene pista de audio, así que no pude transcribirlo. Si quieres guardarlo, escríbeme un resumen manual.")
            return ""
        return res if "⚠️ ERROR" not in res else ""