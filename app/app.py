import os
from flask import Flask
from flask_session import Session

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'BakeStoreSecretKey')
    app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'filesystem')
    
    session_dir = os.path.join(os.path.dirname(__file__), 'flask_session')
    os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_FILE_DIR'] = session_dir
    
    Session(app)
    return app

app = create_app()

from . import routes
