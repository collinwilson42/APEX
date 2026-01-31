"""
FLASK API ENDPOINTS - PROFILE MANAGEMENT FILE SYSTEM (V1.1-1.6)
Add these routes to flask_app_sqlite.py
"""

import os
import json
from datetime import datetime
from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename

# ============================================================================
# FOLDER STRUCTURE SETUP
# ============================================================================

# Define folder paths
PROFILE_FOLDERS = {
    'profiles': 'profiles',
    'inputs': 'inputs',
    'prompts': 'prompts',
    'skills': 'skills'
}

def ensure_folders_exist():
    """Create profile management folders if they don't exist"""
    for folder in PROFILE_FOLDERS.values():
        os.makedirs(folder, exist_ok=True)
    print("[PROFILE MANAGEMENT] Folders initialized")

# Call on app startup
ensure_folders_exist()

# ============================================================================
# FILE COUNT ENDPOINT
# ============================================================================

@app.route('/api/files/counts', methods=['GET'])
def get_file_counts():
    """Get file counts for all folders"""
    try:
        counts = {}
        for key, folder in PROFILE_FOLDERS.items():
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
                counts[key] = len(files)
            else:
                counts[key] = 0
        
        return jsonify(counts)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FILE LISTING ENDPOINT
# ============================================================================

@app.route('/api/files/list', methods=['GET'])
def list_files():
    """List all files in a specific folder"""
    try:
        folder_key = request.args.get('folder', 'profiles')
        
        if folder_key not in PROFILE_FOLDERS:
            return jsonify({'error': 'Invalid folder'}), 400
        
        folder_path = PROFILE_FOLDERS[folder_key]
        
        if not os.path.exists(folder_path):
            return jsonify({'files': []})
        
        files = []
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'folder': folder_key
                })
        
        # Sort by modified date (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'files': files, 'count': len(files)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FILE CONTENT ENDPOINT
# ============================================================================

@app.route('/api/files/content', methods=['GET'])
def get_file_content():
    """Get content of a specific file"""
    try:
        folder_key = request.args.get('folder')
        filename = request.args.get('file')
        
        if not folder_key or not filename:
            return jsonify({'error': 'Missing parameters'}), 400
        
        if folder_key not in PROFILE_FOLDERS:
            return jsonify({'error': 'Invalid folder'}), 400
        
        # Security: Prevent directory traversal
        filename = secure_filename(filename)
        filepath = os.path.join(PROFILE_FOLDERS[folder_key], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine file type
        ext = os.path.splitext(filename)[1].lower()
        content_type = 'text'
        if ext in ['.json']:
            content_type = 'json'
            try:
                content = json.loads(content)
            except:
                pass
        elif ext in ['.py']:
            content_type = 'python'
        
        return jsonify({
            'filename': filename,
            'folder': folder_key,
            'content': content,
            'type': content_type,
            'size': os.path.getsize(filepath),
            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FILE SAVE ENDPOINT
# ============================================================================

@app.route('/api/files/save', methods=['POST'])
def save_file():
    """Save or update a file"""
    try:
        data = request.json
        folder_key = data.get('folder')
        filename = data.get('filename')
        content = data.get('content')
        
        if not all([folder_key, filename, content]):
            return jsonify({'error': 'Missing parameters'}), 400
        
        if folder_key not in PROFILE_FOLDERS:
            return jsonify({'error': 'Invalid folder'}), 400
        
        # Security: Prevent directory traversal
        filename = secure_filename(filename)
        filepath = os.path.join(PROFILE_FOLDERS[folder_key], filename)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(content, dict):
                json.dump(content, f, indent=2)
            else:
                f.write(content)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'folder': folder_key,
            'path': filepath
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FILE DELETE ENDPOINT
# ============================================================================

@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    """Delete a file"""
    try:
        folder_key = request.args.get('folder')
        filename = request.args.get('file')
        
        if not folder_key or not filename:
            return jsonify({'error': 'Missing parameters'}), 400
        
        if folder_key not in PROFILE_FOLDERS:
            return jsonify({'error': 'Invalid folder'}), 400
        
        # Security: Prevent directory traversal
        filename = secure_filename(filename)
        filepath = os.path.join(PROFILE_FOLDERS[folder_key], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Deleted {filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FILE DOWNLOAD ENDPOINT
# ============================================================================

@app.route('/api/files/download', methods=['GET'])
def download_file():
    """Download a file"""
    try:
        folder_key = request.args.get('folder')
        filename = request.args.get('file')
        
        if not folder_key or not filename:
            return jsonify({'error': 'Missing parameters'}), 400
        
        if folder_key not in PROFILE_FOLDERS:
            return jsonify({'error': 'Invalid folder'}), 400
        
        # Security: Prevent directory traversal
        filename = secure_filename(filename)
        filepath = os.path.join(PROFILE_FOLDERS[folder_key], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RISK MANAGEMENT SETTINGS ENDPOINT
# ============================================================================

@app.route('/api/risk/save', methods=['POST'])
def save_risk_settings():
    """Save risk management settings"""
    try:
        settings = request.json
        
        # Save to config file or database
        risk_config_path = 'risk_settings.json'
        with open(risk_config_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Risk settings saved'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk/load', methods=['GET'])
def load_risk_settings():
    """Load risk management settings"""
    try:
        risk_config_path = 'risk_settings.json'
        
        if not os.path.exists(risk_config_path):
            # Return defaults
            return jsonify({
                'maxDrawdown': 3,
                'takeProfits': [
                    {'type': 'atr', 'value': 1.0},
                    {'type': 'atr', 'value': 1.5},
                    {'type': 'atr', 'value': 2.0},
                    {'type': 'atr', 'value': 2.5},
                    {'type': 'trail', 'value': 0.5}
                ]
            })
        
        with open(risk_config_path, 'r') as f:
            settings = json.load(f)
        
        return jsonify(settings)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# END OF PROFILE MANAGEMENT API ENDPOINTS
# ============================================================================
