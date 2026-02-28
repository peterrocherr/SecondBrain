import traceback
from content_extractor import ContentExtractor
from command_processor import CommandProcessor
from state_processor import StateProcessor

class MessageRouter:
    def __init__(self, saver, streak_manager, quizzer, reminders, textos, motor, inbox, ai, estado):
        self.motor = motor
        self.inbox = inbox
        self.textos = textos
        self.estado = estado
        self.commands = CommandProcessor(saver, inbox, ai, quizzer, reminders, motor, estado, textos, streak_manager)
        self.states = StateProcessor(saver, inbox, streak_manager, motor, estado)
        self.valid_commands = ["/process", "/weekly", "/remember", "/remind", "/interval", "/list", "/quiz", "/remove", "/help", "/rectify"]
        self.processed_sids = set()

    def procesar_mensaje(self, remitente, texto, num_media, media_url, media_type, message_sid):
        # 1. Evitar duplicados por reintentos de Twilio
        if message_sid in self.processed_sids:
            return
        self.processed_sids.add(message_sid)
        if len(self.processed_sids) > 100: self.processed_sids.pop()

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
            # Extraemos solo la primera palabra para normalizar respuestas como "Yes!", "Sí.", "No gracias"
            primera_palabra = texto_final.split()[0].lower().rstrip(".,!?¿¡") if texto_final else ""
            comando_base = primera_palabra if texto_final.startswith("/") else primera_palabra

            if self.estado.estados.get(remitente) and self.states.procesar_estado(remitente, comando_base):
                return

            if texto_final.startswith("/"):
                if comando_base in self.valid_commands:
                    self.commands.ejecutar(remitente, comando_base, texto_final)
                return

            # 5. Guardar Nota
            if self.inbox.guardar_nota(texto_final):
                count = len(self.inbox.obtener_todo())
                self.motor.enviar_mensaje(remitente, f"📥 Guardado ({count} pendientes).")

        except Exception as e:
            print(f"❌ Error en Router: {e}\n{traceback.format_exc()}")

    def _gestionar_links(self, remitente, texto):
        u = texto.lower()
        if u.endswith(".pdf"): res = ContentExtractor.extraer_pdf(texto)
        elif u.endswith((".mp4", ".mov")): res = ContentExtractor.extraer_video(texto)
        elif "youtube.com" in u or "youtu.be" in u: res = ContentExtractor.extraer_youtube(texto)
        else: res = ContentExtractor.extraer_web(texto)
        return self._limpiar(res, remitente)

    def _gestionar_adjuntos(self, remitente, url, m_type):
        if m_type == "application/pdf": res = ContentExtractor.extraer_pdf(url)
        elif m_type.startswith("audio/"): res = ContentExtractor.transcribir_audio(url)
        elif m_type.startswith("video/"): res = ContentExtractor.extraer_video(url)
        else: res = ""
        return self._limpiar(res, remitente)

    def _limpiar(self, res, remitente=None):
        if "⚠️ VIDEO_SIN_AUDIO" in res:
            if remitente:
                self.motor.enviar_mensaje(remitente, "🎬 El vídeo no tiene pista de audio, así que no pude transcribirlo. Si quieres guardarlo, escríbeme un resumen manual.")
            return ""
        return res if "⚠️ ERROR" not in res else ""