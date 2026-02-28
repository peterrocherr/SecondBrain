import sqlite3
from datetime import datetime

class StreakManager:
    def __init__(self, db_path="cerebro.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._crear_tabla()

    def _crear_tabla(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                telefono TEXT PRIMARY KEY, racha INTEGER DEFAULT 0, puntuacion INTEGER DEFAULT 0,
                vidas INTEGER DEFAULT 3, intervalo_dias INTEGER DEFAULT 7, topics_nuevos INTEGER DEFAULT 0,
                quizzes_hoy INTEGER DEFAULT 0, fecha_ultimo_quiz TEXT DEFAULT '2000-01-01'
            )
        ''')
        self.conn.commit()

    def _asegurar_usuario(self, telefono: str):
        self.conn.execute('INSERT OR IGNORE INTO usuarios (telefono) VALUES (?)', (telefono,))
        self.conn.commit()

    def registrar_topic(self, telefono: str):
        self._asegurar_usuario(telefono)
        self.conn.execute('UPDATE usuarios SET topics_nuevos = topics_nuevos + 1 WHERE telefono = ?', (telefono,))
        self.conn.commit()

    def puede_hacer_quiz(self, telefono: str):
        self._asegurar_usuario(telefono)
        cursor = self.conn.cursor()
        cursor.execute('SELECT topics_nuevos FROM usuarios WHERE telefono = ?', (telefono,))
        return cursor.fetchone()[0] >= 5

    def registrar_acierto(self, telefono: str):
        hoy = datetime.now().strftime('%Y-%m-%d')
        cursor = self.conn.cursor()
        cursor.execute('SELECT quizzes_hoy, fecha_ultimo_quiz FROM usuarios WHERE telefono = ?', (telefono,))
        quizzes_hoy, fecha_ultimo = cursor.fetchone()

        if hoy != fecha_ultimo: quizzes_hoy = 0

        recompensas = [10, 5, 2, 1] 
        indice = min(quizzes_hoy, 3)
        puntos_ganados = recompensas[indice]
        rendimiento_str = ["100%", "50%", "20%", "10%"][indice]

        cursor.execute('''UPDATE usuarios SET racha = racha + 1, puntuacion = puntuacion + ?, vidas = 3, 
                          topics_nuevos = 0, quizzes_hoy = ?, fecha_ultimo_quiz = ? WHERE telefono = ?''', 
                       (puntos_ganados, quizzes_hoy + 1, hoy, telefono))
        self.conn.commit()
        
        cursor.execute('SELECT racha, puntuacion, vidas FROM usuarios WHERE telefono = ?', (telefono,))
        racha, puntuacion, vidas = cursor.fetchone()
        return racha, puntuacion, vidas, puntos_ganados, rendimiento_str

    def registrar_fallo(self, telefono: str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT vidas FROM usuarios WHERE telefono = ?', (telefono,))
        vidas = cursor.fetchone()[0]

        if vidas > 1:
            cursor.execute('UPDATE usuarios SET vidas = vidas - 1 WHERE telefono = ?', (telefono,))
            self.conn.commit()
            return vidas - 1, False
        else:
            cursor.execute('UPDATE usuarios SET vidas = 3, racha = 0 WHERE telefono = ?', (telefono,))
            self.conn.commit()
            return 3, True

    def cambiar_intervalo(self, telefono: str, dias: int):
        self._asegurar_usuario(telefono)
        self.conn.execute('UPDATE usuarios SET intervalo_dias = ? WHERE telefono = ?', (dias, telefono))
        self.conn.commit()