from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Logs
os.makedirs('logs', exist_ok=True)
security_logger = logging.getLogger('aurora_security')
security_logger.setLevel(logging.INFO)
handler = RotatingFileHandler('logs/security.log', maxBytes=10000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)

# Headers de segurança
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' https:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ============================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================

def validar_senha_forte(senha):
    erros = []
    if len(senha) < 8:
        erros.append("A senha deve ter no mínimo 8 caracteres")
    if not re.search(r"[A-Z]", senha):
        erros.append("A senha deve conter pelo menos uma letra maiúscula")
    if not re.search(r"[a-z]", senha):
        erros.append("A senha deve conter pelo menos uma letra minúscula")
    if not re.search(r"\d", senha):
        erros.append("A senha deve conter pelo menos um número")
    if not re.search(r"[!@#$%&*]", senha):
        erros.append("A senha deve conter pelo menos um caractere especial (!@#$%&*)")
    return erros

def validar_email(email):
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# ============================================
# BANCO DE DADOS (SQLITE - MAIS SIMPLES)
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
            phone TEXT,
            last_login TEXT,
            login_attempts INTEGER DEFAULT 0,
            locked_until TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            relationship TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
            lng TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            ip_address TEXT,
            user_agent TEXT,
            success BOOLEAN,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
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
        alerts = []
        for row in rows:
            alerts.append({
                'id': row['id'],
                'date': row['date'],
                'name': row['name'],
                'situation': row['situation'],
                'message': row['message'] or '',
                'lat': row['lat'],
                'lng': row['lng']
            })
        conn.close()
        return jsonify(alerts)
    except Exception as e:
        return jsonify([])

# ============================================
# ROTAS DE AUTENTICAÇÃO
# ============================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            if not email or not password:
                return jsonify({"status": "error", "message": "E-mail e senha são obrigatórios"}), 400
            
            conn = get_db()
            user = conn.execute(
                "SELECT id, name, password_hash, login_attempts, locked_until FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            
            # Verificar bloqueio
            if user and user['locked_until']:
                locked_until = datetime.fromisoformat(user['locked_until'])
                if locked_until > datetime.now():
                    security_logger.warning(f"Tentativa em conta bloqueada: {email} - IP: {ip}")
                    return jsonify({"status": "error", "message": "Conta bloqueada. Tente novamente mais tarde."}), 403
            
            if user and check_password_hash(user['password_hash'], password):
                # Login sucesso
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                
                conn.execute(
                    "UPDATE users SET login_attempts = 0, last_login = ?, locked_until = NULL WHERE id = ?",
                    (datetime.now().isoformat(), user['id'])
                )
                conn.execute(
                    "INSERT INTO login_logs (user_id, email, ip_address, user_agent, success) VALUES (?, ?, ?, ?, ?)",
                    (user['id'], email, ip, user_agent, True)
                )
                conn.commit()
                conn.close()
                
                security_logger.info(f"Login sucesso: {email} - IP: {ip}")
                return jsonify({"status": "ok", "redirect": "/mulher"})
            else:
                # Login falhou
                if user:
                    novas_tentativas = user['login_attempts'] + 1
                    if novas_tentativas >= 5:
                        locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
                        conn.execute(
                            "UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?",
                            (novas_tentativas, locked_until, user['id'])
                        )
                        security_logger.warning(f"Conta bloqueada: {email} - IP: {ip}")
                    else:
                        conn.execute(
                            "UPDATE users SET login_attempts = ? WHERE id = ?",
                            (novas_tentativas, user['id'])
                        )
                
                conn.execute(
                    "INSERT INTO login_logs (email, ip_address, user_agent, success) VALUES (?, ?, ?, ?)",
                    (email, ip, user_agent, False)
                )
                conn.commit()
                conn.close()
                
                security_logger.warning(f"Login falhou: {email} - IP: {ip}")
                return jsonify({"status": "error", "message": "E-mail ou senha inválidos"}), 401
                
        except Exception as e:
            security_logger.error(f"Erro no login: {str(e)}")
            return jsonify({"status": "error", "message": "Erro interno no servidor"}), 500
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            phone = data.get("phone", "").strip()
            ip = request.remote_addr
            
            if not name or not email or not password:
                return jsonify({"status": "error", "message": "Todos os campos são obrigatórios"}), 400
            
            if not validar_email(email):
                return jsonify({"status": "error", "message": "Formato de e-mail inválido"}), 400
            
            erros_senha = validar_senha_forte(password)
            if erros_senha:
                return jsonify({"status": "error", "message": ". ".join(erros_senha)}), 400
            
            conn = get_db()
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            
            if existing:
                conn.close()
                security_logger.warning(f"Tentativa de cadastro com email existente: {email} - IP: {ip}")
                return jsonify({"status": "error", "message": "E-mail já cadastrado"}), 409
            
            password_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (name, email, password_hash, phone) VALUES (?, ?, ?, ?)",
                (name, email, password_hash, phone)
            )
            conn.commit()
            conn.close()
            
            security_logger.info(f"Novo usuário cadastrado: {email} - IP: {ip}")
            return jsonify({"status": "ok", "message": "Cadastro realizado com sucesso!", "redirect": "/login"})
            
        except Exception as e:
            security_logger.error(f"Erro no cadastro: {str(e)}")
            return jsonify({"status": "error", "message": "Erro ao cadastrar"}), 500
    
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
@limiter.limit("10 per minute")
def api_panic():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "Dados não fornecidos"}), 400
        
        name = data.get("name", "Anônimo")
        situation = data.get("situation", "Emergência")
        message = data.get("message", "")
        lat = str(data.get("lat", "")) if data.get("lat") else ""
        lng = str(data.get("lng", "")) if data.get("lng") else ""
        ip = request.remote_addr
        
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
        
        security_logger.info(f"Alerta enviado: {name} - {situation} - IP: {ip}")
        return jsonify({"status": "ok", "message": "Alerta enviado com sucesso!"})
        
    except Exception as e:
        security_logger.error(f"Erro no alerta: {str(e)}")
        return jsonify({"status": "error", "message": "Erro ao processar alerta"}), 500

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
        email = data.get("email", "")
        relationship = data.get("relationship", "")
        
        if not name or not phone:
            return jsonify({"status": "error", "message": "Nome e telefone obrigatórios"}), 400
        
        cursor = conn.execute("""
            INSERT INTO contacts (user_id, name, phone, email, relationship)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], name, phone, email, relationship))
        conn.commit()
        contact_id = cursor.lastrowid
        conn.close()
        
        return jsonify({"status": "ok", "message": "Contato adicionado", "id": contact_id})
    
    elif request.method == "DELETE":
        contact_id = request.args.get("id")
        conn.execute(
            "DELETE FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, session['user_id'])
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "message": "Contato removido"})

# ============================================
# ROTAS DE TERMOS E PRIVACIDADE
# ============================================

@app.route("/termos")
def termos():
    return render_template("termos.html")

@app.route("/privacidade")
def privacidade():
    return render_template("privacidade.html")

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
# ROTAS DE DIAGNÓSTICO (remover em produção)
# ============================================

@app.route("/diagnostico")
def diagnostico():
    try:
        conn = get_db()
        users = conn.execute("SELECT id, name, email FROM users").fetchall()
        alerts = conn.execute("SELECT COUNT(*) as total FROM alerts").fetchone()
        contacts = conn.execute("SELECT COUNT(*) as total FROM contacts").fetchone()
        conn.close()
        
        html = "<h1>🔍 DIAGNÓSTICO DO SISTEMA</h1>"
        html += f"<p>✅ Banco de dados: SQLite</p>"
        html += f"<p>👤 Usuários cadastrados: {len(users)}</p>"
        html += f"<p>🚨 Total de alertas: {alerts['total']}</p>"
        html += f"<p>📞 Total de contatos: {contacts['total']}</p>"
        
        if users:
            html += "<h2>Usuários:</h2><ul>"
            for user in users:
                html += f"<li>{user['id']} - {user['name']} ({user['email']})</li>"
            html += "</ul>"
        
        html += '<p><a href="/login">Ir para login</a> | <a href="/">Página inicial</a></p>'
        return html
    except Exception as e:
        return f"<h1>❌ ERRO</h1><p>{str(e)}</p>"

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🛡️ AURORA-SHIELD INICIADO")
    print("="*60)
    print("\n📌 USUÁRIOS DEMO:")
    print("   • ana@demo.com / 123456")
    print("   • mulher@demo.com / 123456")
    print("   • confidante@demo.com / 123456")
    print("\n📍 URL: http://localhost:5000")
    print("="*60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)