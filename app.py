from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
import sqlite3
import os
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ============================================
# BANCO DE DADOS
# ============================================

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Tabela de alertas
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
    
    # Tabela de contatos (pessoas de confiança)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            relationship TEXT
        )
    """)
    
    conn.commit()
    
    # Inserir contatos demo se não existirem
    demo = conn.execute("SELECT COUNT(*) as total FROM contacts").fetchone()
    if demo['total'] == 0:
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
# ROTAS PÚBLICAS
# ============================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/mulher")
def mulher():
    """Painel da Mulher - ACESSO DIRETO"""
    try:
        conn = get_db()
        contacts = conn.execute("SELECT * FROM contacts").fetchall()
        conn.close()
        return render_template("mulher.html", contacts=contacts)
    except Exception as e:
        return f"Erro ao carregar página: {str(e)}"

@app.route("/confidant")
def confidant():
    """Painel da Pessoa de Confiança"""
    return render_template("confidant.html")

@app.route("/history_json")
def history_json():
    """API de alertas"""
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
        alerts = [dict(row) for row in rows]
        conn.close()
        return jsonify(alerts)
    except:
        return jsonify([])

# ============================================
# API DO BOTÃO DE PÂNICO - CORRIGIDO COM FUSO BR
# ============================================

@app.route("/api/panic", methods=["POST"])
def api_panic():
    try:
        data = request.get_json()
        
        name = data.get("name", "Usuária")
        situation = data.get("situation", "Emergência")
        message = data.get("message", "")
        
        # CORREÇÃO: Pegar latitude e longitude
        lat = None
        lng = None
        
        if data.get("lat") and data.get("lng"):
            lat = str(data.get("lat"))
            lng = str(data.get("lng"))
            print(f"📍 Localização recebida: {lat}, {lng}")
        else:
            print("📍 Localização NÃO fornecida")
        
        # CORREÇÃO: Data e hora no fuso brasileiro
        fuso_br = pytz.timezone('America/Sao_Paulo')
        agora = datetime.now(fuso_br)
        data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        print(f"📅 Data formatada (BR): {data_formatada}")
        
        conn = get_db()
        conn.execute("""
            INSERT INTO alerts (date, name, situation, message, lat, lng)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data_formatada,
            name,
            situation,
            message,
            lat,
            lng
        ))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "ok", 
            "message": "Alerta enviado!",
            "data": data_formatada,
            "localizacao": f"{lat},{lng}" if lat and lng else None
        })
        
    except Exception as e:
        print(f"❌ Erro no alerta: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# API DE CONTATOS
# ============================================

@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    try:
        conn = get_db()
        contacts = conn.execute("SELECT * FROM contacts").fetchall()
        conn.close()
        return jsonify([dict(c) for c in contacts])
    except:
        return jsonify([])

# ============================================
# ROTAS DE GERENCIAMENTO DE CONTATOS
# ============================================

@app.route("/gerenciar-contatos")
def gerenciar_contatos():
    """Página para gerenciar contatos (adicionar e excluir)"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gerenciar Contatos - Aurora Shield</title>
        <style>
            body { 
                background: #0a0015; 
                color: white; 
                font-family: Arial; 
                padding: 20px; 
                margin: 0;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
            }
            h1 {
                text-align: center;
                background: linear-gradient(45deg, #ff2fd4, #7a00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 30px;
            }
            .card { 
                background: #140022; 
                padding: 25px; 
                border-radius: 20px; 
                box-shadow: 0 0 30px rgba(122, 0, 255, 0.3);
                margin-bottom: 20px;
            }
            h2 {
                color: #ff2fd4;
                margin-top: 0;
                margin-bottom: 20px;
            }
            .form-group {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 20px;
            }
            input, button { 
                padding: 12px; 
                margin: 0; 
                border-radius: 8px; 
                font-size: 14px;
            }
            input {
                flex: 1;
                min-width: 150px;
                background: #1d0030;
                border: 2px solid #7a00ff;
                color: white;
            }
            input:focus {
                outline: none;
                border-color: #ff2fd4;
                box-shadow: 0 0 10px #ff2fd4;
            }
            button { 
                background: #7a00ff; 
                color: white; 
                border: none; 
                cursor: pointer; 
                font-weight: bold;
                padding: 12px 20px;
                transition: 0.3s;
            }
            button:hover {
                background: #9a40ff;
                transform: scale(1.02);
            }
            table { 
                width: 100%; 
                margin-top: 20px; 
                border-collapse: collapse;
            }
            th { 
                color: #ff2fd4; 
                text-align: left;
                padding: 12px 8px;
                border-bottom: 2px solid #7a00ff;
            }
            td { 
                padding: 12px 8px; 
                border-bottom: 1px solid #7a00ff40;
            }
            tr:hover {
                background: #1d0030;
            }
            .delete-btn {
                background: #ff2fd4;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                text-decoration: none;
                font-size: 12px;
            }
            .delete-btn:hover {
                background: #ff4fdb;
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #b366ff;
                text-decoration: none;
                padding: 10px 20px;
                border: 1px solid #7a00ff;
                border-radius: 8px;
            }
            .back-link:hover {
                background: #7a00ff40;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ AURORA SHIELD</h1>
            
            <div class="card">
                <h2>📋 GERENCIAR CONTATOS DE CONFIANÇA</h2>
                
                <form method="POST" action="/adicionar-contato">
                    <div class="form-group">
                        <input type="text" name="name" placeholder="Nome completo" required>
                        <input type="text" name="phone" placeholder="Telefone (com DDD)" required>
                        <input type="text" name="relationship" placeholder="Parentesco (ex: Irmã, Mãe)">
                        <button type="submit">➕ ADICIONAR</button>
                    </div>
                </form>
                
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Nome</th>
                        <th>Telefone</th>
                        <th>Relação</th>
                        <th>Ação</th>
                    </tr>
    """
    
    conn = get_db()
    contacts = conn.execute("SELECT * FROM contacts ORDER BY name").fetchall()
    
    for c in contacts:
        html += f"""
        <tr>
            <td>#{c['id']}</td>
            <td><strong>{c['name']}</strong></td>
            <td>{c['phone']}</td>
            <td>{c['relationship'] or '—'}</td>
            <td>
                <a href="/apagar-contato/{c['id']}" class="delete-btn" onclick="return confirm('Tem certeza que deseja excluir {c['name']}?')">🗑️ Excluir</a>
            </td>
        </tr>
        """
    
    conn.close()
    
    html += """
                </table>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/" class="back-link">← VOLTAR AO INÍCIO</a>
                    <a href="/mulher" class="back-link" style="margin-left: 10px;">👩 IR PARA MULHER</a>
                    <a href="/confidant" class="back-link" style="margin-left: 10px;">👥 IR PARA CONFIDANTE</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/apagar-contato/<int:id>")
def apagar_contato(id):
    """Apaga um contato específico pelo ID"""
    try:
        conn = get_db()
        
        # Verificar se o contato existe
        contato = conn.execute("SELECT name FROM contacts WHERE id = ?", (id,)).fetchone()
        
        if contato:
            conn.execute("DELETE FROM contacts WHERE id = ?", (id,))
            conn.commit()
            print(f"✅ Contato {contato['name']} (ID: {id}) apagado com sucesso!")
        else:
            print(f"❌ Contato ID {id} não encontrado!")
            
        conn.close()
        return redirect("/gerenciar-contatos?success=1")
    except Exception as e:
        print(f"❌ Erro ao apagar: {str(e)}")
        return f"<h1 style='color:red'>Erro ao apagar: {str(e)}</h1><p><a href='/gerenciar-contatos'>Voltar</a></p>"

@app.route("/adicionar-contato", methods=["POST"])
def adicionar_contato():
    """Adiciona um novo contato"""
    try:
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        relationship = request.form.get("relationship", "").strip()
        
        if not name or not phone:
            return "Nome e telefone são obrigatórios!", 400
        
        conn = get_db()
        conn.execute(
            "INSERT INTO contacts (name, phone, relationship) VALUES (?, ?, ?)",
            (name, phone, relationship)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Contato {name} adicionado com sucesso!")
        return redirect("/gerenciar-contatos?success=1")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar: {str(e)}")
        return f"<h1 style='color:red'>Erro ao adicionar: {str(e)}</h1><p><a href='/gerenciar-contatos'>Voltar</a></p>"

# ============================================
# ROTA DE TESTE DA SIRENE - VERSÃO COM SOM REAL
# ============================================

@app.route("/testar-sirene")
def testar_sirene_direto():
    """Página para testar a sirene real manualmente"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste de Sirene Real - Aurora Shield</title>
        <style>
            body { 
                background: #0a0015; 
                color: white; 
                font-family: Arial; 
                text-align: center; 
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: #140022;
                padding: 30px;
                border-radius: 30px;
                box-shadow: 0 0 50px #7a00ff;
            }
            h1 {
                background: linear-gradient(45deg, #ff2fd4, #7a00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 36px;
                margin-bottom: 30px;
            }
            .sirene-btn { 
                background: linear-gradient(45deg, #ff2fd4, #7a00ff);
                color: white;
                border: none;
                padding: 20px 40px;
                font-size: 24px;
                font-weight: bold;
                border-radius: 50px;
                cursor: pointer;
                margin: 10px;
                transition: 0.3s;
                box-shadow: 0 0 20px #ff2fd4;
                width: 250px;
            }
            .sirene-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 0 40px #ff2fd4;
            }
            .stop-btn {
                background: #ff2fd4;
            }
            .info {
                margin-top: 30px;
                color: #b366ff;
                font-size: 14px;
                background: #1d0030;
                padding: 20px;
                border-radius: 15px;
            }
            .back-link {
                display: inline-block;
                margin: 10px;
                color: #b366ff;
                text-decoration: none;
                padding: 10px 20px;
                border: 1px solid #7a00ff;
                border-radius: 8px;
            }
            .back-link:hover {
                background: #7a00ff40;
            }
            .data-hora {
                color: #00ff88;
                font-size: 18px;
                margin: 20px 0;
            }
            .status-audio {
                margin: 15px 0;
                padding: 10px;
                border-radius: 8px;
                font-weight: bold;
            }
            .sucesso {
                background: rgba(0,255,0,0.2);
                border: 1px solid #00ff88;
                color: #00ff88;
            }
            .erro {
                background: rgba(255,0,0,0.2);
                border: 1px solid #ff2fd4;
                color: #ff2fd4;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔊 TESTE DE SIRENE REAL</h1>
            
            <div class="data-hora" id="dataHora"></div>
            
            <div id="statusAudio" class="status-audio"></div>
            
            <button onclick="tocarSirene()" class="sirene-btn">🔊 TOCAR SIRENE REAL</button>
            <button onclick="pararSirene()" class="sirene-btn stop-btn">⏹️ PARAR</button>
            
            <!-- ÁUDIO DA SIRENE REAL - ARQUIVO LOCAL -->
            <audio id="sirene" loop preload="auto">
                <source src="/static/sounds/sirene-real.mp3" type="audio/mpeg">
            </audio>
            
            <div class="info">
                <p>✅ <strong>Instruções:</strong></p>
                <p>1. Clique em "TOCAR SIRENE REAL" - você deve ouvir uma SIRENE DE VERDADE</p>
                <p>2. Se não ouvir, clique em "PARAR" e tente novamente</p>
                <p>3. Verifique se o volume do computador está ativado</p>
                <p>4. O arquivo de áudio está no servidor: /static/sounds/sirene-real.mp3</p>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/confidant" class="back-link">← VOLTAR AO PAINEL</a>
                <a href="/" class="back-link">🏠 INÍCIO</a>
            </div>
        </div>
        
        <script>
            // Atualizar data/hora
            function atualizarDataHora() {
                let agora = new Date();
                let dia = String(agora.getDate()).padStart(2, '0');
                let mes = String(agora.getMonth() + 1).padStart(2, '0');
                let ano = agora.getFullYear();
                let hora = String(agora.getHours()).padStart(2, '0');
                let min = String(agora.getMinutes()).padStart(2, '0');
                let seg = String(agora.getSeconds()).padStart(2, '0');
                
                document.getElementById('dataHora').innerHTML = 
                    `📅 Data/Hora atual: ${dia}/${mes}/${ano} ${hora}:${min}:${seg}`;
            }
            
            setInterval(atualizarDataHora, 1000);
            atualizarDataHora();
            
            // Áudio da sirene real
            let audio = document.getElementById('sirene');
            let timeoutSirene = null;
            let statusDiv = document.getElementById('statusAudio');
            
            function tocarSirene() {
                if (timeoutSirene) {
                    clearTimeout(timeoutSirene);
                }
                
                audio.currentTime = 0;
                audio.play()
                    .then(() => {
                        statusDiv.innerHTML = '🔊 SIRENE REAL TOCANDO!';
                        statusDiv.className = 'status-audio sucesso';
                        
                        timeoutSirene = setTimeout(() => {
                            audio.pause();
                            audio.currentTime = 0;
                            statusDiv.innerHTML = '🔇 Sirene parada automaticamente';
                            statusDiv.className = 'status-audio';
                        }, 5000);
                    })
                    .catch(erro => {
                        console.error('Erro:', erro);
                        statusDiv.innerHTML = '❌ ERRO: ' + erro.message + '. Verifique se o arquivo sirene-real.mp3 existe na pasta /static/sounds/';
                        statusDiv.className = 'status-audio erro';
                    });
            }
            
            function pararSirene() {
                audio.pause();
                audio.currentTime = 0;
                if (timeoutSirene) {
                    clearTimeout(timeoutSirene);
                }
                statusDiv.innerHTML = '🔇 Sirene parada';
                statusDiv.className = 'status-audio';
            }
            
            // Verificar se o áudio carregou
            audio.addEventListener('loadeddata', function() {
                statusDiv.innerHTML = '✅ Arquivo de sirene carregado com sucesso!';
                statusDiv.className = 'status-audio sucesso';
            });
            
            audio.addEventListener('error', function() {
                statusDiv.innerHTML = '❌ ERRO: Arquivo de áudio não encontrado. Coloque sirene-real.mp3 na pasta /static/sounds/';
                statusDiv.className = 'status-audio erro';
            });
            
            // Pré-carregar áudio
            audio.load();
        </script>
    </body>
    </html>
    """

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
        conn.close()
        
        html = "<h1 style='color:green'>✅ SISTEMA FUNCIONANDO!</h1>"
        html += f"<p>🚨 Alertas no banco: {alerts['total']}</p>"
        html += f"<p>👥 Contatos cadastrados: {len(contacts)}</p>"
        html += "<h3>Contatos:</h3><ul>"
        for c in contacts:
            html += f"<li><strong>{c['name']}</strong> - {c['phone']} ({c['relationship']})</li>"
        html += "</ul>"
        html += '<p><a href="/">Voltar ao início</a> | <a href="/mulher">Ir para Mulher</a> | <a href="/confidant">Ir para Confidante</a> | <a href="/gerenciar-contatos">Gerenciar Contatos</a> | <a href="/testar-sirene">Testar Sirene</a></p>'
        return html
    except Exception as e:
        return f"<h1 style='color:red'>❌ ERRO: {str(e)}</h1>"

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🛡️ AURORA-SHIELD INICIADO COM SUCESSO!")
    print("="*70)
    print("\n📌 LINKS DISPONÍVEIS:")
    print("   • Página inicial: /")
    print("   • Mulher (direto): /mulher")
    print("   • Confidante (público): /confidant")
    print("   • Gerenciar contatos: /gerenciar-contatos")
    print("   • Testar sirene: /testar-sirene")
    print("   • Diagnóstico: /diagnostico")
    print("\n👥 Contatos demo:")
    print("   • CLECI (Irmã)")
    print("   • MARIA (Mãe)")
    print("   • JOÃO (Pai)")
    print("\n✅ Sistema completo com SIRENE REAL!")
    print("="*70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)