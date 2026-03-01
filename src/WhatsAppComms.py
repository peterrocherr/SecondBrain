import uvicorn
import json
import asyncio
import uuid
import os
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
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
        self.public_url = None  # Se configura desde main.py con la URL pública del servidor
        self._archivos_temporales = {}  # token → ruta_local
        self.queue = asyncio.Queue()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.scheduler.start()
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
                await self.queue.put((From, Body, NumMedia, MediaUrl0, MediaContentType0, MessageSid))
            return {"status": "ok"}

        @self.app.get("/export/{token}")
        async def servir_export(token: str):
            """Sirve temporalmente un fichero de exportación para que Twilio pueda descargarlo."""
            ruta = self._archivos_temporales.get(token)
            if not ruta or not os.path.exists(ruta):
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Fichero no encontrado o expirado")
            return FileResponse(
                path=ruta,
                media_type="text/markdown",
                filename="cerebro_digital.md"
            )

    async def _worker(self):
        print("Cola de procesamiento lista.")
        while True:
            datos = await self.queue.get()
            try:
                if self.funcion_recepcion:
                    self.funcion_recepcion(*datos)
            except Exception as e:
                print(f"❌ Error en procesamiento de cola: {e}")
            finally:
                self.queue.task_done()
                await asyncio.sleep(1.5)

    def configurar_recepcion(self, funcion):
        self.funcion_recepcion = funcion

    def configurar_twilio(self, account_sid: str, auth_token: str, numero_twilio: str):
        self.twilio_client = Client(account_sid, auth_token)
        self.numero_twilio = numero_twilio
        print("🔌 Conexión con Twilio establecida.")

    def configurar_url_publica(self, url: str):
        """URL base pública del servidor (ej. https://xxxx.ngrok.io)."""
        self.public_url = url.rstrip("/")
        print(f"🌐 URL pública configurada: {self.public_url}")

    def enviar_mensaje(self, destinatario: str, texto: str):
        if not self.twilio_client: return
        if not destinatario.startswith("whatsapp:"):
            destinatario = f"whatsapp:{destinatario}"
        try:
            self.twilio_client.messages.create(
                from_=self.numero_twilio,
                body=texto,
                to=destinatario
            )
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    def enviar_archivo(self, destinatario: str, ruta_local: str, caption: str = ""):
        """
        Envía un fichero local por WhatsApp.
        Lo registra en una ruta temporal del servidor y pasa la URL a Twilio.
        Requiere que public_url esté configurada (URL pública del servidor).
        """
        if not self.twilio_client:
            return
        if not self.public_url:
            print("❌ enviar_archivo: public_url no configurada. Usa configurar_url_publica().")
            return
        if not destinatario.startswith("whatsapp:"):
            destinatario = f"whatsapp:{destinatario}"

        # Registrar el fichero con un token único de un solo uso
        token = uuid.uuid4().hex
        self._archivos_temporales[token] = ruta_local
        media_url = f"{self.public_url}/export/{token}"

        try:
            self.twilio_client.messages.create(
                from_=self.numero_twilio,
                body=caption,
                media_url=[media_url],
                to=destinatario
            )
            print(f"📤 Fichero enviado: {media_url}")
        except Exception as e:
            print(f"❌ Error enviando fichero: {e}")
            self._archivos_temporales.pop(token, None)

    def iniciar(self, puerto=8000):
        print("Iniciando servidor...")
        uvicorn.run(self.app, host="0.0.0.0", port=puerto)
