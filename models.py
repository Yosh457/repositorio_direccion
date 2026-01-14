from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import deferred
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

def obtener_hora_chile():
    cl_tz = pytz.timezone('America/Santiago')
    return datetime.now(cl_tz)

# --- USUARIOS Y ROLES ---

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol')

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile)
    
    cambio_clave_requerido = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(32), nullable=True)
    reset_token_expiracion = db.Column(db.DateTime, nullable=True)

    # Índice agregado explícitamente en la FK (aunque MySQL suele hacerlo, es buena práctica en ORM)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True)
    rol = db.relationship('Rol', back_populates='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=obtener_hora_chile, index=True) 
    
    # Índice agregado
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)
    usuario_nombre = db.Column(db.String(255))
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text)

# --- REPOSITORIO DOCUMENTAL ---

class AreaDocumento(db.Model):
    __tablename__ = 'areas_documentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    icono = db.Column(db.String(100), default='folder') 
    
    documentos = db.relationship('Documento', back_populates='area', cascade="all, delete-orphan")

class Documento(db.Model):
    __tablename__ = 'documentos'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100), default='application/pdf')
    
    # Metadatos solicitados
    size_bytes = db.Column(db.BigInteger, nullable=True) 
    sha256 = db.Column(db.String(64), nullable=True)   
    
    # BLOB diferido
    archivo_data = deferred(db.Column(db.LargeBinary(length=(2**32)-1)))
    
    # Índices solicitados
    fecha_subida = db.Column(db.DateTime, default=obtener_hora_chile, index=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas_documentos.id'), nullable=False, index=True)
    
    area = db.relationship('AreaDocumento', back_populates='documentos')