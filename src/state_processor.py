class StateProcessor:
    def __init__(self, saver, inbox, streak_manager, motor, estado):
        self.saver = saver
        self.inbox = inbox
        self.streak_manager = streak_manager
        self.motor = motor
        self.estado = estado

    def procesar_estado(self, remitente, comando_base):
        estado_actual = self.estado.estados.get(remitente)
        
        # Validating the Inbox organization proposal
        if estado_actual == "ESPERANDO_VALIDACION_INBOX":
            if comando_base in ["yes", "y", "sí", "si"]:
                propuesta = self.estado.obtener_propuesta(remitente)
                if self.saver.guardar_conocimiento_final(propuesta['tema'], propuesta['resumen'], propuesta.get('fuentes', 'Inbox')):
                    self.inbox.vaciar()
                    self.streak_manager.registrar_topic(remitente)
                    self.motor.enviar_mensaje(remitente, f"✅ Knowledge saved: {propuesta['tema']}")
                else:
                    self.motor.enviar_mensaje(remitente, "❌ Error saving data.")
            elif comando_base in ["no", "n"]:
                self.motor.enviar_mensaje(remitente, "❌ Discarded. Notes remain in Inbox.")
            
            self.estado.limpiar_estado(remitente)
            return True

        # Validating Database Wipe
        elif estado_actual == "ESPERANDO_BORRADO_DB":
            if comando_base in ["yes", "y", "sí", "si"]:
                self.saver.borrar_cerebro()
                self.motor.enviar_mensaje(remitente, "🗑️ Database wiped completely.")
            else:
                self.motor.enviar_mensaje(remitente, "😅 Wipe cancelled.")
            self.estado.limpiar_estado(remitente)
            return True

        return False