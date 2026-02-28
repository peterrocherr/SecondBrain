class CommandProcessor:
    def __init__(self, saver, inbox, ai, quizzer, reminders, motor, estado, textos):
        self.saver = saver
        self.inbox = inbox
        self.ai = ai
        self.quizzer = quizzer
        self.reminders = reminders
        self.motor = motor
        self.estado = estado
        self.textos = textos

    def ejecutar(self, remitente, comando_base, texto_completo):
        if comando_base == "/help":
            msg = "\n".join(self.textos["help"]) if isinstance(self.textos["help"], list) else self.textos["help"]
            self.motor.enviar_mensaje(remitente, msg)

        elif comando_base == "/process":
            all_notes = self.inbox.obtener_todo()
            if not all_notes:
                self.motor.enviar_mensaje(remitente, "📭 Your Inbox is empty.")
                return
            
            self.motor.enviar_mensaje(remitente, f"🧠 Analyzing {len(all_notes)} pending items...")
            propuesta_ia = self.ai.generar_propuesta(all_notes)
            if propuesta_ia:
                self.estado.estados[remitente] = "ESPERANDO_VALIDACION_INBOX"
                self.estado.datos_temporales[remitente] = propuesta_ia
                msg = f"📝 *Proposed Topic: {propuesta_ia.get('tema')}*\n\n{propuesta_ia.get('resumen')}\n\nSave this? (Yes/No)"
                self.motor.enviar_mensaje(remitente, msg)

        elif comando_base == "/rectify":
            rectification = texto_completo[8:].strip()
            if not rectification:
                self.motor.enviar_mensaje(remitente, "⚠️ Use: `/rectify [notes]`")
            else:
                self.inbox.guardar_nota(f"User Correction: {rectification}")
                self.motor.enviar_mensaje(remitente, "🔧 Added to the processing queue.")

        elif comando_base == "/list":
            db_res, _ = self.saver.listar_conocimiento()
            inbox_count = len(self.inbox.obtener_todo())
            header = f"📊 *STATUS*\n- Brain database: {self.saver.contar_topics()} notes\n- Inbox queue: {inbox_count} items\n\n"
            self.motor.enviar_mensaje(remitente, header + db_res)

        elif comando_base == "/weekly":
            self.motor.enviar_mensaje(remitente, self.saver.generar_resumen_semanal())

        elif comando_base == "/remove":
            self.estado.estados[remitente] = "ESPERANDO_BORRADO_DB"
            self.motor.enviar_mensaje(remitente, "⚠️ *ALERT!* Wipe database? (Yes/No)")
            
        elif comando_base == "/quiz":
            # Suponiendo que quizzer devuelve el texto directamente
            self.motor.enviar_mensaje(remitente, self.quizzer.generar_quiz_semanal(remitente, self.textos, self.saver, None))