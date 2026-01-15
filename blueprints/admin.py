# blueprints/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import hashlib

# Modelos
from models import db, Usuario, Rol, Log, UsuarioGlobal, AreaDocumento, Documento
# Utilidades
from utils import registrar_log, admin_required

# Definimos el blueprint
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

# ==========================================
#  SECCIÓN 1: PANEL Y USUARIOS (ESTÁNDAR)
# ==========================================

@admin_bp.route('/panel')
@login_required
@admin_required
def panel():
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '')
    rol_filtro = request.args.get('rol_filtro', '')
    estado_filtro = request.args.get('estado_filtro', '')

    # JOIN CON GLOBAL PARA BÚSQUEDA
    query = Usuario.query.join(Usuario.identidad)

    if busqueda:
        query = query.filter(
            or_(
                UsuarioGlobal.nombre_completo.ilike(f'%{busqueda}%'),
                UsuarioGlobal.email.ilike(f'%{busqueda}%')
            )
        )
    
    if rol_filtro:
        query = query.filter(Usuario.rol_id == rol_filtro)

    if estado_filtro == 'activo':
        query = query.filter(Usuario.activo == True)
    elif estado_filtro == 'inactivo':
        query = query.filter(Usuario.activo == False)
    
    pagination = query.order_by(UsuarioGlobal.nombre_completo).paginate(page=page, per_page=10, error_out=False)
    roles_para_filtro = Rol.query.order_by(Rol.nombre).all()

    return render_template('admin/panel.html', 
                           pagination=pagination,
                           roles_para_filtro=roles_para_filtro,
                           busqueda=busqueda,
                           rol_filtro=rol_filtro,
                           estado_filtro=estado_filtro)

# --- VINCULAR USUARIO (NUEVA LÓGICA) ---
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    roles = Rol.query.order_by(Rol.nombre).all()

    if request.method == 'POST':
        usuario_global_id = request.form.get('usuario_global_id')
        rol_id = request.form.get('rol_id')

        if not usuario_global_id or not rol_id:
            flash('Debes seleccionar un funcionario y un rol.', 'danger')
            return redirect(url_for('admin.crear_usuario'))

        if Usuario.query.filter_by(usuario_global_id=usuario_global_id).first():
            flash('Este funcionario ya tiene acceso.', 'warning')
            return redirect(url_for('admin.crear_usuario'))

        nuevo_usuario_local = Usuario(
            usuario_global_id=usuario_global_id,
            rol_id=rol_id,
            activo=True
        )
        
        try:
            db.session.add(nuevo_usuario_local)
            db.session.commit()
            
            usr_glob = UsuarioGlobal.query.get(usuario_global_id)
            nombre_log = usr_glob.nombre_completo if usr_glob else "ID " + str(usuario_global_id)
            
            registrar_log("Vinculación Usuario", f"Admin otorgó acceso a {nombre_log}")
            flash('Funcionario vinculado exitosamente.', 'success')
            return redirect(url_for('admin.panel'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al vincular: {str(e)}', 'danger')

    # Buscar usuarios globales disponibles (que no estén vinculados)
    ids_locales = db.session.query(Usuario.usuario_global_id).all()
    ids_locales_lista = [id[0] for id in ids_locales]

    if ids_locales_lista:
        usuarios_disponibles = UsuarioGlobal.query.filter(
            UsuarioGlobal.id.notin_(ids_locales_lista),
            UsuarioGlobal.activo == True
        ).order_by(UsuarioGlobal.nombre_completo).all()
    else:
        usuarios_disponibles = UsuarioGlobal.query.filter_by(activo=True).order_by(UsuarioGlobal.nombre_completo).all()

    return render_template('admin/crear_usuario.html', roles=roles, usuarios_disponibles=usuarios_disponibles)

# --- EDITAR PERMISOS ---
@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    usuario_local = Usuario.query.get_or_404(id)
    roles = Rol.query.order_by(Rol.nombre).all()

    if request.method == 'POST':
        # Solo editamos Rol localmente
        nuevo_rol_id = request.form.get('rol_id')
        if nuevo_rol_id:
            usuario_local.rol_id = nuevo_rol_id
            db.session.commit()
            registrar_log("Edición Permisos", f"Admin cambió rol de {usuario_local.nombre_completo}")
            flash('Permisos actualizados.', 'success')
            return redirect(url_for('admin.panel'))

    return render_template('admin/editar_usuario.html', usuario=usuario_local, roles=roles)

# --- TOGGLE ACTIVO ---
@admin_bp.route('/toggle_activo/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_activo(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes desactivarte a ti mismo.', 'danger')
        return redirect(url_for('admin.panel'))
        
    usuario.activo = not usuario.activo
    db.session.commit()
    estado = "activado" if usuario.activo else "desactivado"
    registrar_log("Cambio Estado", f"Usuario {usuario.nombre_completo} fue {estado}.")
    flash(f'Usuario {usuario.nombre_completo} {estado}.', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/ver_logs')
@login_required
@admin_required
def ver_logs():
    page = request.args.get('page', 1, type=int)
    usuario_filtro = request.args.get('usuario_id')
    accion_filtro = request.args.get('accion')

    query = Log.query.order_by(Log.timestamp.desc())

    if usuario_filtro and usuario_filtro.isdigit():
        query = query.filter(Log.usuario_id == int(usuario_filtro))
    if accion_filtro:
        query = query.filter(Log.accion == accion_filtro)

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    todos_los_usuarios = Usuario.query.join(Usuario.identidad).order_by(UsuarioGlobal.nombre_completo).all()
    acciones_posibles = ["Inicio de Sesión", "Cierre de Sesión", "Vinculación Usuario", 
                         "Edición Permisos", "Cambio Estado", "Cambio de Clave", 
                         "Recuperación Clave", "Gestión Documental"]

    return render_template('admin/ver_logs.html', pagination=pagination,
                           todos_los_usuarios=todos_los_usuarios,
                           acciones_posibles=acciones_posibles,
                           filtros={'usuario_id': usuario_filtro, 'accion': accion_filtro})

# ==========================================
#  SECCIÓN 2: GESTIÓN DOCUMENTAL (NUEVO)
# ==========================================

@admin_bp.route('/areas')
@login_required
@admin_required
def gestion_areas():
    """Listado de Áreas documentales."""
    areas = AreaDocumento.query.all()
    return render_template('admin/gestion_areas.html', areas=areas)

@admin_bp.route('/area/crear', methods=['POST'])
@login_required
@admin_required
def crear_area():
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    
    if nombre:
        nueva_area = AreaDocumento(nombre=nombre, descripcion=descripcion)
        db.session.add(nueva_area)
        db.session.commit()
        registrar_log("Gestión Documental", f"Área creada: {nombre}")
        flash('Área creada exitosamente.', 'success')
    else:
        flash('El nombre del área es obligatorio.', 'danger')
        
    return redirect(url_for('admin.gestion_areas'))

@admin_bp.route('/area/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_area(id):
    area = AreaDocumento.query.get_or_404(id)
    nombre = area.nombre
    # SQLAlchemy con cascade="all, delete-orphan" eliminará los documentos asociados automáticamente
    db.session.delete(area)
    db.session.commit()
    registrar_log("Gestión Documental", f"Área eliminada: {nombre} y sus documentos.")
    flash('Área eliminada correctamente.', 'success')
    return redirect(url_for('admin.gestion_areas'))

@admin_bp.route('/area/<int:id>/documentos', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar_documentos(id):
    """Vista para subir y listar documentos de un área específica."""
    area = AreaDocumento.query.get_or_404(id)
    
    # SUBIDA DE ARCHIVO
    if request.method == 'POST':
        archivo = request.files.get('archivo')
        titulo = request.form.get('titulo')
        version = request.form.get('version')
        
        if archivo and titulo:
            if archivo.filename == '':
                flash('No se seleccionó ningún archivo.', 'warning')
            elif not archivo.filename.lower().endswith('.pdf'):
                flash('Solo se permiten archivos PDF.', 'danger')
            else:
                try:
                    # 1. Leer datos binarios
                    data = archivo.read()
                    filename = secure_filename(archivo.filename)
                    size = len(data)
                    sha256 = hashlib.sha256(data).hexdigest()
                    
                    # 2. Crear registro
                    nuevo_doc = Documento(
                        titulo=titulo,
                        version=version,
                        descripcion=request.form.get('descripcion'),
                        filename=filename,
                        mimetype='application/pdf',
                        archivo_data=data, # BLOB
                        size_bytes=size,
                        sha256=sha256,
                        area_id=area.id
                    )
                    
                    db.session.add(nuevo_doc)
                    db.session.commit()
                    registrar_log("Gestión Documental", f"Documento subido: {titulo} en {area.nombre}")
                    flash('Documento subido exitosamente.', 'success')
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al subir archivo: {str(e)}', 'danger')
                    print(e)
                    
        return redirect(url_for('admin.gestionar_documentos', id=area.id))
        
    return render_template('admin/gestionar_documentos.html', area=area)

@admin_bp.route('/documento/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_documento(id):
    doc = Documento.query.get_or_404(id)
    area_id = doc.area_id
    titulo = doc.titulo
    
    db.session.delete(doc)
    db.session.commit()
    
    registrar_log("Gestión Documental", f"Documento eliminado: {titulo}")
    flash('Documento eliminado correctamente.', 'success')
    return redirect(url_for('admin.gestionar_documentos', id=area_id))

@admin_bp.route('/area/editar/<int:id>', methods=['POST'])
@login_required
@admin_required
def editar_area(id):
    area = AreaDocumento.query.get_or_404(id)
    nombre = request.form.get('nombre')
    
    if nombre:
        area.nombre = nombre
        area.descripcion = request.form.get('descripcion')
        db.session.commit()
        registrar_log("Gestión Documental", f"Área editada: {nombre}")
        flash('Área actualizada correctamente.', 'success')
    else:
        flash('El nombre no puede estar vacío.', 'warning')
        
    return redirect(url_for('admin.gestion_areas'))

@admin_bp.route('/documento/editar/<int:id>', methods=['POST'])
@login_required
@admin_required
def editar_documento(id):
    doc = Documento.query.get_or_404(id)
    titulo = request.form.get('titulo')
    
    if titulo:
        doc.titulo = titulo
        doc.version = request.form.get('version')
        doc.descripcion = request.form.get('descripcion')
        
        # Verificar si subieron un archivo nuevo para reemplazar el anterior
        archivo = request.files.get('archivo')
        if archivo and archivo.filename != '':
            if archivo.filename.lower().endswith('.pdf'):
                try:
                    data = archivo.read()
                    doc.filename = secure_filename(archivo.filename)
                    doc.archivo_data = data
                    doc.size_bytes = len(data)
                    doc.sha256 = hashlib.sha256(data).hexdigest()
                    flash('Documento y archivo actualizados.', 'success')
                except Exception as e:
                    flash(f'Error al procesar el nuevo archivo: {e}', 'danger')
            else:
                flash('El archivo nuevo debe ser PDF. Se actualizaron solo los textos.', 'warning')
        else:
            flash('Datos del documento actualizados (archivo mantenido).', 'success')

        db.session.commit()
        registrar_log("Gestión Documental", f"Documento editado: {titulo}")
    else:
        flash('El título es obligatorio.', 'warning')
        
    return redirect(url_for('admin.gestionar_documentos', id=doc.area_id))