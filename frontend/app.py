import os
from flask import Flask, send_from_directory, render_template
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory(STATIC_DIR, path)

@app.route('/<path:filename>')
def send_root(filename):
    # Serve files that remain at project root (legacy)
    root_dir = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
    return send_from_directory(root_dir, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
