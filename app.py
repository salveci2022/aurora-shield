from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
import secrets
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Logs
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/app.log', level=logging.INFO)

# ============================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================

def validar_senha_forte(senha):
    erros = []
    if len(senha) < 6:
        erros.append("A senha deve ter no mínimo 6 caracteres")
    return erros

def validar_email(email):
    return '@' in email and '.' in email

# ============================================
# BANCO DE DADOS (SQLITE SIMPLES)
# ============================================

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Criar tabelas se não existirem
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            relationship TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            situation TEXT NOT NULL,
            message TEXT,
            lat TEXT,
            lng TEXT
        )
    """)
    
    conn.commit()
    
    # Criar usuários demo se não existirem
    demo = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()
    if not demo:
        password_hash = generate_password_hash("123456")
        
        # Criar usuárias demo
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Ana Silva", "ana@demo.com", password_hash)
        )
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Maria Demo", "mulher@demo.com", password_hash)
        )
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("João Confiança", "confidante@demo.com", password_hash)
        )
        
        # Pegar ID da Ana
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()['id']
        
        # Criar contato de confiança
        conn.execute(
            "INSERT INTO contacts (user_id, name, phone, relationship) VALUES (?, ?, ?, ?)",
            (user_id, "CLECI", "(11) 99999-9999", "Irmã")
        )
        
        # Criar alerta demo
        conn.execute("""
            INSERT INTO alerts (date, name, situation, lat, lng) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Ana Silva",
            "Situação de risco",
            "-23.5505",
            "-46.6333"
        ))
        
        conn.commit()
    
    return conn

# ============================================
# ROTAS PÚBLICAS
# ============================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/confidant")
def confidant():
    return render_template("confidant.html")

@app.route("/history_json")
def history_json():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
        alerts = [dict(row) for row in rows]
        conn.close()
        return jsonify(alerts)
    except:
        return jsonify([])

# ============================================
# ROTAS DE AUTENTICAÇÃO
# ============================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            
            if not email or not password:
                return jsonify({"status": "error", "message": "E-mail e senha obrigatórios"}), 400
            
            conn = get_db()
            user = conn.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                conn.close()
                return jsonify({"status": "ok", "redirect": "/mulher"})
            else:
                conn.close()
                return jsonify({"status": "error", "message": "E-mail ou senha inválidos"}), 401
                
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            
            if not name or not email or not password:
                return jsonify({"status": "error", "message": "Todos os campos obrigatórios"}), 400
            
            if not validar_email(email):
                return jsonify({"status": "error", "message": "E-mail inválido"}), 400
            
            conn = get_db()
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            
            if existing:
                conn.close()
                return jsonify({"status": "error", "message": "E-mail já cadastrado"}), 409
            
            password_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash)
            )
            conn.commit()
            conn.close()
            
            return jsonify({"status": "ok", "message": "Cadastro realizado!", "redirect": "/login"})
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ============================================
# ROTAS PROTEGIDAS
# ============================================

@app.route("/mulher")
def mulher():
    if 'user_id' not in session:
        return redirect("/login")
    return render_template("mulher.html", user=session.get('user_name'))

@app.route("/contacts")
def contacts():
    if 'user_id' not in session:
        return redirect("/login")
    
    conn = get_db()
    contacts = conn.execute(
        "SELECT * FROM contacts WHERE user_id = ?",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template("contacts.html", contacts=contacts)

@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect("/login")
    
    conn = get_db()
    alerts = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("history.html", alerts=alerts)

# ============================================
# API DO BOTÃO DE PÂNICO
# ============================================

@app.route("/api/panic", methods=["POST"])
def api_panic():
    try:
        data = request.get_json()
        
        name = data.get("name", "Anônimo")
        situation = data.get("situation", "Emergência")
        message = data.get("message", "")
        lat = str(data.get("lat", "")) if data.get("lat") else ""
        lng = str(data.get("lng", "")) if data.get("lng") else ""
        
        conn = get_db()
        conn.execute("""
            INSERT INTO alerts (date, name, situation, message, lat, lng)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            name,
            situation,
            message,
            lat,
            lng
        ))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "message": "Alerta enviado!"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# API DE CONTATOS
# ============================================

@app.route("/api/contacts", methods=["GET", "POST", "DELETE"])
def api_contacts():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Não autorizado"}), 401
    
    conn = get_db()
    
    if request.method == "GET":
        contacts = conn.execute(
            "SELECT * FROM contacts WHERE user_id = ?",
            (session['user_id'],)
        ).fetchall()
        conn.close()
        return jsonify([dict(c) for c in contacts])
    
    elif request.method == "POST":
        data = request.get_json()
        name = data.get("name")
        phone = data.get("phone")
        relationship = data.get("relationship", "")
        
        cursor = conn.execute("""
            INSERT INTO contacts (user_id, name, phone, relationship)
            VALUES (?, ?, ?, ?)
        """, (session['user_id'], name, phone, relationship))
        conn.commit()
        contact_id = cursor.lastrowid
        conn.close()
        return jsonify({"status": "ok", "id": contact_id})
    
    elif request.method == "DELETE":
        contact_id = request.args.get("id")
        conn.execute(
            "DELETE FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, session['user_id'])
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})

# ============================================
# ARQUIVOS ESTÁTICOS
# ============================================

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

# ============================================
# ROTA DE DIAGNÓSTICO
# ============================================

@app.route("/diagnostico")
def diagnostico():
    try:
        conn = get_db()
        users = conn.execute("SELECT id, name, email FROM users").fetchall()
        conn.close()
        
        html = "<h1>✅ SISTEMA FUNCIONANDO!</h1>"
        html += f"<p>Usuários: {len(users)}</p>"
        html += "<ul>"
        for user in users:
            html += f"<li>{user['email']}</li>"
        html += "</ul>"
        html += '<p><a href="/login">Ir para login</a></p>'
        return html
    except Exception as e:
        return f"<h1>❌ ERRO: {str(e)}</h1>"

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    print("="*50)
    print("🚀 AURORA-SHIELD INICIADO")
    print("="*50)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)