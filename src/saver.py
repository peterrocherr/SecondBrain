import sqlite3
import json
from web_reader import WebReader

class Saver:
    def __init__(self, llm, db_path="cerebro.db"):
        self.llm = llm
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.crear_tablas()

    def crear_tablas(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS topics (id INTEGER PRIMARY KEY AUTOINCREMENT, tema TEXT, resumen TEXT, fuentes TEXT)''')
        self.conn.commit()

    def procesar_y_guardar(self, texto_crudo: str):
        texto_final = WebReader.extraer_texto(texto_crudo)
        prompt = f"Analiza el texto. Extrae tema, resumen y fuentes. Devuelve SOLO JSON: {{\"tema\": \"...\", \"resumen\": \"...\", \"fuentes\": \"...\"}}\nTexto: {texto_final}"
        respuesta_json = self.llm.consultar(prompt)
        
        try:
            datos = json.loads(respuesta_json.replace("```json", "").replace("```", "").strip())
            self.conn.execute('INSERT INTO topics (tema, resumen, fuentes) VALUES (?, ?, ?)', (datos.get('tema'), datos.get('resumen'), str(datos.get('fuentes'))))
            self.conn.commit()
            return datos.get('tema')
        except: return None

    def contar_topics(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM topics')
        return cursor.fetchone()[0]

    def recordar_topic(self, query: str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT tema, resumen FROM topics')
        topics = cursor.fetchall()
        
        if not topics: return "Aún no tengo información guardada."
        lista_topics = "\n".join([f"- {t[0]}: {t[1]}" for t in topics])
        
        prompt = f"Actúa como mi cerebro digital. Topics:\n{lista_topics}\nUsuario: '{query}'. Encuentra el topic y explícalo de forma conversacional. Si no coincide nada, responde: 'No sé a qué te refieres.'"
        return self.llm.consultar(prompt)