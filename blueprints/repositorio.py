# blueprints/repositorio.py
from flask import Blueprint, render_template, make_response, abort
from flask_login import login_required, current_user
from models import AreaDocumento, Documento, db

# Definimos el Blueprint
repositorio_bp = Blueprint('repositorio', __name__, template_folder='../templates', url_prefix='/repositorio')

@repositorio_bp.route('/panel')
@login_required
def panel():
    """Vista principal: Grid de Áreas (Estilo Estadísticas)"""
    areas = AreaDocumento.query.all()
    return render_template('repositorio/index.html', areas=areas)

@repositorio_bp.route('/area/<int:id>')
@login_required
def ver_area(id):
    """Vista interna: Acordeón con documentos"""
    area = AreaDocumento.query.get_or_404(id)
    return render_template('repositorio/ver_area.html', area=area)

# --- VISUALIZAR PDF (SOLUCIÓN BLINDADA CPANEL) ---
@repositorio_bp.route('/ver_pdf/<int:id>')
@login_required
def ver_pdf(id):
    doc = Documento.query.get_or_404(id)
    
    if not doc.archivo_data:
        abort(404, description="El archivo no tiene contenido.")

    # Usamos make_response en lugar de send_file para evitar error 'fileno' en Passenger
    response = make_response(doc.archivo_data)
    response.headers['Content-Type'] = doc.mimetype
    # 'inline' hace que el navegador intente abrirlo ahí mismo (Vista Previa)
    response.headers['Content-Disposition'] = f'inline; filename="{doc.filename}"'
    
    return response

# --- DESCARGAR PDF (SOLUCIÓN BLINDADA CPANEL) ---
@repositorio_bp.route('/descargar_pdf/<int:id>')
@login_required
def descargar_pdf(id):
    doc = Documento.query.get_or_404(id)
    
    if not doc.archivo_data:
        abort(404, description="El archivo no tiene contenido.")

    # Usamos make_response para forzar la descarga sin usar disco
    response = make_response(doc.archivo_data)
    response.headers['Content-Type'] = doc.mimetype
    # 'attachment' fuerza la descarga automática
    response.headers['Content-Disposition'] = f'attachment; filename="{doc.filename}"'
    
    return response