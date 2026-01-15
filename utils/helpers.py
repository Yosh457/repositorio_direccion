from flask_login import current_user
from datetime import datetime
import pytz
import re

# BORRA O COMENTA ESTA LÍNEA DE ARRIBA:
# from models import db, Log  <-- ESTO CAUSA EL ERROR

def obtener_hora_chile():
    cl_tz = pytz.timezone('America/Santiago')
    return datetime.now(cl_tz)

def registrar_log(accion, detalles=None):
    """Registra una acción en la base de datos."""
    
    # --- IMPORTACIÓN DIFERIDA (LA SOLUCIÓN) ---
    # Importamos aquí dentro para evitar el ciclo con models.py
    from models import db, Log 
    # ------------------------------------------

    try:
        # Verificamos si hay usuario logueado de forma segura
        # (A veces current_user puede no estar disponible en ciertos contextos)
        if current_user and current_user.is_authenticated:
            usuario_id = current_user.id
            # Usamos el proxy nombre_completo que definimos en el modelo
            usuario_nombre = current_user.nombre_completo 
        else:
            usuario_id = None
            usuario_nombre = 'Sistema/Anónimo'
        
        nuevo_log = Log(
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            accion=accion,
            detalles=detalles,
            timestamp=obtener_hora_chile()
        )
        db.session.add(nuevo_log)
        db.session.commit()
    except Exception as e:
        # En producción es mejor imprimir al log de errores del servidor
        print(f"Error al registrar log: {e}")

# --- AGREGAR ESTA FUNCIÓN AL FINAL ---
def es_password_segura(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[0-9]", password): return False
    return True