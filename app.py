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

# ============================================
# CONFIGURAÇÕES DE SEGURANÇA
# ============================================

# Sessões seguras
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

# Rate limiting (proteção contra ataques de força bruta)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Para produção, usar Redis
)

# Logs de segurança
os.makedirs('logs', exist_ok=True)
security_logger = logging.getLogger('aurora_security')
security_logger.setLevel(logging.INFO)
handler = RotatingFileHandler('logs/security.log', maxBytes=10000000, backupCount=5)
formatter = loggingFormatter('%(asctime)s - %(levelname)s - %(message)s')
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
    response.headers['Permissions-Policy'] = 'geolocation=(self), microphone=()'
    return response

# ============================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================

def validar_senha_forte(senha):
    """
    Valida se a senha atende aos requisitos de segurança
    """
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
    """
    Valida formato do email
    """
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def validar_telefone(telefone):
    """
    Valida formato do telefone (opcional)
    """
    if not telefone:
        return True
    telefone = re.sub(r'\D', '', telefone)
    return len(telefone) in [10, 11]

# ============================================
# BANCO DE DADOS
# ============================================

def get_db():
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgresql://'):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url)
        
        # Criar tabelas se não existirem
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    date TEXT NOT NULL,
                    name TEXT NOT NULL,
                    situation TEXT NOT NULL,
                    message TEXT,
                    lat TEXT,
                    lng TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    phone TEXT,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    relationship TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    email TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        return conn
    else:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        
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
        
        # Criar usuário demo se não existir
        demo = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()
        if not demo:
            password_hash = generate_password_hash("123456")
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Ana Silva", "ana@demo.com", password_hash)
            )
            
            user_id = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()['id']
            
            conn.execute(
                "INSERT INTO contacts (user_id, name, phone, relationship) VALUES (?, ?, ?, ?)",
                (user_id, "CLECI", "(11) 99999-9999", "Irmã")
            )
            
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
        alerts = []
        
        if hasattr(conn, 'cursor'):
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100")
                for row in cursor.fetchall():
                    alerts.append({
                        'id': row['id'],
                        'date': row['date'],
                        'name': row['name'],
                        'situation': row['situation'],
                        'message': row['message'] or '',
                        'lat': row['lat'],
                        'lng': row['lng']
                    })
        else:
            rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
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
        security_logger.error(f"Erro ao buscar histórico: {str(e)}")
        return jsonify([])

# ============================================
# ROTAS DE AUTENTICAÇÃO (COM SEGURANÇA)
# ============================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Máx 5 tentativas por minuto
def login():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            if not email or not password:
                return jsonify({
                    "status": "error", 
                    "message": "E-mail e senha são obrigatórios"
                }), 400
            
            conn = get_db()
            user = None
            
            # Verificar se usuário está bloqueado
            if hasattr(conn, 'cursor'):
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, name, password_hash, login_attempts, locked_until 
                        FROM users WHERE email = %s
                    """, (email,))
                    user = cursor.fetchone()
            else:
                user = conn.execute("""
                    SELECT id, name, password_hash, login_attempts, locked_until 
                    FROM users WHERE email = ?
                """, (email,)).fetchone()
            
            # Verificar bloqueio
            if user and user['locked_until']:
                locked_until = datetime.fromisoformat(user['locked_until']) if isinstance(user['locked_until'], str) else user['locked_until']
                if locked_until > datetime.now():
                    security_logger.warning(f"Tentativa de login em conta bloqueada: {email} - IP: {ip}")
                    return jsonify({
                        "status": "error", 
                        "message": "Conta temporariamente bloqueada por muitas tentativas. Tente novamente mais tarde."
                    }), 403
            
            # Verificar senha
            if user and check_password_hash(user['password_hash'], password):
                # Login bem-sucedido
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                
                # Resetar tentativas e atualizar último login
                if hasattr(conn, 'cursor'):
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE users 
                            SET login_attempts = 0, last_login = %s, locked_until = NULL 
                            WHERE id = %s
                        """, (datetime.now(), user['id']))
                        
                        cursor.execute("""
                            INSERT INTO login_logs (user_id, email, ip_address, user_agent, success)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (user['id'], email, ip, user_agent, True))
                else:
                    conn.execute("""
                        UPDATE users 
                        SET login_attempts = 0, last_login = ?, locked_until = NULL 
                        WHERE id = ?
                    """, (datetime.now().isoformat(), user['id']))
                    
                    conn.execute("""
                        INSERT INTO login_logs (user_id, email, ip_address, user_agent, success)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user['id'], email, ip, user_agent, True))
                
                conn.commit()
                conn.close()
                
                security_logger.info(f"Login bem-sucedido: {email} - IP: {ip}")
                
                return jsonify({
                    "status": "ok", 
                    "redirect": "/mulher"
                })
            else:
                # Login falhou - incrementar tentativas
                if user:
                    novas_tentativas = user['login_attempts'] + 1
                    
                    # Bloquear após 5 tentativas
                    if novas_tentativas >= 5:
                        locked_until = datetime.now() + timedelta(minutes=15)
                        
                        if hasattr(conn, 'cursor'):
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    UPDATE users 
                                    SET login_attempts = %s, locked_until = %s 
                                    WHERE id = %s
                                """, (novas_tentativas, locked_until, user['id']))
                        else:
                            conn.execute("""
                                UPDATE users 
                                SET login_attempts = ?, locked_until = ? 
                                WHERE id = ?
                            """, (novas_tentativas, locked_until.isoformat(), user['id']))
                        
                        security_logger.warning(f"Conta bloqueada após 5 tentativas: {email} - IP: {ip}")
                    else:
                        if hasattr(conn, 'cursor'):
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    UPDATE users SET login_attempts = %s WHERE id = %s
                                """, (novas_tentativas, user['id']))
                        else:
                            conn.execute("""
                                UPDATE users SET login_attempts = ? WHERE id = ?
                            """, (novas_tentativas, user['id']))
                
                # Registrar tentativa falha
                if hasattr(conn, 'cursor'):
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO login_logs (email, ip_address, user_agent, success)
                            VALUES (%s, %s, %s, %s)
                        """, (email, ip, user_agent, False))
                else:
                    conn.execute("""
                        INSERT INTO login_logs (email, ip_address, user_agent, success)
                        VALUES (?, ?, ?, ?)
                    """, (email, ip, user_agent, False))
                
                conn.commit()
                conn.close()
                
                security_logger.warning(f"Tentativa de login falha: {email} - IP: {ip}")
                
                return jsonify({
                    "status": "error", 
                    "message": "E-mail ou senha inválidos"
                }), 401
                
        except Exception as e:
            security_logger.error(f"Erro no login: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": "Erro interno no servidor"
            }), 500
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")  # Máx 3 cadastros por hora
def register():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            phone = data.get("phone", "").strip()
            ip = request.remote_addr
            
            # Validações
            if not name or not email or not password:
                return jsonify({"status": "error", "message": "Todos os campos são obrigatórios"}), 400
            
            if not validar_email(email):
                return jsonify({"status": "error", "message": "Formato de e-mail inválido"}), 400
            
            if not validar_telefone(phone):
                return jsonify({"status": "error", "message": "Formato de telefone inválido"}), 400
            
            erros_senha = validar_senha_forte(password)
            if erros_senha:
                return jsonify({"status": "error", "message": ". ".join(erros_senha)}), 400
            
            conn = get_db()
            existing_user = None
            
            if hasattr(conn, 'cursor'):
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    existing_user = cursor.fetchone()
            else:
                existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            
            if existing_user:
                conn.close()
                security_logger.warning(f"Tentativa de cadastro com e-mail existente: {email} - IP: {ip}")
                return jsonify({"status": "error", "message": "E-mail já cadastrado"}), 409
            
            password_hash = generate_password_hash(password)
            
            if hasattr(conn, 'cursor'):
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (name, email, password_hash, phone)
                        VALUES (%s, %s, %s, %s)
                    """, (name, email, password_hash, phone))
            else:
                conn.execute("""
                    INSERT INTO users (name, email, password_hash, phone)
                    VALUES (?, ?, ?, ?)
                """, (name, email, password_hash, phone))
            
            conn.commit()
            conn.close()
            
            security_logger.info(f"Novo usuário cadastrado: {email} - IP: {ip}")
            
            return jsonify({
                "status": "ok", 
                "message": "Cadastro realizado com sucesso!",
                "redirect": "/login"
            })
            
        except Exception as e:
            security_logger.error(f"Erro no cadastro: {str(e)}")
            return jsonify({"status": "error", "message": "Erro ao cadastrar"}), 500
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    if 'user_id' in session:
        security_logger.info(f"Logout: usuário {session['user_id']} - IP: {request.remote_addr}")
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
    contacts_list = []
    
    if hasattr(conn, 'cursor'):
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM contacts WHERE user_id = %s", (session['user_id'],))
            for row in cursor.fetchall():
                contacts_list.append({
                    'id': row['id'],
                    'name': row['name'],
                    'phone': row['phone'],
                    'email': row.get('email', ''),
                    'relationship': row.get('relationship', '')
                })
    else:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE user_id = ?", 
            (session['user_id'],)
        ).fetchall()
        for row in rows:
            contacts_list.append({
                'id': row['id'],
                'name': row['name'],
                'phone': row['phone'],
                'email': row['email'] or '',
                'relationship': row['relationship'] or ''
            })
    
    conn.close()
    return render_template("contacts.html", contacts=contacts_list)

@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect("/login")
    
    conn = get_db()
    alerts_list = []
    
    if hasattr(conn, 'cursor'):
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM alerts ORDER BY id DESC")
            for row in cursor.fetchall():
                alerts_list.append({
                    'id': row['id'],
                    'date': row['date'],
                    'name': row['name'],
                    'situation': row['situation'],
                    'message': row['message'] or '',
                    'lat': row['lat'],
                    'lng': row['lng']
                })
    else:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
        for row in rows:
            alerts_list.append({
                'id': row['id'],
                'date': row['date'],
                'name': row['name'],
                'situation': row['situation'],
                'message': row['message'] or '',
                'lat': row['lat'],
                'lng': row['lng']
            })
    
    conn.close()
    return render_template("history.html", alerts=alerts_list)

# ============================================
# API DO BOTÃO DE PÂNICO
# ============================================

@app.route("/api/panic", methods=["POST"])
@limiter.limit("10 per minute")  # Máx 10 alertas por minuto
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
        
        if hasattr(conn, 'cursor'):
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO alerts (date, name, situation, message, lat, lng)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    name,
                    situation,
                    message,
                    lat,
                    lng
                ))
        else:
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
        security_logger.error(f"Erro ao processar alerta: {str(e)}")
        return jsonify({"status": "error", "message": "Erro ao processar alerta"}), 500

# ============================================
# API DE CONTATOS (PROTEGIDA)
# ============================================

@app.route("/api/contacts", methods=["GET", "POST", "DELETE", "PUT"])
def api_contacts():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Não autorizado"}), 401
    
    conn = get_db()
    
    if request.method == "GET":
        contacts_list = []
        if hasattr(conn, 'cursor'):
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT * FROM contacts WHERE user_id = %s", (session['user_id'],))
                for row in cursor.fetchall():
                    contacts_list.append({
                        'id': row['id'],
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row.get('email', ''),
                        'relationship': row.get('relationship', '')
                    })
        else:
            rows = conn.execute("SELECT * FROM contacts WHERE user_id = ?", (session['user_id'],)).fetchall()
            for row in rows:
                contacts_list.append({
                    'id': row['id'],
                    'name': row['name'],
                    'phone': row['phone'],
                    'email': row['email'] or '',
                    'relationship': row['relationship'] or ''
                })
        conn.close()
        return jsonify(contacts_list)
    
    elif request.method == "POST":
        data = request.get_json()
        name = data.get("name")
        phone = data.get("phone")
        email = data.get("email", "")
        relationship = data.get("relationship", "")
        
        if not name or not phone:
            return jsonify({"status": "error", "message": "Nome e telefone obrigatórios"}), 400
        
        if hasattr(conn, 'cursor'):
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO contacts (user_id, name, phone, email, relationship)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session['user_id'], name, phone, email, relationship))
                contact_id = cursor.fetchone()[0] if hasattr(cursor, 'fetchone') else None
        else:
            cursor = conn.execute("""
                INSERT INTO contacts (user_id, name, phone, email, relationship)
                VALUES (?, ?, ?, ?, ?)
            """, (session['user_id'], name, phone, email, relationship))
            contact_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "message": "Contato adicionado", "id": contact_id})
    
    elif request.method == "DELETE":
        contact_id = request.args.get("id")
        if hasattr(conn, 'cursor'):
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM contacts WHERE id = %s AND user_id = %s", (contact_id, session['user_id']))
        else:
            conn.execute("DELETE FROM contacts WHERE id = ? AND user_id = ?", (contact_id, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "message": "Contato removido"})
    
    elif request.method == "PUT":
        data = request.get_json()
        contact_id = data.get("id")
        
        if hasattr(conn, 'cursor'):
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE contacts 
                    SET name=%s, phone=%s, email=%s, relationship=%s
                    WHERE id=%s AND user_id=%s
                """, (
                    data.get("name"),
                    data.get("phone"),
                    data.get("email", ""),
                    data.get("relationship", ""),
                    contact_id,
                    session['user_id']
                ))
        else:
            conn.execute("""
                UPDATE contacts 
                SET name=?, phone=?, email=?, relationship=?
                WHERE id=? AND user_id=?
            """, (
                data.get("name"),
                data.get("phone"),
                data.get("email", ""),
                data.get("relationship", ""),
                contact_id,
                session['user_id']
            ))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "message": "Contato atualizado"})

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
# PÁGINA DE TERMOS E PRIVACIDADE
# ============================================

@app.route("/termos")
def termos():
    return render_template("termos.html")

@app.route("/privacidade")
def privacidade():
    return render_template("privacidade.html")

# ============================================
# INICIALIZAÇÃO DO SERVIDOR
# ============================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🛡️ AURORA-SHIELD - MODO PRODUÇÃO")
    print("="*70)
    print("\n📌 SEGURANÇA ATIVADA:")
    print("   • Rate limiting: 5 tentativas/minuto")
    print("   • Senhas fortes: Obrigatório")
    print("   • Headers de segurança: Configurados")
    print("   • Logs: Ativos")
    print("   • Bloqueio após 5 tentativas")
    print("\n📍 ENDEREÇO:")
    print(f"   • https://aurora-shield.onrender.com")
    print("\n" + "="*70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)