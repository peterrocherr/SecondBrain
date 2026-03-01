class CommandProcessor:
    def __init__(self, saver, inbox, ai, quizzer, reminders, motor, estado, textos, streak_manager=None):
        self.saver = saver
        self.inbox = inbox
        self.ai = ai
        self.quizzer = quizzer
        self.reminders = reminders
        self.motor = motor
        self.estado = estado
        self.textos = textos
        self.streak_manager = streak_manager

    def ejecutar(self, remitente, comando_base, texto_completo):

        if comando_base == "/help":
            msg = "\n".join(self.textos["help"]) if isinstance(self.textos["help"], list) else self.textos["help"]
            self.motor.enviar_mensaje(remitente, msg)

        elif comando_base == "/process":
            all_notes = self.inbox.obtener_todo(usuario=remitente)
            if not all_notes:
                self.motor.enviar_mensaje(remitente, "📭 Tu inbox está vacío.")
                return

            self.motor.enviar_mensaje(remitente, f"🔍 Analizando {len(all_notes)} elementos y detectando temas...")

            resultado = self.ai.detectar_grupos(all_notes)
            if not resultado:
                self.motor.enviar_mensaje(
                    remitente,
                    "❌ No pude analizar el inbox. Usa /rectify para añadir contexto e inténtalo de nuevo."
                )
                return

            grupos = resultado["grupos"]

            if len(grupos) == 1:
                # Un solo tema: usar propuesta_directa si ya viene incluida (ahorra 1 llamada LLM)
                propuesta = resultado.get("propuesta_directa")
                if not propuesta:
                    notas = [resultado["notas_resueltas"][i] for i in grupos[0]["indices"]]
                    self.motor.enviar_mensaje(remitente, f"🧠 Generando propuesta para *{grupos[0]['titulo']}*...")
                    propuesta = self.ai.generar_propuesta(notas)
                if propuesta:
                    self.estado.set_estado_validacion(remitente, propuesta)
                    msg = (
                        f"📝 *Proposed Topic: {propuesta.get('tema')}*\n\n"
                        f"{propuesta.get('resumen')}\n\n"
                        f"Save this? (Yes/No)"
                    )
                    self.motor.enviar_mensaje(remitente, msg)
                else:
                    self.motor.enviar_mensaje(
                        remitente,
                        "❌ No pude generar una propuesta. Usa /rectify para añadir más contexto e inténtalo de nuevo."
                    )
            else:
                # Varios temas: mostrar menú de selección
                self.estado.set_estado_seleccion_grupo(remitente, resultado)
                menu = self._formatear_menu_grupos(grupos)
                self.motor.enviar_mensaje(remitente, menu)

        elif comando_base == "/rectify":
            rectification = texto_completo[8:].strip()
            if not rectification:
                self.motor.enviar_mensaje(remitente, "⚠️ Uso: `/rectify [texto]`")
            else:
                self.inbox.guardar_nota(f"User Correction: {rectification}", usuario=remitente)
                self.motor.enviar_mensaje(remitente, "🔧 Añadido a la cola de procesamiento.")

        elif comando_base == "/list":
            db_res, _ = self.saver.listar_conocimiento()
            inbox_breakdown = self.inbox.resumen_por_tipo(remitente)
            inbox_count = self.inbox.contar_pendientes(remitente)
            header = (
                f"📊 *STATUS*\n"
                f"- Base de conocimiento: {self.saver.contar_topics()} notas\n"
                f"- Inbox pendiente: {inbox_count} elementos\n"
                f"{inbox_breakdown}\n\n"
            )
            self.motor.enviar_mensaje(remitente, header + db_res)

        elif comando_base == "/weekly":
            self.motor.enviar_mensaje(remitente, self.saver.generar_resumen_semanal())

        elif comando_base == "/remove":
            self.estado.estados[remitente] = "ESPERANDO_BORRADO_DB"
            self.motor.enviar_mensaje(remitente, "⚠️ *ALERTA* ¿Borrar toda la base de datos? (Sí/No)")

        elif comando_base == "/remember":
            query = texto_completo[9:].strip()
            if not query:
                self.motor.enviar_mensaje(remitente, "⚠️ Uso: `/remember [pregunta]`")
            else:
                self.motor.enviar_mensaje(remitente, self.saver.recordar_topic(query))

        elif comando_base == "/remind":
            self.motor.enviar_mensaje(remitente, self.reminders.procesar_remind(remitente, texto_completo))

        elif comando_base == "/interval":
            self.motor.enviar_mensaje(remitente, self.reminders.procesar_intervalo(remitente, texto_completo))

        elif comando_base == "/export":
            ruta, msg = self.saver.exportar_markdown()
            if ruta and hasattr(self.motor, "enviar_archivo") and getattr(self.motor, "public_url", None):
                # Enviar el fichero .md directamente por WhatsApp
                self.motor.enviar_archivo(remitente, ruta, caption=msg)
            else:
                # Fallback: solo mensaje de texto (simulador o sin URL pública)
                self.motor.enviar_mensaje(remitente, msg if msg else "📭 No hay nada que exportar.")

        elif comando_base == "/quiz":
            self.motor.enviar_mensaje(
                remitente,
                self.quizzer.generar_quiz_semanal(remitente, self.textos, self.saver, self.streak_manager)
            )

    @staticmethod
    def _formatear_menu_grupos(grupos):
        lineas = ["🗂️ *He detectado varios temas en tu inbox. ¿Cuál proceso?*\n"]
        for i, g in enumerate(grupos, 1):
            lineas.append(f"  *{i}.* {g['titulo']} ({len(g['indices'])} notas)")
        lineas.append(f"\n  *todos* — Procesar todo junto")
        lineas.append("\nPuedes combinar: *1 3*, *1 2*, *todos*")
        return "\n".join(lineas)
