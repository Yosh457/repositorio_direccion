# models.py (Versión Producción Global)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import deferred
from werkzeug.security import generate_password_hash, check_password_hash
from utils import obtener_hora_chile

db = SQLAlchemy()

# --- MODELO GLOBAL (Solo lectura para Login) ---
class UsuarioGlobal(db.Model):
    __tablename__ = 'usuarios_global'
    __table_args__ = {'schema': 'mahosalu_usuarios_global'} 

    id = db.Column(db.Integer, primary_key=True)
    rut = db.Column(db.String(12))
    nombre_completo = db.Column(db.String(255))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    activo = db.Column(db.Boolean)
    cambio_clave_requerido = db.Column(db.Boolean)
    reset_token = db.Column(db.String(32))
    reset_token_expiracion = db.Column(db.DateTime)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- MODELO LOCAL DE USUARIO (Vinculación) ---
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile)
    
    # Vínculo con la Global
    usuario_global_id = db.Column(db.Integer, nullable=False, unique=True)
    
    # Relación "Virtual" con UsuarioGlobal
    identidad = db.relationship('UsuarioGlobal', 
                                primaryjoin='Usuario.usuario_global_id == UsuarioGlobal.id',
                                foreign_keys='Usuario.usuario_global_id',
                                uselist=False, viewonly=True)

    # Relaciones locales
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    rol = db.relationship('Rol', back_populates='usuarios')

    # PROXIES
    @property
    def nombre_completo(self):
        return self.identidad.nombre_completo if self.identidad else "Usuario Desconocido"
    
    @property
    def email(self):
        return self.identidad.email if self.identidad else ""
    
    @property
    def cambio_clave_requerido(self):
        return self.identidad.cambio_clave_requerido if self.identidad else False

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol')

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=obtener_hora_chile) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(255))
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text)
    
    # Relación opcional para acceder al objeto usuario desde el log
    usuario = db.relationship('Usuario', backref=db.backref('logs', lazy=True))

# --- MODELOS DE REPOSITORIO (Negocio) ---

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
    version = db.Column(db.String(50), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100), default='application/pdf')
    
    size_bytes = db.Column(db.BigInteger, nullable=True) 
    sha256 = db.Column(db.String(64), nullable=True)   
    
    archivo_data = deferred(db.Column(db.LargeBinary(length=(2**32)-1)))
    
    fecha_subida = db.Column(db.DateTime, default=obtener_hora_chile, index=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas_documentos.id'), nullable=False, index=True)
    
    area = db.relationship('AreaDocumento', back_populates='documentos')