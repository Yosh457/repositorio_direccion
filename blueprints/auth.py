# blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import pytz
import secrets
import re

from models import db, Usuario
from utils import registrar_log, enviar_correo_reseteo

# Definimos el Blueprint
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

# --- VALIDACIONES LOCALES ---
def es_password_segura(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[0-9]", password): return False
    return True

def obtener_ruta_redireccion(usuario):
    """Define a dónde va el usuario después de loguearse según su Rol."""
    if not usuario.rol:
        return url_for('auth.login')
    
    # LÓGICA CORREGIDA:
    # Si es Admin, va al Panel de Administración
    if usuario.rol.nombre == 'Admin':
        return url_for('admin.panel')
    
    # Director, Visualizador (y cualquier otro) van al Repositorio
    return url_for('repositorio.panel')

# --- RUTAS DE AUTENTICACIÓN ---

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            if not usuario.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            if usuario.check_password(password):
                login_user(usuario)
                registrar_log("Inicio de Sesión", f"Usuario {usuario.nombre_completo} accedió.")

                if usuario.cambio_clave_requerido:
                    return redirect(url_for('auth.cambiar_clave'))
                
                flash(f'Bienvenido, {usuario.nombre_completo}', 'success')
                return redirect(obtener_ruta_redireccion(usuario))
        
        flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    registrar_log("Cierre de Sesión", "Usuario salió del sistema.")
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    if not current_user.cambio_clave_requerido:
        return redirect(obtener_ruta_redireccion(current_user))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')

        if not es_password_segura(nueva_password):
            flash('Error: La contraseña debe tener 8 caracteres, mayúscula y número.', 'danger')
        else:
            current_user.set_password(nueva_password)
            current_user.cambio_clave_requerido = False
            db.session.commit()
            
            registrar_log("Cambio de Clave", "Usuario actualizó su contraseña obligatoria.")
            logout_user()
            flash('Contraseña actualizada. Ingresa nuevamente.', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/cambiar_clave.html')

@auth_bp.route('/solicitar-reseteo', methods=['GET', 'POST'])
def solicitar_reseteo():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            token = secrets.token_hex(16)
            cl_tz = pytz.timezone('America/Santiago')
            expiracion = datetime.now(cl_tz).replace(tzinfo=None) + timedelta(hours=1)
            
            usuario.reset_token = token
            usuario.reset_token_expiracion = expiracion
            db.session.commit()
            
            enviar_correo_reseteo(usuario, token)
            flash(f'Se ha enviado un enlace a {email}.', 'success')
        else:
            flash(f'El correo {email} no está registrado.', 'danger')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/solicitar_reseteo.html')

@auth_bp.route('/resetear-clave/<token>', methods=['GET', 'POST'])
def resetear_clave(token):
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    usuario = Usuario.query.filter_by(reset_token=token).first()
    cl_tz = pytz.timezone('America/Santiago')
    ahora = datetime.now(cl_tz).replace(tzinfo=None)
    
    if not usuario or not usuario.reset_token_expiracion or usuario.reset_token_expiracion < ahora:
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.solicitar_reseteo'))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')

        if not es_password_segura(nueva_password):
            flash('Error: Requisitos de seguridad no cumplidos.', 'danger')
        else:
            usuario.set_password(nueva_password)
            usuario.reset_token = None
            usuario.reset_token_expiracion = None
            db.session.commit()
            
            registrar_log("Recuperación Clave", f"Usuario {usuario.email} recuperó su clave.")
            flash('Tu contraseña ha sido restablecida. Inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
        
    return render_template('auth/resetear_clave.html')