class InboxManager:
    def __init__(self):
        self.notas = []

    def guardar_nota(self, texto: str) -> bool:
        if texto.strip():
            self.notas.append(texto)
            return True
        return False

    def obtener_todo(self) -> list:
        # Devolvemos una copia de la lista para evitar errores de referencia
        return list(self.notas)

    def vaciar(self):
        """Limpia la cola por completo."""
        self.notas = []
        print("🧹 Inbox vaciado correctamente.")