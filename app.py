# app.py  (REPOSITORIO DIRECCIÓN – VERSIÓN BLINDADA PARA CPANEL PASSENGER)

import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, flash
from flask_wtf.csrf import CSRFError

from extensions import login_manager, csrf
from models import db, Usuario

# ----------------------------------------------------
# CARGA DE ENTORNO (una sola vez)
# ----------------------------------------------------
load_dotenv()

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')

# ----------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# 🔐 Base de Datos (Producción cPanel)
db_user = os.getenv('DB_USER', 'mahosalu_repositorio_sstt')
db_password = os.getenv('DB_PASSWORD')  # <-- recomendado en .env
db_name = os.getenv('DB_NAME', 'mahosalu_repositorio_direccion_db')
db_host = os.getenv('DB_HOST', 'localhost')

# ⚠️ Si DB_PASSWORD viene vacío, mejor fallar rápido
if not db_password:
    raise ValueError("❌ Falta DB_PASSWORD en el archivo .env")

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🛡️ CRÍTICO PARA CPANEL: Pool controlado (evita saturación de conexiones)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 280,
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 2
}

# 📦 Límite de subida (PDFs grandes, ej: 32MB)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# ----------------------------------------------------
# EXTENSIONES
# ----------------------------------------------------
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Acceso restringido al Repositorio de Dirección.'
login_manager.login_message_category = 'warning'

# ----------------------------------------------------
# BLUEPRINTS (una sola vez)
# ----------------------------------------------------
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.repositorio import repositorio_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(repositorio_bp)

# ----------------------------------------------------
# RUTAS
# ----------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

# ----------------------------------------------------
# ERRORES
# ----------------------------------------------------
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('La sesión expiró. Intenta enviar el formulario de nuevo.', 'warning')
    return redirect(url_for('auth.login'))

@app.after_request
def add_header(response):
    # 🛡️ Evita problemas con botón "atrás" después del logout
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ----------------------------------------------------
# USER LOADER
# ----------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ----------------------------------------------------
# PUNTO DE ENTRADA LOCAL (solo desarrollo)
# ----------------------------------------------------
if __name__ == '__main__':
    # ⚠️ IMPORTANTE:
    # En producción (cPanel Passenger) NO se debe ejecutar db.create_all()
    # porque Passenger puede levantar múltiples workers y repetirlo.
    #
    # Si necesitas crear tablas, hazlo manual o con un script aparte.
    app.run(debug=False)
