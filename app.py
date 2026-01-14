import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from extensions import login_manager, csrf
from models import db, Usuario

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # --- CONFIGURACIÓN ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    
    db_pass = os.getenv('MYSQL_PASSWORD')
    db_name = 'repositorio_direccion_db'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{db_pass}@localhost/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Límite de subida (Ajustado para PDFs grandes, ej: 32MB)
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

    # --- INICIALIZACIÓN ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Acceso restringido al Repositorio de Dirección.'
    login_manager.login_message_category = 'warning'

    # --- REGISTRO DE BLUEPRINTS ---
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    # from blueprints.admin import admin_bp
    # app.register_blueprint(admin_bp)
    
    from blueprints.repositorio import repositorio_bp
    app.register_blueprint(repositorio_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login')) # Asumiendo que auth existirá pronto

    return app

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Esto crea las tablas según el modelo definido si no existen
        db.create_all()
        print("Sistema inicializado. Tablas verificadas.")
    app.run(debug=True)