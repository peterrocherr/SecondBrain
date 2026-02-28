import uvicorn
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

        @self.app.post("/whatsapp")
        async def webhook_whatsapp(From: str = Form(...), Body: str = Form(...)):
            if self.funcion_recepcion:
                self.funcion_recepcion(From, Body)
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

    def iniciar(self, puerto=8000):
        print("Iniciando servidor...")
        uvicorn.run(self.app, host="0.0.0.0", port=puerto)