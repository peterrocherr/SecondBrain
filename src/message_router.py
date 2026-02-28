import traceback  # <-- NUEVO: Para imprimir la línea exacta del error en tu consola
from content_extractor import ContentExtractor
from command_processor import CommandProcessor
from state_processor import StateProcessor

class MessageRouter:
    def __init__(self, saver, streak_manager, quizzer, reminders, textos, motor, inbox, ai, estado):
        self.motor = motor
        self.inbox = inbox
        self.textos = textos
        self.estado = estado
        self.commands = CommandProcessor(saver, inbox, ai, quizzer, reminders, motor, estado, textos)
        self.states = StateProcessor(saver, inbox, streak_manager, motor, estado)
        self.valid_commands = ["/process", "/weekly", "/remember", "/remind", "/interval", "/list", "/quiz", "/remove", "/help", "/rectify"]

    def procesar_mensaje(self, remitente, texto, num_media, media_url, media_type):
        try:
            texto = texto.strip() if texto else ""
            extra_content = ""
            
            # Protección extra por si Twilio manda num_media vacío o nulo
            try:
                cantidad_media = int(num_media) if num_media else 0
            except ValueError:
                cantidad_media = 0

            # 1. CASO LINKS EN EL TEXTO
            if "http" in texto:
                url_lower = texto.lower()
                if url_lower.endswith(".pdf"):
                    self.motor.enviar_mensaje(remitente, "📄 Analizando PDF desde link...")
                    res = ContentExtractor.extraer_pdf(texto)
                elif url_lower.endswith((".mp4", ".mov", ".avi")):
                    self.motor.enviar_mensaje(remitente, "🎥 Procesando vídeo desde link...")
                    res = ContentExtractor.extraer_video(texto)
                elif url_lower.endswith((".mp3", ".ogg", ".wav", ".m4a")):
                    self.motor.enviar_mensaje(remitente, "🎤 Escuchando audio desde link...")
                    res = ContentExtractor.transcribir_audio(texto)
                elif "youtube.com" in texto or "youtu.be" in texto:
                    self.motor.enviar_mensaje(remitente, "🎥 Analizando YouTube...")
                    res = ContentExtractor.extraer_youtube(texto)
                else:
                    self.motor.enviar_mensaje(remitente, "🌐 Analizando Web...")
                    res = ContentExtractor.extraer_web(texto)
                
                # --- NUEVO CONTROL DE ERRORES SILENCIOSO ---
                if "⚠️ ERROR" in res:
                    print(f"\n❌ [LOG INTERNO - ERROR DE LINK]: {res}")
                    self.motor.enviar_mensaje(remitente, "⚠️ Ha ocurrido un error inesperado al intentar leer el enlace. Prueba con otro formato.")
                else:
                    extra_content += res

            # 2. CASO ADJUNTOS MULTIMEDIA (Audios, Vídeos, PDFs directos)
            if cantidad_media > 0 and media_url and media_type:
                res = ""
                if media_type == "application/pdf":
                    self.motor.enviar_mensaje(remitente, "📄 Analizando PDF adjunto...")
                    res = ContentExtractor.extraer_pdf(media_url)
                elif media_type.startswith("audio/"):
                    self.motor.enviar_mensaje(remitente, "🎤 Escuchando nota de voz...")
                    res = ContentExtractor.transcribir_audio(media_url)
                elif media_type.startswith("video/"):
                    self.motor.enviar_mensaje(remitente, "🎥 Procesando vídeo adjunto...")
                    res = ContentExtractor.extraer_video(media_url)

                # --- NUEVO CONTROL DE ERRORES SILENCIOSO ---
                if "⚠️ ERROR" in res:
                    print(f"\n❌ [LOG INTERNO - ERROR MULTIMEDIA]: {res}")
                    self.motor.enviar_mensaje(remitente, "⚠️ Ha ocurrido un error inesperado al procesar tu archivo. Asegúrate de que no esté corrupto.")
                else:
                    extra_content += res

            texto_final = (texto + extra_content).strip()
            if not texto_final: return

            # --- PROTECCIÓN ANTI INDEX-ERROR AL PARTIR COMANDOS ---
            partes_texto = texto_final.split()
            if len(partes_texto) > 0:
                comando_base = partes_texto[0].lower() if texto_final.startswith("/") else texto_final.lower()
            else:
                comando_base = texto_final.lower()

            # 3. PROCESAR ESTADOS Y COMANDOS
            if self.estado.estados.get(remitente) and self.states.procesar_estado(remitente, comando_base):
                return

            if texto_final.startswith("/"):
                if comando_base in self.valid_commands:
                    self.commands.ejecutar(remitente, comando_base, texto_final)
                else:
                    self.motor.enviar_mensaje(remitente, f"🚫 Comando no reconocido. Escribe /help para ver las opciones.")
                return

            # 4. GUARDAR EN INBOX
            if self.inbox.guardar_nota(texto_final):
                count = len(self.inbox.obtener_todo())
                self.motor.enviar_mensaje(remitente, f"📥 Guardado en Inbox ({count} pendientes). Usa */process*.")

        # --- CAPTURA DE ERRORES FATALES ---
        except IndexError as e:
            print(f"\n🔥 [CRASH - IndexError Detectado]: Intentaste acceder a una posición de la lista que no existe.")
            print(traceback.format_exc())
            self.motor.enviar_mensaje(remitente, "⚠️ Ups, error de formato. Revisa cómo has escrito el comando.")
            
        except Exception as e:
            print(f"\n🔥 [CRASH - Error Crítico Inesperado]: {e}")
            print(traceback.format_exc()) # Imprime la línea exacta del fallo en tu consola
            self.motor.enviar_mensaje(remitente, "⚠️ Error inesperado en los servidores del Cerebro Digital. Avisando a los técnicos.")