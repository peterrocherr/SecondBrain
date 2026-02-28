from pdf_reader import PDFReader

class MessageRouter:
    def __init__(self, saver, streak_manager, quizzer, reminders, textos, motor):
        self.saver = saver
        self.streak_manager = streak_manager
        self.quizzer = quizzer
        self.reminders = reminders
        self.textos = textos
        self.motor = motor

    def procesar_mensaje(self, remitente, texto, num_media, media_url, media_type):
        try:
            texto = texto.strip() if texto else ""
            respuesta = ""

            if int(num_media) > 0 and media_url:
                if media_type == "application/pdf":
                    self.motor.enviar_mensaje(remitente, "📄 He recibido tu PDF. Lo estoy leyendo, dame unos segundos...")
                    texto_extraido = PDFReader.extraer_texto(media_url)
                    texto = f"{texto} {texto_extraido}".strip()
                else:
                    self.motor.enviar_mensaje(remitente, "⚠️ Solo admito PDFs por ahora.")
                    return 

            if not texto:
                return 

            comando = texto.lower()

            if comando == "/quiz":
                respuesta = self.quizzer.generar_quiz_semanal(remitente, self.textos, self.saver, self.streak_manager)
            elif len(comando) == 5 and all(l in "abc" for l in comando):
                respuesta = self.quizzer.evaluar_respuesta(remitente, texto, self.streak_manager, self.textos)
            elif comando.startswith("/intervalo "):
                respuesta = self.reminders.procesar_intervalo(remitente, texto, self.streak_manager, self.textos)
            elif comando.startswith("/remember "):
                query = texto.replace("/remember ", "").strip()
                respuesta = self.saver.recordar_topic(query)
            elif comando.startswith("/remind "):
                respuesta = self.reminders.procesar_remind(remitente, texto, self.textos)
            elif comando == "/resumen_semanal":
                self.motor.enviar_mensaje(remitente, "📝 Revisando tus apuntes de los últimos 7 días... Dame un momento.")
                respuesta = self.saver.generar_resumen_semanal()
            else:
                respuesta = self._procesar_conocimiento(remitente, texto)

            if respuesta:
                self.motor.enviar_mensaje(remitente, respuesta)

        except Exception as e:
            print(f"\nERROR FATAL PROCESANDO MENSAJE DE {remitente}:\n{str(e)}\n{'-'*50}\n")
            self.motor.enviar_mensaje(remitente, self.textos.get("error_critico", "🚨 Error interno en el servidor."))

    def _procesar_conocimiento(self, remitente, texto):
        tema = self.saver.procesar_y_guardar(texto)
        if tema:
            self.streak_manager.registrar_topic(remitente)
            return self.textos["captura_exito"].format(tema=tema, total=self.saver.contar_topics())
        return self.textos["captura_error"]