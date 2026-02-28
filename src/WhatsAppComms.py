import uvicorn
from fastapi import FastAPI, Form
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from twilio.rest import Client

class WhatsAppComms:
    _instancia = None

    def __new__(cls):
        # Singleton: Si no existe la instancia, la creamos. Si existe, la devolvemos.
        if cls._instancia is None:
            cls._instancia = super(WhatsAppComms, cls).__new__(cls)
            cls._instancia._inicializar()
        return cls._instancia

    def _inicializar(self):
        """Se ejecuta solo una vez al crear el Singleton."""
        self.funcion_recepcion = None
        self.scheduler = BackgroundScheduler()
        self.twilio_client = None  # Preparado para guardar la conexión de Twilio
        self.numero_twilio = None  # Preparado para guardar el número del Sandbox

        # Ciclo de vida
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.scheduler.start()
            yield
            self.scheduler.shutdown()

        self.app = FastAPI(lifespan=lifespan)

        # Configuración del Webhook dentro de la clase
        @self.app.post("/whatsapp")
        async def webhook_whatsapp(From: str = Form(...), Body: str = Form(...)):
            if self.funcion_recepcion:
                # Llamamos a la función que nos hayan pasado desde fuera
                self.funcion_recepcion(From, Body)
            return {"status": "ok"}

    def configurar_recepcion(self, funcion):
        """Asigna la función que manejará los mensajes entrantes."""
        self.funcion_recepcion = funcion

    def configurar_tareas(self, lista_tareas: list):
        """Recibe una lista de tuplas [(funcion, "HH:MM")] y las programa."""
        for funcion_tarea, hora_str in lista_tareas:
            hora, minuto = map(int, hora_str.split(':'))
            self.scheduler.add_job(funcion_tarea, 'cron', hour=hora, minute=minuto)
            print(f"⏰ Tarea programada a las {hora_str}")

    def configurar_twilio(self, account_sid: str, auth_token: str, numero_twilio: str):
        """Inicializa la conexión con Twilio una sola vez."""
        self.twilio_client = Client(account_sid, auth_token)
        self.numero_twilio = numero_twilio
        print("🔌 Conexión con Twilio establecida.")

    def enviar_mensaje(self, destinatario: str, texto: str):
        """Función pública para enviar mensajes reales mediante Twilio."""
        # Protección para evitar errores si no has configurado Twilio
        if not self.twilio_client:
            print("⚠️ Error: Debes llamar a configurar_twilio() antes de enviar mensajes.")
            return

        # Aseguramos el formato "whatsapp:+XXXXXXXX" exigido por la API
        if not destinatario.startswith("whatsapp:"):
            destinatario = f"whatsapp:{destinatario}"

        try:
            # Llamada oficial a la API de Twilio para sacar el mensaje
            mensaje = self.twilio_client.messages.create(
                from_=self.numero_twilio,
                body=texto,
                to=destinatario
            )
            print(f"✅ Mensaje enviado a {destinatario} (SID: {mensaje.sid})")
        except Exception as error_api:
            print(f"❌ Fallo al enviar mensaje a través de Twilio: {error_api}")

    def iniciar(self, puerto=8000):
        """Arranca el servidor Uvicorn."""
        print("🚀 Arrancando el Cerebro Digital (WhatsAppComms Singleton)...")
        uvicorn.run(self.app, host="0.0.0.0", port=puerto)