class StateManager:
    def __init__(self):
        self.estados = {}
        self.datos_temporales = {}

    # ------------------------------------------------------------------
    # Estado 1: selección de grupo temático (Opción A)
    # datos_temporales[remitente] = {
    #     "notas_resueltas": [...],
    #     "grupos": [{"titulo": "...", "indices": [...]}, ...]
    # }
    # ------------------------------------------------------------------
    def set_estado_seleccion_grupo(self, remitente: str, resultado_grupos: dict):
        self.estados[remitente] = "ESPERANDO_SELECCION_GRUPO"
        self.datos_temporales[remitente] = resultado_grupos

    def obtener_grupos(self, remitente: str) -> dict:
        return self.datos_temporales.get(remitente)

    # ------------------------------------------------------------------
    # Estado 2: validación de propuesta IA (flujo existente)
    # datos_temporales[remitente] = {"tema": ..., "resumen": ..., ...}
    # ------------------------------------------------------------------
    def set_estado_validacion(self, remitente: str, propuesta: dict):
        self.estados[remitente] = "ESPERANDO_VALIDACION_INBOX"
        self.datos_temporales[remitente] = propuesta

    def obtener_propuesta(self, remitente: str) -> dict:
        return self.datos_temporales.get(remitente)

    def esta_esperando_validacion(self, remitente: str) -> bool:
        return self.estados.get(remitente) == "ESPERANDO_VALIDACION_INBOX"

    # ------------------------------------------------------------------
    # Utilidades comunes
    # ------------------------------------------------------------------
    def limpiar_estado(self, remitente: str):
        self.estados.pop(remitente, None)
        self.datos_temporales.pop(remitente, None)
