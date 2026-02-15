from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
import sqlite3
import os
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# -------------------------
# BANCO DE DADOS ADAPTÁVEL (SQLite / PostgreSQL)
# -------------------------

def get_db():
    """Conecta ao banco de dados - SQLite local ou PostgreSQL produção"""
    database_url = os.environ.get('DATABASE_URL')
    
    # PRODUÇÃO: PostgreSQL no Render
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
                    lng TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Verificar se existe usuário demo
            cursor.execute("SELECT id FROM users WHERE email = %s", ("ana@demo.com",))
            if not cursor.fetchone():
                password_hash = generate_password_hash("123456")
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    ("Ana Silva", "ana@demo.com", password_hash)
                )
                
                # Pegar ID da usuária criada
                cursor.execute("SELECT id FROM users WHERE email = %s", ("ana@demo.com",))
                user_id = cursor.fetchone()[0]
                
                # Inserir contato CLECI
                cursor.execute(
                    "INSERT INTO contacts (user_id, name, phone) VALUES (%s, %s, %s)",
                    (user_id, "CLECI", "(11) 99999-9999")
                )
                
                # Inserir alerta demo
                cursor.execute("""
                    INSERT INTO alerts (date, name, situation, lat, lng) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Ana Silva",
                    "Situação de risco",
                    "-23.5505",
                    "-46.6333"
                ))
        
        conn.commit()
        return conn
    
    # DESENVOLVIMENTO: SQLite local
    else:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        
        # Criar tabelas
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
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
        
        # Verificar se existe usuário demo
        demo_user = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()
        if not demo_user:
            password_hash = generate_password_hash("123456")
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Ana Silva", "ana@demo.com", password_hash)
            )
            
            user_id = conn.execute("SELECT id FROM users WHERE email = ?", ("ana@demo.com",)).fetchone()['id']
            
            conn.execute(
                "INSERT INTO contacts (user_id, name, phone) VALUES (?, ?, ?)",
                (user_id, "CLECI", "(11) 99999-9999")
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

# -------------------------
# ROTAS PÚBLICAS
# -------------------------

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
        
        # Verifica se é PostgreSQL ou SQLite
        if hasattr(conn, 'cursor'):  # É PostgreSQL
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
        else:  # É SQLite
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
        print(f"Erro ao buscar histórico: {e}")
        return jsonify([])

# -------------------------
# ROTAS DE AUTENTICAÇÃO
# -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            
            if not email or not password:
                return jsonify({
                    "status": "error", 
                    "message": "E-mail e senha são obrigatórios"
                }), 400
            
            conn = get_db()
            user = None
            
            if hasattr(conn, 'cursor'):  # PostgreSQL
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("SELECT id, name, password_hash FROM users WHERE email = %s", (email,))
                    user = cursor.fetchone()
            else:  # SQLite
                user = conn.execute(
                    "SELECT id, name, password_hash FROM users WHERE email = ?", 
                    (email,)
                ).fetchone()
            
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                return jsonify({
                    "status": "ok", 
                    "redirect": "/mulher"
                })
            else:
                return jsonify({
                    "status": "error", 
                    "message": "E-mail ou senha inválidos"
                }), 401
                
        except Exception as e:
            print(f"Erro no login: {e}")
            return jsonify({
                "status": "error", 
                "message": "Erro interno no servidor"
            }), 500
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -------------------------
# ROTAS PROTEGIDAS
# -------------------------

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
    
    if hasattr(conn, 'cursor'):  # PostgreSQL
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM contacts WHERE user_id = %s", (session['user_id'],))
            for row in cursor.fetchall():
                contacts_list.append({
                    'id': row['id'],
                    'name': row['name'],
                    'phone': row['phone']
                })
    else:  # SQLite
        rows = conn.execute(
            "SELECT * FROM contacts WHERE user_id = ?", 
            (session['user_id'],)
        ).fetchall()
        for row in rows:
            contacts_list.append({
                'id': row['id'],
                'name': row['name'],
                'phone': row['phone']
            })
    
    conn.close()
    return render_template("contacts.html", contacts=contacts_list)

@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect("/login")
    
    conn = get_db()
    alerts_list = []
    
    if hasattr(conn, 'cursor'):  # PostgreSQL
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
    else:  # SQLite
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

# -------------------------
# API DO BOTÃO DE PÂNICO
# -------------------------

@app.route("/api/panic", methods=["POST"])
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
        
        conn = get_db()
        
        if hasattr(conn, 'cursor'):  # PostgreSQL
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
        else:  # SQLite
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
        
        print(f"🚨 ALERTA RECEBIDO: {name} - {situation}")
        
        return jsonify({"status": "ok", "message": "Alerta enviado com sucesso!"})
        
    except Exception as e:
        print(f"Erro ao processar alerta: {e}")
        return jsonify({"status": "error", "message": "Erro ao processar alerta"}), 500

# -------------------------
# ROTA DE CADASTRO
# -------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            
            if not name or not email or not password:
                return jsonify({"status": "error", "message": "Todos os campos são obrigatórios"}), 400
            
            if len(password) < 6:
                return jsonify({"status": "error", "message": "Senha deve ter no mínimo 6 caracteres"}), 400
            
            conn = get_db()
            existing_user = None
            
            if hasattr(conn, 'cursor'):  # PostgreSQL
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    existing_user = cursor.fetchone()
            else:  # SQLite
                existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            
            if existing_user:
                conn.close()
                return jsonify({"status": "error", "message": "E-mail já cadastrado"}), 409
            
            password_hash = generate_password_hash(password)
            
            if hasattr(conn, 'cursor'):  # PostgreSQL
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                        (name, email, password_hash)
                    )
            else:  # SQLite
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, password_hash)
                )
            
            conn.commit()
            conn.close()
            
            return jsonify({
                "status": "ok", 
                "message": "Cadastro realizado com sucesso!",
                "redirect": "/login"
            })
            
        except Exception as e:
            print(f"Erro no cadastro: {e}")
            return jsonify({"status": "error", "message": "Erro ao cadastrar"}), 500
    
    return render_template("register.html")

# -------------------------
# ARQUIVOS ESTÁTICOS
# -------------------------

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

# -------------------------
# HEADERS DE SEGURANÇA
# -------------------------

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# -------------------------
# INICIALIZAÇÃO DO SERVIDOR
# -------------------------

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 AURORA MULHER SEGURA - SERVIDOR INICIADO")
    print("="*70)
    print("\n📌 BANCO DE DADOS:")
    
    if os.environ.get('DATABASE_URL'):
        print("   • Modo: PRODUÇÃO (PostgreSQL)")
    else:
        print("   • Modo: DESENVOLVIMENTO (SQLite)")
    
    print("\n📍 ENDEREÇOS:")
    print(f"   • Local: http://localhost:5000")
    print(f"   • Produção: https://aurora-mulher-segura.onrender.com")
    
    print("\n👤 ACESSO MULHER:")
    print("   • Login: http://localhost:5000/login")
    print("   • Email: ana@demo.com")
    print("   • Senha: 123456")
    
    print("\n👥 ACESSO CONFIDANTE:")
    print("   • Painel: http://localhost:5000/confidant")
    print("   • Sirene: ATIVA após primeiro clique")
    
    print("\n" + "="*70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)