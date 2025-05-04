from flask import Flask
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello from Flask on Vercel!"

asgi_app = WsgiToAsgi(app)
