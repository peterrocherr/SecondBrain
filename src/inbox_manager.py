import sqlite3
from datetime import datetime

class InboxManager:
    """
    Inbox persistente con metadatos por entrada y soporte multi-usuario.
    Cada nota se guarda con: usuario, tipo detectado, origen, fecha y estado.
    Esto cumple el requisito de Kelea de 'inbox semántico'.
    """

    TIPOS = {
        "[IMAGE_PENDING]": "imagen",
        "[WEB_PENDING]":   "enlace",
        "[PDF]":           "pdf",
        "[AUDIO]":         "audio",
        "[VIDEO]":         "video",
        "[YT]":            "youtube",
        "[YT_PENDING]":    "youtube",
        "[WEB]":           "web",
        "http":            "enlace",
        "User Correction": "corrección",
    }

    def __init__(self, db_path="cerebro.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._crear_tabla()

    def _crear_tabla(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS inbox (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT    NOT NULL,
                texto   TEXT    NOT NULL,
                tipo    TEXT    DEFAULT "texto",
                fecha   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estado  TEXT    DEFAULT "pendiente"
            )
        ''')
        self.conn.commit()

    def _detectar_tipo(self, texto: str) -> str:
        for prefijo, tipo in self.TIPOS.items():
            if prefijo in texto:
                return tipo
        return "texto"

    def guardar_nota(self, texto: str, usuario: str = "default") -> bool:
        texto = texto.strip()
        if not texto:
            return False
        tipo = self._detectar_tipo(texto)
        self.conn.execute(
            'INSERT INTO inbox (usuario, texto, tipo) VALUES (?, ?, ?)',
            (usuario, texto, tipo)
        )
        self.conn.commit()
        return True

    def obtener_todo(self, usuario: str = "default") -> list:
        """Devuelve solo el texto de las notas pendientes del usuario."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT texto FROM inbox WHERE usuario = ? AND estado = "pendiente" ORDER BY fecha ASC',
            (usuario,)
        )
        return [r[0] for r in cursor.fetchall()]

    def obtener_con_metadatos(self, usuario: str = "default") -> list:
        """Devuelve notas completas con todos sus metadatos."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id, texto, tipo, fecha FROM inbox WHERE usuario = ? AND estado = "pendiente" ORDER BY fecha ASC',
            (usuario,)
        )
        return [{"id": r[0], "texto": r[1], "tipo": r[2], "fecha": r[3]} for r in cursor.fetchall()]

    def vaciar(self, usuario: str = "default"):
        """Marca las notas como procesadas (no las borra, conserva historial)."""
        self.conn.execute(
            'UPDATE inbox SET estado = "procesado" WHERE usuario = ? AND estado = "pendiente"',
            (usuario,)
        )
        self.conn.commit()
        print(f"🧹 Inbox de {usuario} marcado como procesado.")

    def contar_pendientes(self, usuario: str = "default") -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM inbox WHERE usuario = ? AND estado = "pendiente"',
            (usuario,)
        )
        return cursor.fetchone()[0]

    def resumen_por_tipo(self, usuario: str = "default") -> str:
        """Devuelve un desglose del inbox por tipo de contenido."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT tipo, COUNT(*) FROM inbox WHERE usuario = ? AND estado = "pendiente" GROUP BY tipo',
            (usuario,)
        )
        filas = cursor.fetchall()
        if not filas:
            return "📭 Inbox vacío."
        iconos = {"texto": "📝", "enlace": "🔗", "imagen": "🖼️", "pdf": "📄",
                  "audio": "🎵", "video": "🎬", "youtube": "▶️", "corrección": "🔧"}
        return "\n".join([f"{iconos.get(t, '📌')} {t}: {c}" for t, c in filas])
