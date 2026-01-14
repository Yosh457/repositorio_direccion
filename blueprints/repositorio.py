from flask import Blueprint, render_template, send_file, abort
from flask_login import login_required
from models import AreaDocumento, Documento
from io import BytesIO

repositorio_bp = Blueprint('repositorio', __name__, template_folder='../templates')

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

@repositorio_bp.route('/documento/<int:id>/ver')
@login_required
def ver_pdf(id):
    """Streaming del BLOB al navegador"""
    doc = Documento.query.get_or_404(id)
    
    # Validamos que exista data binaria
    if not doc.archivo_data:
        abort(404)
        
    return send_file(
        BytesIO(doc.archivo_data),
        mimetype=doc.mimetype,
        as_attachment=False, 
        download_name=doc.filename
    )

@repositorio_bp.route('/documento/<int:id>/descargar')
@login_required
def descargar_pdf(id):
    """Descarga forzada del BLOB"""
    doc = Documento.query.get_or_404(id)
    if not doc.archivo_data:
        abort(404)

    return send_file(
        BytesIO(doc.archivo_data),
        mimetype=doc.mimetype,
        as_attachment=True,
        download_name=doc.filename
    )