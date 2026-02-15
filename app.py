from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
import sqlite3
import os
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ============================================
# BANCO DE DADOS
# ============================================

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Tabela de alertas (para o botão de pânico)
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
    
    # Tabela de pessoas de confiança (agora com login)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trusted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de contatos (pessoas de confiança da mulher)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            relationship TEXT
        )
    """)
    
    conn.commit()
    
    # Criar contatos demo
    demo = conn.execute("SELECT id FROM contacts LIMIT 1").fetchone()
    if not demo:
        conn.execute(
            "INSERT INTO contacts (name, phone, relationship) VALUES (?, ?, ?)",
            ("CLECI", "(11) 99999-9999", "Irmã")
        )
        conn.execute(
            "INSERT INTO contacts (name, phone, relationship) VALUES (?, ?, ?)",
            ("MARIA", "(11) 98888-7777", "Mãe")
        )
        conn.execute(
            "INSERT INTO contacts (name, phone, relationship) VALUES (?, ?, ?)",
            ("JOÃO", "(11) 97777-6666", "Pai")
        )
        conn.commit()
    
    return conn

# ============================================
# ROTAS PÚBLICAS (MULHER - SEM LOGIN)
# ============================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/mulher")
def mulher():
    """Painel da Mulher - ACESSO DIRETO (sem login)"""
    conn = get_db()
    contacts = conn.execute("SELECT * FROM contacts").fetchall()
    conn.close()
    return render_template("mulher.html", contacts=contacts)

@app.route("/confidant")
def confidant():
    """Painel da Pessoa de Confiança - ACESSO PÚBLICO"""
    return render_template("confidant.html")

@app.route("/history_json")
def history_json():
    """API pública de alertas"""
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
        alerts = [dict(row) for row in rows]
        conn.close()
        return jsonify(alerts)
    except:
        return jsonify([])

# ============================================
# API DO BOTÃO DE PÂNICO (PÚBLICO)
# ============================================

@app.route("/api/panic", methods=["POST"])
def api_panic():
    try:
        data = request.get_json()
        
        name = data.get("name", "Usuária")
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
# ROTAS PARA PESSOAS DE CONFIANÇA (COM LOGIN)
# ============================================

@app.route("/login-confidante", methods=["GET", "POST"])
def login_confidante():
    """Login exclusivo para pessoas de confiança"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        conn = get_db()
        user = conn.execute(
            "SELECT id, name FROM trusted WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['trusted_id'] = user['id']
            session['trusted_name'] = user['name']
            return jsonify({"status": "ok", "redirect": "/painel-confidante"})
        else:
            return jsonify({"status": "error", "message": "E-mail ou senha inválidos"}), 401
    
    return render_template("login_confidante.html")

@app.route("/registro-confidante", methods=["GET", "POST"])
def registro_confidante():
    """Cadastro exclusivo para pessoas de confiança"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        phone = data.get("phone", "").strip()
        
        if not name or not email or not password:
            return jsonify({"status": "error", "message": "Todos os campos obrigatórios"}), 400
        
        conn = get_db()
        existing = conn.execute("SELECT id FROM trusted WHERE email = ?", (email,)).fetchone()
        
        if existing:
            conn.close()
            return jsonify({"status": "error", "message": "E-mail já cadastrado"}), 409
        
        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO trusted (name, email, password_hash, phone) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, phone)
        )
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "message": "Cadastro realizado!", "redirect": "/login-confidante"})
    
    return render_template("registro_confidante.html")

@app.route("/painel-confidante")
def painel_confidante():
    """Painel da pessoa de confiança (protegido)"""
    if 'trusted_id' not in session:
        return redirect("/login-confidante")
    return render_template("painel_confidante.html", user=session.get('trusted_name'))

@app.route("/logout-confidante")
def logout_confidante():
    session.clear()
    return redirect("/")

# ============================================
# API DE CONTATOS (PÚBLICA)
# ============================================

@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    conn = get_db()
    contacts = conn.execute("SELECT * FROM contacts").fetchall()
    conn.close()
    return jsonify([dict(c) for c in contacts])

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
        alerts = conn.execute("SELECT COUNT(*) as total FROM alerts").fetchone()
        contacts = conn.execute("SELECT * FROM contacts").fetchall()
        trusted = conn.execute("SELECT COUNT(*) as total FROM trusted").fetchone()
        conn.close()
        
        html = "<h1>✅ SISTEMA FUNCIONANDO!</h1>"
        html += f"<p>🚨 Alertas: {alerts['total']}</p>"
        html += f"<p>👥 Contatos de confiança: {len(contacts)}</p>"
        html += f"<p>🔐 Pessoas de confiança cadastradas: {trusted['total']}</p>"
        html += "<h3>Contatos:</h3><ul>"
        for c in contacts:
            html += f"<li>{c['name']} - {c['phone']} ({c['relationship']})</li>"
        html += "</ul>"
        html += '<p><a href="/">Voltar</a></p>'
        return html
    except Exception as e:
        return f"<h1>❌ ERRO: {str(e)}</h1>"

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🛡️ AURORA-SHIELD - MODO SIMPLIFICADO")
    print("="*60)
    print("\n👩 MULHER: ACESSO DIRETO (sem login)")
    print("   • https://aurora-shield.onrender.com/mulher")
    print("\n👥 CONFIDANTE: ACESSO PÚBLICO")
    print("   • https://aurora-shield.onrender.com/confidant")
    print("\n🔐 CONFIDANTE COM LOGIN (opcional):")
    print("   • /login-confidante")
    print("   • /registro-confidante")
    print("\n📌 Contatos demo:")
    print("   • CLECI, MARIA, JOÃO")
    print("\n" + "="*60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)