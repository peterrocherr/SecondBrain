import uvicorn
import json
from fastapi import FastAPI, Form
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from twilio.rest import Client

class WhatsAppComms:
    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(WhatsAppComms, cls).__new__(cls)
            cls._instancia._inicializar()
        return cls._instancia

    def _inicializar(self):
        self.funcion_recepcion = None
        self.scheduler = BackgroundScheduler()
        self.twilio_client = None
        self.numero_twilio = None

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.scheduler.start()
            yield
            self.scheduler.shutdown()

        self.app = FastAPI(lifespan=lifespan)

        @self.app.get("/")
        async def home():
            return {"status": "Cerebro Digital Online"}

        # Aceptar MediaUrl y NumMedia
        @self.app.post("/whatsapp")
        async def webhook_whatsapp(
            From: str = Form(...), 
            Body: str = Form(""), 
            NumMedia: str = Form("0"), 
            MediaUrl0: str = Form(None), 
            MediaContentType0: str = Form(None)
        ):
            if self.funcion_recepcion:
                # Le pasamos todos los datos nuevos a main.py
                self.funcion_recepcion(From, Body, NumMedia, MediaUrl0, MediaContentType0)
            return {"status": "ok"}

    def configurar_recepcion(self, funcion):
        self.funcion_recepcion = funcion

    def configurar_twilio(self, account_sid: str, auth_token: str, numero_twilio: str):
        self.twilio_client = Client(account_sid, auth_token)
        self.numero_twilio = numero_twilio
        print("🔌 Conexión con Twilio establecida.")

    def enviar_mensaje(self, destinatario: str, texto: str):
        if not self.twilio_client: return
        if not destinatario.startswith("whatsapp:"): destinatario = f"whatsapp:{destinatario}"
        try:
            self.twilio_client.messages.create(from_=self.numero_twilio, body=texto, to=destinatario)
        except Exception as e:
            print(f"❌ Error enviando mensaje a Twilio: {e}")

    def enviar_botones(self, destinatario: str, texto_cuerpo: str, botones: list):
        """
        Envía botones de respuesta rápida (Quick Replies).
        Twilio admite un máximo de 3 botones con títulos de hasta 20 caracteres.
        """
        if not self.twilio_client: return
        if not destinatario.startswith("whatsapp:"): destinatario = f"whatsapp:{destinatario}"
        
        try:
            # Twilio requiere que el ID sea en minúsculas y sin espacios raros idealmente
            actions = [{"type": "reply", "reply": {"id": b[:20].lower(), "title": b[:20]}} for b in botones[:3]]
            
            self.twilio_client.messages.create(
                from_=self.numero_twilio,
                to=destinatario,
                body=texto_cuerpo,
                persistent_action=[{
                    "type": "whatsapp:interactive",
                    "parameters": {
                        "type": "button",
                        "body": {"text": texto_cuerpo},
                        "action": {"buttons": actions}
                    }
                }]
            )
        except Exception as e:
            print(f"❌ Error enviando botones Twilio: {e}")
            # Fallback de seguridad: si fallan los botones, enviamos como texto normal
            self.enviar_mensaje(destinatario, f"{texto_cuerpo}\n\nOpciones: {', '.join(botones)}")

    def enviar_lista(self, destinatario: str, texto_cuerpo: str, titulo_boton: str, opciones: list):
        """
        Envía un menú desplegable (lista).
        'opciones' debe ser una lista de tuplas (id_opcion, titulo_opcion).
        """
        if not self.twilio_client: return
        if not destinatario.startswith("whatsapp:"): destinatario = f"whatsapp:{destinatario}"
        
        try:
            rows = []
            for row_id, titulo in opciones[:10]: # Máximo 10 opciones
                rows.append({"id": str(row_id)[:20], "title": str(titulo)[:24]})

            self.twilio_client.messages.create(
                from_=self.numero_twilio,
                to=destinatario,
                body=texto_cuerpo,
                persistent_action=[{
                    "type": "whatsapp:interactive",
                    "parameters": {
                        "type": "list",
                        "body": {"text": texto_cuerpo},
                        "action": {
                            "button": titulo_boton[:20],
                            "sections": [{"title": "Opciones disponibles", "rows": rows}]
                        }
                    }
                }]
            )
        except Exception as e:
            print(f"❌ Error enviando lista Twilio: {e}")
            self.enviar_mensaje(destinatario, texto_cuerpo)

    def iniciar(self, puerto=8000):
        print("Iniciando servidor...")
        uvicorn.run(self.app, host="0.0.0.0", port=puerto)