import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Importamos tus piezas del motor
from llm_manager import LLMManager
from saver import Saver
from streak_manager import StreakManager
from quizzer import Quizzer
from reminder_manager import ReminderManager
from message_router import MessageRouter
from inbox_manager import InboxManager
from state_manager import StateManager
from ai_processor import AIProcessor

# --- MOCK DEL MOTOR (Simulamos WhatsAppComms) ---
class MockMotor:
    def __init__(self):
        self.scheduler = type('obj', (object,), {'get_job': lambda *a: None, 'remove_job': lambda *a: None, 'add_job': lambda *a: None})

    def enviar_mensaje(self, destinatario, texto):
        print(f"\n[BOT]: {texto}")

def simulator():
    # 1. Configuración igual que en main.py
    load_dotenv()
    with open("messages.json", "r", encoding="utf-8") as f:
        textos = json.load(f)

    print("===================================================")
    print(" DIGITAL BRAIN - CONSOLE SIMULATOR")
    print("===================================================")
    print("Escribe tus mensajes abajo. Simula audios, vídeos o PDFs con:")
    print("  !pdf C:\\ruta\\archivo.pdf")
    print("  !audio C:\\ruta\\audio.ogg")
    print("  !video C:\\ruta\\video.mp4")
    print("Comandos extra:")
    print("  !debug  -> Ver las notas pendientes en el Inbox")
    print("  exit    -> Cerrar el simulador")
    print("===================================================\n")

    # 2. Inicialización de servicios
    llm = LLMManager(api_key=os.getenv("GEMINI_API_KEY"))
    saver = Saver(llm=llm)
    streak_manager = StreakManager()
    motor_falso = MockMotor()
    
    inbox = InboxManager()
    estado = StateManager()
    ai_processor = AIProcessor(modelo_llm=llm)
    
    reminders = ReminderManager(llm=llm, scheduler=motor_falso.scheduler, send_func=motor_falso.enviar_mensaje, saver=saver)
    quizzer = Quizzer(llm=llm)

    # 3. El Router (el cerebro real)
    router = MessageRouter(saver, streak_manager, quizzer, reminders, textos, motor_falso, inbox, ai_processor, estado)

    # 4. Bucle de chat
    user_phone = "whatsapp:+123456789"
    
    while True:
        try:
            user_input = input("\n[TÚ]: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'salir']:
                print("👋 Apagando simulador...")
                break
            
            # Variables por defecto (Simulando un mensaje de texto normal de Twilio)
            num_media = "0"
            media_url = None
            media_type = None
            texto_final = user_input

            # --- DETECCIÓN DE ARCHIVOS MULTIMEDIA ---
            if user_input.startswith("!pdf "):
                num_media = "1"
                media_url = user_input.replace("!pdf ", "").strip()
                media_type = "application/pdf"
                texto_final = "Te mando este PDF."
                
            elif user_input.startswith("!audio "):
                num_media = "1"
                media_url = user_input.replace("!audio ", "").strip()
                media_type = "audio/ogg"
                texto_final = "Te mando este audio."
                
            elif user_input.startswith("!video "):
                num_media = "1"
                media_url = user_input.replace("!video ", "").strip()
                media_type = "video/mp4" 
                texto_final = "He mandado este vídeo para analizar."

            # --- HERRAMIENTA DE DEBUG ---
            elif user_input == "!debug":
                print("\n🔍 [DEBUG - ESTADO DEL INBOX]")
                notas = inbox.obtener_todo()
                print(f"Notas acumuladas: {len(notas)}")
                for i, n in enumerate(notas):
                    print(f"  {i+1}. {n[:150]}...")
                continue

            # Ejecutamos la lógica real del router
            router.procesar_mensaje(user_phone, texto_final, num_media, media_url, media_type)

        except KeyboardInterrupt:
            print("\n👋 Apagando simulador de forma forzada...")
            break
        except Exception as e:
            print(f"❌ Error en el simulador: {e}")

if __name__ == "__main__":
    simulator()