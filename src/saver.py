import sqlite3

class Saver:
    def __init__(self, db_path="cerebro.db", llm=None):
        self.llm = llm
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')  # Evita 'database is locked' en escrituras concurrentes
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.crear_tablas()

    def crear_tablas(self):
        # Tabla de conocimiento
        self.conn.execute('''CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            tema TEXT, resumen TEXT, fuentes TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # NUEVA: Tabla de configuración de usuario
        self.conn.execute('''CREATE TABLE IF NOT EXISTS config (
            usuario TEXT PRIMARY KEY,
            intervalo_horas INTEGER DEFAULT 24,
            ultima_interaccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        self.conn.commit()

    def guardar_conocimiento_final(self, tema: str, resumen: str, fuentes: str = "Inbox") -> bool:
        try:
            self.conn.execute('INSERT INTO topics (tema, resumen, fuentes) VALUES (?, ?, ?)', (tema, resumen, fuentes))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error Saver: {e}")
            return False

    def obtener_topic_aleatorio(self):
        """Recupera una nota al azar para el repaso proactivo."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT tema, resumen FROM topics ORDER BY RANDOM() LIMIT 1')
        res = cursor.fetchone()
        return {"tema": res[0], "resumen": res[1]} if res else None

    def set_intervalo(self, usuario, horas):
        self.conn.execute('INSERT OR REPLACE INTO config (usuario, intervalo_horas) VALUES (?, ?)', (usuario, horas))
        self.conn.commit()

    def get_intervalo(self, usuario):
        cursor = self.conn.cursor()
        cursor.execute('SELECT intervalo_horas FROM config WHERE usuario = ?', (usuario,))
        res = cursor.fetchone()
        return res[0] if res else 24

    def contar_topics(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM topics')
        return cursor.fetchone()[0]

    def listar_conocimiento(self, offset: int = 0, limite: int = 15):
        cursor = self.conn.cursor()
        cursor.execute('SELECT fecha, tema FROM topics ORDER BY fecha DESC LIMIT ? OFFSET ?', (limite + 1, offset))
        resultados = cursor.fetchall()
        if not resultados: return "📭 Brain is empty.", False
        hay_mas = len(resultados) > limite
        texto = "📚 *DIGITAL BRAIN LOG*\n\n" + "\n".join([f"🔹 [{r[0].split()[0]}] {r[1]}" for r in resultados[:limite]])
        return texto, hay_mas

    def recordar_topic(self, query: str, limite: int = 20):
        if not self.llm: return "IA not configured."
        cursor = self.conn.cursor()
        # Limitamos el contexto enviado al LLM para evitar desbordamiento
        cursor.execute('SELECT tema, resumen FROM topics ORDER BY fecha DESC LIMIT ?', (limite,))
        topics = cursor.fetchall()
        if not topics: return "No knowledge stored."
        contexto = "\n".join([f"- {t[0]}: {t[1][:300]}" for t in topics])
        return self.llm.consultar(f"Based on this knowledge base:\n{contexto}\n\nAnswer concisely: {query}")


    def exportar_markdown(self, carpeta: str = "cerebro_digital") -> str:
        """
        Exporta todos los topics a ficheros Markdown individuales.
        Kelea valora explícitamente formatos abiertos y portabilidad.
        Cada fichero es compatible con Obsidian, MkDocs o cualquier editor.
        """
        import os
        os.makedirs(carpeta, exist_ok=True)

        cursor = self.conn.cursor()
        cursor.execute('SELECT tema, resumen, fuentes, fecha FROM topics ORDER BY fecha DESC')
        topics = cursor.fetchall()

        if not topics:
            return "📭 No hay topics para exportar."

        archivos = []
        for tema, resumen, fuentes, fecha in topics:
            # Nombre de fichero seguro
            nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in tema)[:60].strip()
            ruta = os.path.join(carpeta, f"{nombre}.md")

            contenido = f"""# {tema}

> **Fuentes:** {fuentes}  
> **Fecha:** {fecha}

{resumen}
"""
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            archivos.append(nombre)

        # Crear índice general
        indice = "# 🧠 Cerebro Digital\n\n"
        indice += "\n".join([f"- [[{a}]]" for a in archivos])
        with open(os.path.join(carpeta, "INDEX.md"), "w", encoding="utf-8") as f:
            f.write(indice)

        return f"✅ Exportados {len(archivos)} topics a `/{carpeta}/`. Compatible con Obsidian y MkDocs."

    def borrar_cerebro(self):
        """Elimina todos los topics de la base de datos."""
        self.conn.execute('DELETE FROM topics')
        self.conn.commit()

    def generar_resumen_semanal(self):
        if not self.llm: return "IA not configured."
        cursor = self.conn.cursor()
        cursor.execute("SELECT tema, resumen FROM topics WHERE fecha >= date('now', '-7 days')")
        notes = cursor.fetchall()
        if not notes: return "No new notes this week."
        contexto = "\n".join([f"Topic: {n[0]}\nSummary: {n[1]}" for n in notes])
        return self.llm.consultar(f"Create a weekly synthesis of these topics:\n{contexto}")