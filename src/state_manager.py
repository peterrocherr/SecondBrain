class StateManager:
    def __init__(self):
        # Guarda el estado actual del usuario (ej: "ESPERANDO_VALIDACION")
        self.estados = {}
        # Guarda temporalmente los datos asociados a ese estado (ej: la propuesta de la IA)
        self.datos_temporales = {}

    def set_estado_validacion(self, remitente: str, propuesta: dict):
        """Activa el modo de espera de validación para un usuario."""
        self.estados[remitente] = "ESPERANDO_VALIDACION"
        self.datos_temporales[remitente] = propuesta

    def esta_esperando_validacion(self, remitente: str) -> bool:
        """Comprueba si el usuario debe responder Sí/No."""
        return self.estados.get(remitente) == "ESPERANDO_VALIDACION"

    def obtener_propuesta(self, remitente: str) -> dict:
        """Recupera la propuesta temporal generada por la IA."""
        return self.datos_temporales.get(remitente)

    def limpiar_estado(self, remitente: str):
        """Resetea al usuario a su estado normal."""
        if remitente in self.estados:
            del self.estados[remitente]
        if remitente in self.datos_temporales:
            del self.datos_temporales[remitente]