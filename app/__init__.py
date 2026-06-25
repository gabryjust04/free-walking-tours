import os
from flask import Flask
from dotenv import load_dotenv
from app.core import db
from app.core.login_manager import login_manager
from app.auth.routes import auth_bp
from pathlib import Path
from app.public.routes import public_bp
from app.guide_dashboard.routes import guide_dashboard_bp
from app.admin.routes import admin_bp
BASE_DIR = Path(__file__).resolve().parent.parent # Base directory


def create_app():
    # Load variables from the .env file
    load_dotenv()
    
    # Create the app object
    app = Flask(__name__)
    

    # Configuration

    database_path = os.getenv("DATABASE_PATH")
    database_path = Path(database_path)
    
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-super-secret'),
        DATABASE=str(database_path)
    )
    
    db.init_app(app)
    login_manager.init_app(app)
    

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(guide_dashboard_bp)


    app.register_blueprint(admin_bp)

   
    
    return app
