# 🌸 AURORA - MULHER SEGURA

![Aurora Logo](https://img.icons8.com/fluency/96/null/woman.png)

## 🚨 **SISTEMA DE SEGURANÇA FEMININA COM BOTÃO DE PÂNICO**

Aurora é um aplicativo web de emergência desenvolvido para oferecer segurança e proteção para mulheres em situações de risco. Com um botão de pânico de fácil acesso, o sistema notifica instantaneamente pessoas de confiança com a localização exata da vítima.

---

## ✨ **CARACTERÍSTICAS PRINCIPAIS**

### 🛡️ **PARA MULHERES**
- **Botão de Pânico SOS** com ativação por toque prolongado
- **Compartilhamento automático de localização** via GPS
- **Seleção rápida do tipo de situação** (violência física, agressão verbal, perseguição)
- **Mensagem personalizada** para descrever a emergência
- **Interface roxa** com design acolhedor e intuitivo
- **Histórico completo** de todos os alertas enviados

### 👥 **PARA PESSOAS DE CONFIANÇA**
- **Painel público** (acesso imediato sem login para agilizar atendimento)
- **Sirene automática** que toca ao receber novo alerta
- **Mapa interativo** com localização exata da emergência
- **Informações detalhadas** (nome, situação, mensagem, horário)
- **Histórico dos últimos alertas**
- **Interface vermelha pulsante** em situação de emergência

### 📱 **RECURSOS TÉCNICOS**
- **PWA (Progressive Web App)** - pode ser instalado como app no celular
- **Responsivo** - funciona perfeitamente em smartphones, tablets e computadores
- **Geolocalização em tempo real**
- **Sirene de emergência** com alerta sonoro
- **Sistema de login seguro** com hash de senhas
- **Banco de dados SQLite** (pronto para PostgreSQL em produção)

---

## 🎯 **OBJETIVO DO PROJETO**

O Aurora nasceu da necessidade de criar uma ferramenta **rápida, acessível e eficaz** para mulheres em situação de vulnerabilidade. Diferente de aplicativos convencionais que exigem cadastro complexo, o Aurora prioriza a **VELOCIDADE** no momento do perigo.

A pessoa de confiança tem acesso **PÚBLICO E IMEDIATO** ao painel de alertas, eliminando barreiras de login quando cada segundo conta.

---

## 🖼️ **CAPTURAS DE TELA**

| Painel da Mulher | Painel do Confidante |
|------------------|----------------------|
| Botão SOS em destaque | Alerta com mapa e sirene |
| Interface roxa acolhedora | Interface vermelha em emergência |

---

## 🚀 **TECNOLOGIAS UTILIZADAS**

- **Backend:** Python + Flask
- **Frontend:** HTML5, CSS3, JavaScript
- **Banco de Dados:** SQLite (desenvolvimento) / PostgreSQL (produção)
- **Autenticação:** Sessões Flask + Hash de senhas (Werkzeug)
- **Mapas:** OpenStreetMap (embed)
- **PWA:** Manifest.json + Service Worker
- **Deploy:** Render / PythonAnywhere / Qualquer servidor Python

---

## 📦 **INSTALAÇÃO LOCAL**

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/aurora-mulher-segura.git

# Entre na pasta
cd aurora-mulher-segura

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Execute o aplicativo
python app.py

# Acesse no navegador
http://localhost:5000
```

---

## 🔑 **DADOS DE ACESSO (DEMO)**

| Tipo | Email | Senha |
|------|-------|-------|
| 👩 Mulher | `ana@demo.com` | `123456` |
| 👥 Confidante | **Acesso público** | **Sem senha** |

---

## 🌐 **DEPLOY NO RENDER**

Este projeto está configurado para deploy fácil no [Render](https://render.com):

1. Faça fork deste repositório
2. No Render, clique em "New Web Service"
3. Conecte seu GitHub e escolha o repositório
4. Use os comandos:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `gunicorn app:app`
5. Pronto! Seu site estará online em minutos

---

## 📁 **ESTRUTURA DO PROJETO**

```
aurora-mulher-segura/
├── app.py                 # Aplicação principal Flask
├── requirements.txt       # Dependências
├── manifest.json          # Configuração PWA
├── service-worker.js      # Service Worker
├── .gitignore             # Arquivos ignorados
├── render.yaml            # Configuração do Render
├── static/                # Arquivos estáticos
│   ├── css/               # Estilos
│   ├── js/                # Scripts
│   └── sounds/            # Sons de sirene
└── templates/             # Páginas HTML
    ├── index.html
    ├── login.html
    ├── register.html
    ├── mulher.html
    ├── confidant.html
    ├── contacts.html
    └── history.html
```

---

## ⚠️ **SEGURANÇA**

- ✅ Senhas armazenadas com **hash** (Werkzeug)
- ✅ Sessões seguras com chave aleatória
- ✅ Proteção contra SQL Injection
- ✅ HTTPS obrigatório em produção
- ✅ CORS configurado
- ✅ Debug desabilitado em produção

---

## 🚧 **PRÓXIMOS PASSOS / MELHORIAS**

- [ ] Envio de SMS para pessoas de confiança
- [ ] Notificações push em tempo real
- [ ] Integração com WhatsApp
- [ ] Banco PostgreSQL para dados persistentes
- [ ] Modo escuro
- [ ] Múltiplos idiomas
- [ ] Cadastro de múltiplos contatos de confiança
- [ ] Estatísticas de uso

---

## 📄 **LICENÇA**

Este projeto está sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🤝 **CONTRIBUIÇÕES**

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Enviar pull requests

---

## 📞 **CONTATO**

- **Autor:** [Seu Nome]
- **Email:** [seu-email@example.com]
- **LinkedIn:** [Seu LinkedIn]
- **Projeto:** [https://github.com/seu-usuario/aurora-mulher-segura]

---

## ⭐ **APOIE O PROJETO**

Se este projeto foi útil para você, deixe uma ⭐ no GitHub!

---

**🌸 Aurora - Proteção Feminina 24 horas 🌸**

---

## 🎯 **COMO USAR ESTA DESCRIÇÃO:**

### **1. No GitHub:**
- Copie todo o texto acima
- Vá até seu repositório no GitHub
- Clique em "About" (ícone de engrenagem)
- Cole na descrição
- Ou edite o arquivo `README.md`
no GitHub terá uma descrição profissional, completa e atraente! 🚀
