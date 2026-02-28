import datetime

class ReminderManager:
    def __init__(self, llm, scheduler, send_func, saver):
        self.llm = llm
        self.scheduler = scheduler
        self.send_func = send_func
        self.saver = saver

    def procesar_intervalo(self, remitente, texto):
        """Configura el intervalo de repaso y programa la tarea."""
        try:
            # Extraer número del comando: /interval 12
            partes = texto.split()
            if len(partes) < 2:
                return "⚠️ Usage: `/interval [hours]` (e.g., `/interval 24` for daily checks)"
            
            horas = int(partes[1])
            self.saver.set_intervalo(remitente, horas)
            
            # Programar la tarea proactiva en el scheduler
            job_id = f"recall_{remitente}"
            # Eliminamos si ya existía una para ese usuario
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Añadimos la nueva tarea recurrente
            self.scheduler.add_job(
                self.daily_recall, 
                'interval', 
                hours=horas, 
                args=[remitente], 
                id=job_id
            )
            
            return f"✅ Spaced Repetition set to every {horas} hours. I'll message you proactively!"
        except ValueError:
            return "❌ Please provide a valid number of hours."

    def daily_recall(self, remitente):
        """El bot te escribe de forma proactiva para repasar."""
        nota = self.saver.obtener_topic_aleatorio()
        if nota:
            mensaje = (
                f"🧠 *PROACTIVE RECALL*\n"
                f"Time to refresh your memory! Do you remember this?\n\n"
                f"*Topic:* {nota['tema']}\n"
                f"*Summary:* {nota['resumen']}\n\n"
                f"Use `/quiz` if you want to test yourself!"
            )
            self.send_func(remitente, mensaje)

    def procesar_remind(self, remitente, texto):
        # Lógica simple de recordatorios puntuales
        remind_text = texto.replace("/remind", "").strip()
        return f"⏰ Reminder set for: {remind_text} (Simulated)"