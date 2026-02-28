import uvicorn
import json
import asyncio
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
        # Cola asíncrona para procesar mensajes secuencialmente
        self.queue = asyncio.Queue()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.scheduler.start()
            # Iniciamos el trabajador de la cola en segundo plano
            worker_task = asyncio.create_task(self._worker())
            yield
            worker_task.cancel()
            self.scheduler.shutdown()

        self.app = FastAPI(lifespan=lifespan)

        @self.app.get("/")
        async def home():
            return {"status": "Cerebro Digital Online"}

        @self.app.post("/whatsapp")
        async def webhook_whatsapp(
            MessageSid: str = Form(...),
            From: str = Form(...), 
            Body: str = Form(""), 
            NumMedia: str = Form("0"), 
            MediaUrl0: str = Form(None), 
            MediaContentType0: str = Form(None)
        ):
            if self.funcion_recepcion:
                # Añadimos a la cola y respondemos 200 OK inmediatamente
                await self.queue.put((From, Body, NumMedia, MediaUrl0, MediaContentType0, MessageSid))
            
            return {"status": "ok"}

    async def _worker(self):
        """Procesa la cola de uno en uno para evitar bloqueos de la IA."""
        print("Cola de procesamiento lista.")
        while True:
            datos = await self.queue.get()
            try:
                if self.funcion_recepcion:
                    # Ejecutamos la función de MessageRouter
                    self.funcion_recepcion(*datos)
            except Exception as e:
                print(f"❌ Error en procesamiento de cola: {e}")
            finally:
                self.queue.task_done()
                # Breve pausa para no saturar la API entre archivos
                await asyncio.sleep(1.5)

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
            print(f"❌ Error enviando mensaje: {e}")

    def iniciar(self, puerto=8000):
        print("Iniciando servidor...")
        uvicorn.run(self.app, host="0.0.0.0", port=puerto)