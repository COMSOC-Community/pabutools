# pip install python-dotenv
import dotenv, os
dotenv.load_dotenv()
SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32))

from flask import Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

from flask_example import routes
