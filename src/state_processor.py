class StateProcessor:
    def __init__(self, saver, inbox, streak_manager, motor, estado, ai=None):
        self.saver = saver
        self.inbox = inbox
        self.streak_manager = streak_manager
        self.motor = motor
        self.estado = estado
        self.ai = ai  # Necesario para generar propuesta tras selección de grupo

    def procesar_estado(self, remitente, texto_usuario):
        estado_actual = self.estado.estados.get(remitente)

        # ----------------------------------------------------------------
        # Estado A: el usuario elige qué grupo procesar
        # ----------------------------------------------------------------
        if estado_actual == "ESPERANDO_SELECCION_GRUPO":
            return self._manejar_seleccion_grupo(remitente, texto_usuario)

        # ----------------------------------------------------------------
        # Estado B: el usuario valida la propuesta de la IA (Yes/No)
        # ----------------------------------------------------------------
        if estado_actual == "ESPERANDO_VALIDACION_INBOX":
            return self._manejar_validacion_inbox(remitente, texto_usuario)

        # ----------------------------------------------------------------
        # Estado C: confirmación de borrado de DB
        # ----------------------------------------------------------------
        if estado_actual == "ESPERANDO_BORRADO_DB":
            return self._manejar_borrado(remitente, texto_usuario)

        return False

    # ------------------------------------------------------------------

    def _manejar_seleccion_grupo(self, remitente, texto_usuario):
        datos = self.estado.obtener_grupos(remitente)
        if not datos:
            self.estado.limpiar_estado(remitente)
            return True

        grupos = datos["grupos"]
        notas_resueltas = datos["notas_resueltas"]
        entrada = texto_usuario.strip().lower().rstrip(".,!?¿¡")

        # Parsear la selección: acepta "1", "1 3", "1,3", "1 y 3", "todos"
        if entrada in ["todos", "all", "todo"]:
            indices_grupos = list(range(len(grupos)))
            etiqueta = "Todo el inbox"
        else:
            import re as _re
            numeros = _re.findall(r'\d+', entrada)
            indices_grupos = []
            for n in numeros:
                idx = int(n) - 1  # 1-based → 0-based
                if 0 <= idx < len(grupos):
                    indices_grupos.append(idx)

            if not indices_grupos:
                self.motor.enviar_mensaje(remitente, self._formatear_menu(grupos, invalida=True))
                return True

            # Deduplicar manteniendo orden
            indices_grupos = list(dict.fromkeys(indices_grupos))
            titulos = [grupos[i]["titulo"] for i in indices_grupos]
            etiqueta = " + ".join(titulos)

        # Reunir notas de todos los grupos seleccionados (sin duplicados, en orden)
        indices_notas = []
        for ig in indices_grupos:
            for i in grupos[ig]["indices"]:
                if i not in indices_notas:
                    indices_notas.append(i)
        notas_seleccionadas = [notas_resueltas[i] for i in indices_notas]

        # Generar propuesta para el grupo seleccionado
        self.motor.enviar_mensaje(remitente, f"🧠 Generating proposal for *{etiqueta}*...")
        propuesta = self.ai.generar_propuesta(notas_seleccionadas)

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
                "❌ Couldn't generate a proposal for this group. "
                "Try /rectify to add more context, then /process again."
            )
            self.estado.limpiar_estado(remitente)

        return True

    def _manejar_validacion_inbox(self, remitente, texto_usuario):
        if texto_usuario in ["yes", "y", "sí", "si"]:
            propuesta = self.estado.obtener_propuesta(remitente)
            if self.saver.guardar_conocimiento_final(
                propuesta['tema'],
                propuesta['resumen'],
                propuesta.get('fuentes', 'Inbox')
            ):
                self.inbox.vaciar(usuario=remitente)
                self.streak_manager.registrar_topic(remitente)
                self.motor.enviar_mensaje(remitente, f"✅ Knowledge saved: *{propuesta['tema']}*")
            else:
                self.motor.enviar_mensaje(remitente, "❌ Error saving data.")
        elif texto_usuario in ["no", "n"]:
            self.motor.enviar_mensaje(remitente, "❌ Discarded. Notes remain in Inbox.")

        self.estado.limpiar_estado(remitente)
        return True

    def _manejar_borrado(self, remitente, texto_usuario):
        if texto_usuario in ["yes", "y", "sí", "si"]:
            self.saver.borrar_cerebro()
            self.motor.enviar_mensaje(remitente, "🗑️ Database wiped completely.")
        else:
            self.motor.enviar_mensaje(remitente, "😅 Wipe cancelled.")
        self.estado.limpiar_estado(remitente)
        return True

    # ------------------------------------------------------------------

    @staticmethod
    def _formatear_menu(grupos, invalida=False):
        lineas = []
        if invalida:
            lineas.append("⚠️ Invalid option. Use numbers, combinations or 'todos'.\n")
        lineas.append("🗂️ *Choose which groups to process:*\n")
        for i, g in enumerate(grupos, 1):
            lineas.append(f"  *{i}.* {g['titulo']} ({len(g['indices'])} notes)")
        lineas.append(f"\n  *todos* — Process everything together")
        lineas.append("\nYou can combine groups: *1*, *2*, *1 3*, *1 2 3*, *todos*")
        return "\n".join(lineas)
