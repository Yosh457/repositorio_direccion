from datetime import datetime
import pytz
from flask_login import current_user
from models import db, Log

def obtener_hora_chile():
    cl_tz = pytz.timezone('America/Santiago')
    return datetime.now(cl_tz)

def registrar_log(accion, detalles=None):
    """Registra una acción en la base de datos."""
    try:
        usuario_id = current_user.id if current_user.is_authenticated else None
        usuario_nombre = current_user.nombre_completo if current_user.is_authenticated else 'Sistema/Anónimo'
        
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
        print(f"Error al registrar log: {e}")