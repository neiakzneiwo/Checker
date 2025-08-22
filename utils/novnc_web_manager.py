#!/usr/bin/env python3
"""
noVNC Web Manager
Provides a web interface to manage and access multiple VNC sessions
"""

import os
import json
import logging
from typing import Dict, List, Any
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from .vnc_manager import vnc_manager
from .vnc_browser_manager import vnc_browser_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NoVNCWebManager:
    """Web interface for managing noVNC sessions"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Set up Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard showing all VNC sessions"""
            sessions = vnc_browser_manager.list_sessions()
            return render_template_string(DASHBOARD_TEMPLATE, sessions=sessions)
        
        @self.app.route('/api/sessions')
        def api_sessions():
            """API endpoint to get all sessions"""
            sessions = vnc_browser_manager.list_sessions()
            return jsonify(sessions)
        
        @self.app.route('/api/create_session', methods=['POST'])
        def api_create_session():
            """API endpoint to create a new session"""
            try:
                data = request.get_json() or {}
                user_id = data.get('user_id', f'user_{len(vnc_browser_manager.browser_sessions) + 1}')
                
                # This would need to be called in an async context
                # For now, return a placeholder response
                return jsonify({
                    'success': False,
                    'error': 'Session creation requires async context. Use the async API instead.'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/destroy_session/<session_id>', methods=['DELETE'])
        def api_destroy_session(session_id):
            """API endpoint to destroy a session"""
            try:
                # This would need to be called in an async context
                return jsonify({
                    'success': False,
                    'error': 'Session destruction requires async context. Use the async API instead.'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/health')
        def api_health():
            """API endpoint for health check"""
            try:
                vnc_health = vnc_manager.health_check()
                return jsonify({
                    'vnc_sessions': vnc_health,
                    'total_sessions': len(vnc_manager.sessions),
                    'active_sessions': sum(1 for s in vnc_manager.sessions.values() if s.is_active)
                })
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/vnc/<session_id>')
        def vnc_viewer(session_id):
            """Direct VNC viewer for a session"""
            session = vnc_manager.get_session(session_id)
            if not session:
                return f"Session {session_id} not found", 404
            
            novnc_url = vnc_manager.get_novnc_url(session_id)
            if not novnc_url:
                return f"noVNC URL not available for session {session_id}", 404
            
            return redirect(novnc_url)
    
    def run(self, debug: bool = False):
        """Run the web manager"""
        logger.info(f"🌐 Starting noVNC Web Manager on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>noVNC Session Manager</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .sessions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .session-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .session-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
        }
        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .session-id {
            font-weight: bold;
            color: #333;
            font-size: 1.1em;
        }
        .session-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            background: #4CAF50;
            color: white;
        }
        .session-info {
            margin-bottom: 15px;
        }
        .session-info div {
            margin: 5px 0;
            color: #666;
        }
        .session-info strong {
            color: #333;
        }
        .session-actions {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        .btn-primary {
            background: #007bff;
            color: white;
        }
        .btn-primary:hover {
            background: #0056b3;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .no-sessions {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .no-sessions h3 {
            color: #666;
            margin-bottom: 10px;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .controls h3 {
            margin-top: 0;
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-group input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ noVNC Session Manager</h1>
        <p>Manage and monitor VNC sessions for browser automation</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{{ sessions|length }}</div>
            <div class="stat-label">Active Sessions</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">10</div>
            <div class="stat-label">Max Sessions</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ sessions|length * 100 // 10 }}%</div>
            <div class="stat-label">Capacity Used</div>
        </div>
    </div>

    <div class="controls">
        <h3>🚀 Create New Session</h3>
        <div class="form-group">
            <label for="user_id">User ID:</label>
            <input type="text" id="user_id" placeholder="Enter user ID (optional)">
        </div>
        <button class="btn btn-primary" onclick="createSession()">Create Session</button>
    </div>

    {% if sessions %}
    <div class="sessions-grid">
        {% for session_id, session in sessions.items() %}
        <div class="session-card">
            <div class="session-header">
                <div class="session-id">{{ session_id[:20] }}...</div>
                <div class="session-status">ACTIVE</div>
            </div>
            <div class="session-info">
                <div><strong>User ID:</strong> {{ session.user_id }}</div>
                <div><strong>Display:</strong> {{ session.display }}</div>
                <div><strong>Session ID:</strong> {{ session.session_id }}</div>
            </div>
            <div class="session-actions">
                <a href="{{ session.novnc_url }}" target="_blank" class="btn btn-primary">
                    🖥️ Open VNC
                </a>
                <button class="btn btn-danger" onclick="destroySession('{{ session_id }}')">
                    🗑️ Destroy
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="no-sessions">
        <h3>No Active Sessions</h3>
        <p>Create a new session to get started with VNC monitoring.</p>
    </div>
    {% endif %}

    <script>
        function createSession() {
            const userId = document.getElementById('user_id').value || 'user_' + Date.now();
            
            fetch('/api/create_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error creating session: ' + data.error);
                }
            })
            .catch(error => {
                alert('Error: ' + error);
            });
        }

        function destroySession(sessionId) {
            if (confirm('Are you sure you want to destroy this session?')) {
                fetch('/api/destroy_session/' + sessionId, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error destroying session: ' + data.error);
                    }
                })
                .catch(error => {
                    alert('Error: ' + error);
                });
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

# Global web manager instance
novnc_web_manager = NoVNCWebManager()

if __name__ == "__main__":
    # Run the web manager
    novnc_web_manager.run(debug=True)