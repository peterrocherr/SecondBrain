import json
from datetime import datetime, timedelta

class ReminderManager:
    def __init__(self, llm, scheduler, send_func):
        self.llm = llm
        self.scheduler = scheduler
        self.send_func = send_func

    def procesar_remind(self, remitente: str, texto: str, textos: dict) -> str:
        ahora = datetime.now()
        fecha_actual = ahora.strftime('%Y-%m-%d %H:%M:%S')
        
        prompt = f"""
        Hoy es {fecha_actual}.
        Analiza esta orden: '{texto}'. 
        Calcula la fecha y hora exacta en la que debo avisar al usuario.
        Devuelve SOLO JSON con este formato estricto: {{"fecha_hora": "YYYY-MM-DD HH:MM:SS", "tarea": "..."}}
        """
        
        try:
            resp = self.llm.consultar(prompt).replace("```json", "").replace("```", "").strip()
            datos = json.loads(resp)
            
            fecha_ejecucion = datetime.strptime(datos["fecha_hora"], '%Y-%m-%d %H:%M:%S')
            self.scheduler.add_job(self.send_func, 'date', run_date=fecha_ejecucion, args=[remitente, f"⏰ RECORDATORIO: {datos['tarea']}"])
            
            fecha_bonita = fecha_ejecucion.strftime('%d/%m/%Y a las %H:%M')
            
            # AQUÍ ESTÁ EL CAMBIO: Volvemos a usar el JSON de textos
            return textos["recordatorio_exito"].format(tarea=datos['tarea'], fecha=fecha_bonita)
            
        except Exception as e:
            print(f"Error en remind: {e}")
            return "❌ No he entendido bien la fecha. Usa algo como: /remind mañana a las 17:00 que llame al dentista."

    def procesar_intervalo(self, remitente: str, texto: str, streak_manager, textos: dict) -> str:
        try:
            dias = int(texto.split(" ")[1])
            if 1 <= dias <= 7:
                streak_manager.cambiar_intervalo(remitente, dias)
                fecha_aviso = datetime.now() + timedelta(days=dias) - timedelta(hours=12)
                
                if fecha_aviso > datetime.now():
                    self.scheduler.add_job(self.send_func, 'date', run_date=fecha_aviso, args=[remitente, "⏰ ¡Tic tac! Tu intervalo acaba en 12h. ¡Haz un /quiz para mantener la racha!"])
                return textos["intervalo_exito"].format(dias=dias)
            return "❌ El intervalo debe ser entre 1 y 7 días."
        except:
            return "❌ Formato incorrecto. Usa: /interval 3"