class StateManager:
    def __init__(self):
        self.estados = {}
        self.datos_temporales = {}

    def set_estado_validacion(self, remitente: str, propuesta: dict):
        """Activa el modo de espera de validación para un usuario."""
        # FIX: nombre de estado alineado con el resto del código
        self.estados[remitente] = "ESPERANDO_VALIDACION_INBOX"
        self.datos_temporales[remitente] = propuesta

    def esta_esperando_validacion(self, remitente: str) -> bool:
        return self.estados.get(remitente) == "ESPERANDO_VALIDACION_INBOX"

    def obtener_propuesta(self, remitente: str) -> dict:
        return self.datos_temporales.get(remitente)

    def limpiar_estado(self, remitente: str):
        if remitente in self.estados:
            del self.estados[remitente]
        if remitente in self.datos_temporales:
            del self.datos_temporales[remitente]
