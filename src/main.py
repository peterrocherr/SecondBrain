import os
import json
from dotenv import load_dotenv
from pathlib import Path

from WhatsAppComms import WhatsAppComms
from llm_manager import LLMManager
from saver import Saver
from streak_manager import StreakManager
from quizzer import Quizzer
from reminder_manager import ReminderManager
from message_router import MessageRouter
from inbox_manager import InboxManager
from state_manager import StateManager
from ai_processor import AIProcessor

def iniciar_servidor():
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    with open("messages.json", "r", encoding="utf-8") as f:
        textos = json.load(f)

    # 1. Servicios Base
    llm = LLMManager(api_key=os.getenv("GEMINI_API_KEY"))
    saver = Saver(llm=llm)
    streak_manager = StreakManager()
    motor = WhatsAppComms()
    motor.configurar_twilio(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"), os.getenv("TWILIO_PHONE"))
    # PUBLIC_URL es la URL pública del servidor (ej. https://xxxx.ngrok.io)
    # Necesaria para que Twilio pueda descargar los ficheros de exportación
    if os.getenv("PUBLIC_URL"):
        motor.configurar_url_publica(os.getenv("PUBLIC_URL"))

    # 2. Gestores de Inbox y AI
    inbox = InboxManager()
    estado = StateManager()
    ai_processor = AIProcessor(modelo_llm=llm)

    # 3. Manager de Recordatorios (AHORA USA EL SAVER)
    reminders = ReminderManager(
        llm=llm, 
        scheduler=motor.scheduler, 
        send_func=motor.enviar_mensaje, 
        saver=saver
    )
    
    quizzer = Quizzer(llm=llm)

    # 4. Enrutador Modular
    router = MessageRouter(saver, streak_manager, quizzer, reminders, textos, motor, inbox, ai_processor, estado, llm=llm)

    # 5. Arranque
    motor.configurar_recepcion(router.procesar_mensaje)
    motor.iniciar(puerto=8000)

if __name__ == "__main__":
    iniciar_servidor()