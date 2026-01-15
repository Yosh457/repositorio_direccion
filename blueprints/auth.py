# blueprints/auth.py
import secrets
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

# Importamos modelos (Global y Local)
from models import db, Usuario, Rol, UsuarioGlobal
from utils import registrar_log, enviar_correo_reseteo, es_password_segura

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def obtener_ruta_redireccion(usuario):
    if not usuario.rol:
        return url_for('auth.login')
    
    if usuario.rol.nombre == 'Admin':
        return url_for('admin.panel')
    
    # Director y Visualizador van al Repositorio
    return url_for('repositorio.panel')

# --- RUTAS DE AUTENTICACIÓN ---

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. BUSCAR EN LA BD GLOBAL (Autenticación)
        identidad_global = UsuarioGlobal.query.filter_by(email=email).first()

        if identidad_global and identidad_global.check_password(password):
            # 2. BUSCAR EN BD LOCAL (Autorización)
            usuario_local = Usuario.query.filter_by(usuario_global_id=identidad_global.id).first()
            
            if usuario_local and usuario_local.activo and identidad_global.activo:
                login_user(usuario_local)
                
                # Usamos el nombre del proxy
                registrar_log("Inicio de Sesión", f"Usuario {usuario_local.nombre_completo} inició sesión.")

                if identidad_global.cambio_clave_requerido:
                    flash('Por seguridad, debes cambiar tu contraseña ahora.', 'warning')
                    return redirect(url_for('auth.cambiar_clave'))
                
                flash(f'Bienvenido, {usuario_local.nombre_completo}', 'success')
                return redirect(obtener_ruta_redireccion(usuario_local))
            else:
                flash('Credenciales correctas, pero no tienes permisos para este sistema.', 'warning')
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    registrar_log("Cierre de Sesión", f"Usuario {current_user.nombre_completo} cerró sesión.")
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    # ... Lógica Global Idéntica a Inventario ...
    if request.method == 'POST':
        password_nueva = request.form.get('nueva_password')
        password_confirmar = request.form.get('confirmar_password')

        if password_nueva != password_confirmar:
            flash('Las nuevas contraseñas no coinciden.', 'warning')
            return render_template('auth/cambiar_clave.html')

        if not es_password_segura(password_nueva):
            flash('La contraseña no cumple los requisitos de seguridad.', 'warning')
            return render_template('auth/cambiar_clave.html')

        try:
            usuario_global = current_user.identidad
            usuario_global.password_hash = generate_password_hash(password_nueva)
            usuario_global.cambio_clave_requerido = False 
            db.session.commit()
            
            registrar_log("Cambio de Clave", f"Usuario {current_user.nombre_completo} cambió su clave.")
            logout_user()
            flash('Contraseña actualizada. Inicia sesión de nuevo.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            flash('Ocurrió un error al actualizar.', 'danger')

    return render_template('auth/cambiar_clave.html')

@auth_bp.route('/solicitar-reseteo', methods=['GET', 'POST'])
def solicitar_reseteo():
    # ... Lógica Global Idéntica a Inventario ...
    if request.method == 'POST':
        email = request.form.get('email')
        usuario_global = UsuarioGlobal.query.filter_by(email=email).first()
        
        if usuario_global:
            token = secrets.token_hex(16)
            usuario_global.reset_token = token
            usuario_global.reset_token_expiracion = datetime.now() + timedelta(hours=1)
            db.session.commit()
            
            enviar_correo_reseteo(usuario_global, token)
            flash(f'Se ha enviado un enlace a {email}.', 'success')
        else:
            flash(f'El correo {email} no se encuentra registrado.', 'danger')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/solicitar_reseteo.html')

@auth_bp.route('/resetear-clave/<token>', methods=['GET', 'POST'])
def resetear_clave(token):
    # ... Lógica Global Idéntica a Inventario ...
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    usuario_global = UsuarioGlobal.query.filter_by(reset_token=token).first()
    
    if not usuario_global or not usuario_global.reset_token_expiracion or usuario_global.reset_token_expiracion < datetime.now():
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.solicitar_reseteo'))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        confirmar = request.form.get('confirmar_password')

        if nueva_password != confirmar:
             flash('Las contraseñas no coinciden.', 'warning')
             return render_template('auth/resetear_clave.html', token=token)

        if not es_password_segura(nueva_password):
            flash('La contraseña no cumple los requisitos.', 'danger')
            return render_template('auth/resetear_clave.html', token=token)
        
        try:
            usuario_global.password_hash = generate_password_hash(nueva_password)
            usuario_global.reset_token = None
            usuario_global.reset_token_expiracion = None
            usuario_global.cambio_clave_requerido = False
            db.session.commit()
            
            flash('Tu contraseña ha sido restablecida.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al restablecer contraseña.', 'danger')
        
    return render_template('auth/resetear_clave.html')