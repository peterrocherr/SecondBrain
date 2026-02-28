import os
import json
from dotenv import load_dotenv

from WhatsAppComms import WhatsAppComms
from llm_manager import LLMManager
from saver import Saver
from streak_manager import StreakManager
from quizzer import Quizzer
from reminder_manager import ReminderManager
from message_router import MessageRouter

def iniciar_servidor():
    # 1. Carga de configuración
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    with open("messages.json", "r", encoding="utf-8") as f:
        textos = json.load(f)

    # 2. Inicialización de Servicios (Base de datos, IA, Servidor)
    llm = LLMManager(api_key=os.getenv("GEMINI_API_KEY"))
    saver = Saver(llm=llm)
    streak_manager = StreakManager()
    quizzer = Quizzer(llm=llm)
    
    motor = WhatsAppComms()
    motor.configurar_twilio(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"), os.getenv("TWILIO_PHONE"))
    
    reminders = ReminderManager(llm=llm, scheduler=motor.scheduler, send_func=motor.enviar_mensaje)

    # 3. El Enrutador (Inyección de dependencias)
    router = MessageRouter(saver, streak_manager, quizzer, reminders, textos, motor)

    # 4. Conexión y Arranque
    motor.configurar_recepcion(router.procesar_mensaje)
    motor.iniciar(puerto=8000)

if __name__ == "__main__":
    iniciar_servidor()