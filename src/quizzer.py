import sqlite3
import json

class Quizzer:
    def __init__(self, llm, db_path="cerebro.db"):
        self.llm = llm
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.quiz_actual = {} # Guarda {"respuestas": "ABC", "texto": "..."}

    def generar_quiz_semanal(self, telefono: str, textos: dict, saver, streak_manager):
        # Si ya tiene un quiz a medias, se lo reenviamos intacto
        if telefono in self.quiz_actual:
            return "⚠️ Ya tienes un examen a medias. ¡Aquí lo tienes de nuevo!\n\n" + self.quiz_actual[telefono]["texto"]

        if saver.contar_topics() < 5: return textos["quiz_sin_topics"]
        if not streak_manager.puede_hacer_quiz(telefono): return textos["quiz_sin_nuevos"]

        cursor = self.conn.cursor()
        cursor.execute('SELECT tema, resumen FROM topics ORDER BY id DESC LIMIT 5')
        topics = cursor.fetchall()

        contexto = "\n".join([f"Tema: {t[0]}\nResumen: {t[1]}" for t in topics])
        prompt = f"Genera repaso y 5 preguntas test A/B/C. Devuelve SOLO JSON: {{\"repaso\": \"...\", \"preguntas\": [{{ \"pregunta\": \"...\", \"opciones\": [\"A)...\"], \"correcta\": \"A\" }}] }}\nContexto: {contexto}"
        
        try:
            datos = json.loads(self.llm.consultar(prompt).replace("```json", "").replace("```", "").strip())
            mensaje = f"📚 *REPASO*\n\n{datos['repaso']}\n\n❓ *QUIZ*\n"
            ans = ""
            for i, p in enumerate(datos['preguntas']):
                mensaje += f"\n{i+1}. {p['pregunta']}\n" + "\n".join(p['opciones']) + "\n"
                ans += p['correcta']
            
            mensaje_final = mensaje + "\n👉 Responde con las 5 letras (ej. ABCAA)."
            self.quiz_actual[telefono] = {"respuestas": ans, "texto": mensaje_final}
            
            return mensaje_final
        except: return textos["quiz_error_ia"]

    def evaluar_respuesta(self, telefono: str, respuestas_usuario: str, streak_manager, textos: dict):
        if telefono not in self.quiz_actual: return textos["quiz_sin_activo"]
            
        usuario_limpio = respuestas_usuario.strip().upper().replace(" ", "")
        correctas = self.quiz_actual[telefono]["respuestas"]
        
        if usuario_limpio == correctas:
            racha, puntos, vidas, pts_ganados, rend = streak_manager.registrar_acierto(telefono)
            del self.quiz_actual[telefono] 
            return textos["quiz_acierto"].format(puntos_ganados=pts_ganados, rendimiento=rend, racha=racha, vidas=vidas, puntos=puntos)
        else:
            vidas_restantes, ha_muerto = streak_manager.registrar_fallo(telefono)
            if ha_muerto:
                del self.quiz_actual[telefono]
                return textos["quiz_muerte"].format(correctas=correctas)
            else:
                return textos["quiz_fallo"].format(correctas=correctas, vidas=vidas_restantes)