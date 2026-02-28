import os
import json
from dotenv import load_dotenv

from WhatsAppComms import WhatsAppComms
from llm_manager import LLMManager
from saver import Saver
from streak_manager import StreakManager
from quizzer import Quizzer
from reminder_manager import ReminderManager

load_dotenv()
with open("messages.json", "r", encoding="utf-8") as f:
    TEXTOS = json.load(f)

mi_llm = LLMManager(api_key=os.getenv("GEMINI_API_KEY"))
saver = Saver(llm=mi_llm)
streak_manager = StreakManager()
quizzer = Quizzer(llm=mi_llm)
motor = WhatsAppComms()
motor.configurar_twilio(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"), os.getenv("TWILIO_PHONE"))

reminders = ReminderManager(llm=mi_llm, scheduler=motor.scheduler, send_func=motor.enviar_mensaje)

def enrutador_principal(remitente, texto):
    try:
        texto = texto.strip()
        comando = texto.lower()
        respuesta = ""

        if comando == "/quiz":
            respuesta = quizzer.generar_quiz_semanal(remitente, TEXTOS, saver, streak_manager)
        elif len(texto) == 5 and all(l in "ABC" for l in texto.upper()):
            respuesta = quizzer.evaluar_respuesta(remitente, texto, streak_manager, TEXTOS)
        elif comando.startswith("/interval "):
            respuesta = reminders.procesar_intervalo(remitente, texto, streak_manager, TEXTOS)
        elif comando.startswith("/remember "):
            query = texto.replace("/remember ", "").strip()
            respuesta = saver.recordar_topic(query)
        elif comando.startswith("/remind "):
            respuesta = reminders.procesar_remind(remitente, texto, TEXTOS)
        else:
            tema = saver.procesar_y_guardar(texto)
            if tema:
                streak_manager.registrar_topic(remitente)
                respuesta = TEXTOS["captura_exito"].format(tema=tema, total=saver.contar_topics())
            else:
                respuesta = TEXTOS["captura_error"]

        motor.enviar_mensaje(remitente, respuesta)

    except Exception as e:
        print(f"\nERROR FATAL PROCESANDO MENSAJE DE {remitente}:")
        print(str(e))
        print("--------------------------------------------------\n")
        motor.enviar_mensaje(remitente, TEXTOS.get("error_critico", "Error en el servidor."))

if __name__ == "__main__":
    motor.configurar_recepcion(enrutador_principal)
    motor.iniciar(puerto=8000)