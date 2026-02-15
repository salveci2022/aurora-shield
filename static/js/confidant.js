// Variáveis globais
let lastId = 0;
let audioEnabled = true; // MUDADO PARA TRUE POR PADRÃO
let currentAlert = null;
let audioPlayed = false; // Para não repetir o mesmo alerta

// Elementos DOM
const status = document.getElementById('status');
const alertBox = document.getElementById('alertBox');
const infoNome = document.getElementById('infoNome');
const infoSit = document.getElementById('infoSit');
const infoMsg = document.getElementById('infoMsg');
const infoData = document.getElementById('infoData');
const map = document.getElementById('map');
const noLocation = document.getElementById('noLocation');
const siren = document.getElementById('siren');
const historyItems = document.getElementById('historyItems');

// Configurar áudio para tocar automaticamente
siren.load();
siren.volume = 0.8;

// Função para tentar tocar áudio (requer interação do usuário)
function playSiren() {
    if (!audioEnabled) return;
    
    siren.currentTime = 0;
    siren.play()
        .then(() => {
            console.log('Sirene tocando');
            // Toca em loop até ser parada
            siren.loop = true;
        })
        .catch(e => {
            console.log('Áudio bloqueado pelo navegador:', e);
            // Se falhou, tenta novamente após interação do usuário
            document.addEventListener('click', function enableAudioOnce() {
                siren.play()
                    .then(() => {
                        siren.loop = true;
                        document.removeEventListener('click', enableAudioOnce);
                    })
                    .catch(() => {});
            }, { once: true });
        });
}

// Função para parar sirene
function stopSiren() {
    siren.pause();
    siren.currentTime = 0;
    siren.loop = false;
}

// Botões
document.getElementById('btnAudio').onclick = () => {
    audioEnabled = !audioEnabled;
    if (audioEnabled) {
        document.getElementById('btnAudio').textContent = '🔊 Som Ativo';
        document.getElementById('btnAudio').style.background = '#00ff88';
        if (currentAlert) playSiren();
    } else {
        document.getElementById('btnAudio').textContent = '🔇 Som Mudo';
        document.getElementById('btnAudio').style.background = '#ff2fd4';
        stopSiren();
    }
};

document.getElementById('btnClear').onclick = () => {
    currentAlert = null;
    audioPlayed = false;
    alertBox.className = 'alert';
    alertBox.textContent = '⏳ Aguardando alertas...';
    status.textContent = '🟢 Monitorando';
    infoNome.textContent = '—';
    infoSit.textContent = '—';
    infoMsg.textContent = '—';
    infoData.textContent = '—';
    map.style.display = 'none';
    noLocation.style.display = 'flex';
    stopSiren();
};

document.getElementById('btnReset').onclick = () => {
    lastId = 0;
    audioPlayed = false;
    stopSiren();
    fetchAlerts();
};

// Buscar alertas
async function fetchAlerts() {
    try {
        const r = await fetch('/history_json', {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache' }
        });
        const data = await r.json();
        
        // Atualizar histórico
        if (data.length > 0) {
            let history = '';
            for (let i = 0; i < Math.min(data.length, 5); i++) {
                history += `<div class="history-item">📢 ${data[i].date} - ${data[i].name || 'Alerta'}</div>`;
            }
            if (historyItems) historyItems.innerHTML = history;
        }
        
        if (data.length === 0) return;
        
        const latest = data[0];
        
        if (latest.id !== lastId) {
            lastId = latest.id;
            currentAlert = latest;
            audioPlayed = false;
            
            // Atualizar UI
            alertBox.className = 'alert active';
            alertBox.textContent = '🚨 ALERTA DE EMERGÊNCIA!';
            status.textContent = '🔴 ALERTA ATIVO';
            
            infoNome.textContent = latest.name || 'Anônimo';
            infoSit.textContent = latest.situation || 'Emergência';
            infoMsg.textContent = latest.message || '—';
            infoData.textContent = latest.date || '—';
            
            // Mapa
            if (latest.lat && latest.lng && latest.lat !== 'null' && latest.lng !== 'null') {
                const lat = parseFloat(latest.lat);
                const lng = parseFloat(latest.lng);
                
                if (!isNaN(lat) && !isNaN(lng)) {
                    map.src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng-0.01},${lat-0.01},${lng+0.01},${lat+0.01}&layer=mapnik&marker=${lat},${lng}`;
                    map.style.display = 'block';
                    noLocation.style.display = 'none';
                } else {
                    map.style.display = 'none';
                    noLocation.style.display = 'flex';
                }
            } else {
                map.style.display = 'none';
                noLocation.style.display = 'flex';
            }
            
            // Tocar sirene automaticamente se for um novo alerta
            if (audioEnabled && !audioPlayed) {
                audioPlayed = true;
                playSiren();
            }
        }
    } catch (e) {
        console.log('Erro ao buscar alertas');
    }
}

// Iniciar com áudio habilitado
document.addEventListener('DOMContentLoaded', () => {
    console.log('Confidante carregado - Áudio automático ativado');
    
    // Tenta tocar um som de teste (alguns navegadores bloqueiam)
    siren.load();
    
    // Se o navegador bloquear, aguarda interação
    document.body.addEventListener('click', function initAudio() {
        if (audioEnabled && currentAlert && !audioPlayed) {
            playSiren();
        }
    }, { once: true });
    
    // Iniciar polling
    fetchAlerts();
    setInterval(fetchAlerts, 3000);
});