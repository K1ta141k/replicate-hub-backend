import os
from flask import Flask, request, send_from_directory, jsonify, session, redirect, url_for, abort
from werkzeug.utils import secure_filename
from flask_cors import CORS
import zipfile

app = Flask(__name__)
# Use a fixed secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'piskachort')
CORS(app, supports_credentials=True)

# Set the root directory for file management
ROOT_DIR = os.path.abspath("/home/ali")

# Security settings
PIN_CODE = os.environ.get('FILE_MANAGER_PIN', '1234')  # Default PIN is 1234, can be set via environment variable

# Authentication decorator
def require_auth(f):
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Helpers
def get_abs_path(rel_path):
    safe_path = os.path.normpath(os.path.join(ROOT_DIR, rel_path.strip('/')))
    if not safe_path.startswith(ROOT_DIR):
        raise ValueError('Invalid path')
    return safe_path

def get_file_info(path, name):
    full_path = os.path.join(path, name)
    stat = os.stat(full_path)
    size = stat.st_size
    ext = os.path.splitext(name)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        ftype = 'image'
    elif ext in ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx']:
        ftype = 'document'
    elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
        ftype = 'video'
    elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
        ftype = 'audio'
    elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
        ftype = 'archive'
    else:
        ftype = 'default'
    return {
        'name': name,
        'size': sizeof_fmt(size),
        'type': ftype,
        'modified': str(stat.st_mtime)
    }

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)

def is_text_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.txt', '.md', '.py', '.js', '.json', '.html', '.css', '.csv', '.log', '.xml', '.yml', '.yaml', '.ini', '.conf']

# Authentication endpoints
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    pin = data.get('pin')
    if pin == PIN_CODE:
        session['authenticated'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Invalid PIN'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'authenticated': session.get('authenticated', False)})

# Serve the main page
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# Protected API Endpoints
@app.route('/api/list', methods=['GET'])
@require_auth
def list_files():
    rel_path = request.args.get('path', '/')
    abs_path = get_abs_path(rel_path)
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path does not exist'}), 404
    files = []
    folders = []
    for entry in os.listdir(abs_path):
        full_entry = os.path.join(abs_path, entry)
        if os.path.isdir(full_entry):
            folders.append({'name': entry, 'path': os.path.join(rel_path, entry).replace('\\', '/')})
        else:
            files.append(get_file_info(abs_path, entry))
    return jsonify({'files': files, 'folders': folders})

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    rel_path = request.form.get('path', '/')
    abs_path = get_abs_path(rel_path)
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(abs_path, filename))
    return jsonify({'success': True})

@app.route('/api/download', methods=['GET'])
@require_auth
def download_file():
    rel_path = request.args.get('path', '/')
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path):
        return jsonify({'error': 'File not found'}), 404
    dir_name = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    return send_from_directory(dir_name, file_name, as_attachment=True)

@app.route('/api/rename', methods=['POST'])
@require_auth
def rename_file():
    data = request.json
    rel_path = data.get('path')
    new_name = data.get('newName')
    abs_path = get_abs_path(rel_path)
    new_abs_path = os.path.join(os.path.dirname(abs_path), secure_filename(new_name))
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File/folder not found'}), 404
    os.rename(abs_path, new_abs_path)
    return jsonify({'success': True})

@app.route('/api/delete', methods=['POST'])
@require_auth
def delete_file():
    data = request.json
    rel_path = data.get('path')
    abs_path = get_abs_path(rel_path)
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File/folder not found'}), 404
    if os.path.isdir(abs_path):
        try:
            os.rmdir(abs_path)
        except OSError:
            return jsonify({'error': 'Directory not empty'}), 400
    else:
        os.remove(abs_path)
    return jsonify({'success': True})

@app.route('/api/read', methods=['GET'])
@require_auth
def read_file():
    rel_path = request.args.get('path')
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path):
        return jsonify({'error': 'File not found'}), 404
    if not is_text_file(abs_path):
        return jsonify({'error': 'Not a text file'}), 400
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save', methods=['POST'])
@require_auth
def save_file():
    data = request.json
    rel_path = data.get('path')
    content = data.get('content')
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path):
        return jsonify({'error': 'File not found'}), 404
    if not is_text_file(abs_path):
        return jsonify({'error': 'Not a text file'}), 400
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unzip', methods=['POST'])
@require_auth
def unzip_file():
    data = request.json
    rel_path = data.get('path')
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path) or not abs_path.lower().endswith('.zip'):
        return jsonify({'error': 'Not a zip file'}), 400
    try:
        extract_dir = abs_path + '_unzipped'
        with zipfile.ZipFile(abs_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return jsonify({'success': True, 'extracted_to': extract_dir})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
