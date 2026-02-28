from WhatsAppComms import WhatsAppComms

motor = WhatsAppComms()



if __name__ == "__main__":
    
    # 1. Conexión con Twilio
    motor.configurar_twilio(
        account_sid="ACCOUNT_SID_AQUI",
        auth_token="AUTH_TOKEN_AQUI",
        numero_twilio="whatsapp:+14155238886"
    )
    
    # 2. Inyectar rutas y tareas
    motor.configurar_recepcion()

    # Lista de tuplas con tarea y hora. Ej: (generar_resumen_diario, "20:00")
    motor.configurar_tareas()
    
    # 3. Arrancae el motor local
    motor.iniciar(puerto=8000)