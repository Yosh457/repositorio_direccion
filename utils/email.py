def enviar_correo_reseteo(usuario, token):
    """
    Simula el envío de un correo electrónico imprimiendo en consola.
    En producción, aquí iría la configuración SMTP.
    """
    print(f"\n========================================")
    print(f"📧 SIMULACIÓN DE ENVÍO DE CORREO")
    print(f"----------------------------------------")
    print(f"Para:  {usuario.email}")
    print(f"Asunto: Recuperación de Contraseña - Repositorio Dirección")
    print(f"Mensaje: Hola {usuario.nombre_completo}, usa este enlace para recuperar tu clave:")
    print(f"Link:  http://127.0.0.1:5000/resetear-clave/{token}")
    print(f"========================================\n")