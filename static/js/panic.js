// Variáveis para controle do botão
let isSending = false;

function selectTag(el) {
    document.querySelectorAll('.tag').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('statusMessage');
    if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.className = 'status-message ' + type;
        
        setTimeout(() => {
            statusDiv.className = 'status-message';
        }, 5000);
    } else {
        alert(message);
    }
}

function getLocation(options = {}) {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocalização não suportada'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
            ...options
        });
    });
}

async function panic() {
    // Previne múltiplos envios
    if (isSending) {
        showStatus('Enviando alerta anterior...', 'error');
        return;
    }
    
    const name = document.getElementById('name')?.value || 'Usuária';
    const situation = document.querySelector('.tag.active')?.innerText || 'Emergência';
    const message = document.getElementById('message')?.value || '';
    const shareLocation = document.getElementById('shareLocation')?.checked || true;
    
    // Validação básica
    if (!name.trim()) {
        showStatus('Por favor, informe seu nome', 'error');
        return;
    }
    
    // Desabilita botão durante envio
    const btn = document.getElementById('sosButton');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'ENVIANDO...';
    btn.disabled = true;
    isSending = true;
    
    try {
        let lat = null;
        let lng = null;
        
        // Tenta obter localização se autorizado
        if (shareLocation) {
            try {
                const position = await getLocation();
                lat = position.coords.latitude;
                lng = position.coords.longitude;
                console.log('Localização obtida:', lat, lng);
            } catch (geoError) {
                console.warn('Erro ao obter localização:', geoError);
                showStatus('Não foi possível obter localização. Enviando alerta sem localização.', 'error');
            }
        }
        
        // Prepara dados
        const alertData = {
            name: name,
            situation: situation,
            message: message,
            lat: lat,
            lng: lng
        };
        
        console.log('Enviando alerta:', alertData);
        
        // Envia alerta
        const response = await fetch('/api/panic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(alertData)
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'ok') {
            // Sucesso
            showStatus('✅ ALERTA ENVIADO COM SUCESSO!', 'success');
            
            // Vibração (se suportado)
            if (navigator.vibrate) {
                navigator.vibrate([500, 200, 500]);
            }
            
            // Opcional: tocar som de confirmação
            // (pode ser implementado depois)
            
        } else {
            throw new Error(result.message || 'Erro ao enviar alerta');
        }
        
    } catch (error) {
        console.error('Erro detalhado:', error);
        showStatus('❌ Erro ao enviar alerta. Tente novamente.', 'error');
    } finally {
        // Reabilita botão
        btn.innerHTML = originalText;
        btn.disabled = false;
        isSending = false;
    }
}

// Função para testar localização (útil para debug)
async function testLocation() {
    try {
        const position = await getLocation();
        alert(`Localização atual:\nLat: ${position.coords.latitude}\nLng: ${position.coords.longitude}`);
    } catch (error) {
        alert('Erro ao obter localização: ' + error.message);
    }
}

// Adiciona listener para quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    console.log('Panic.js carregado');
    
    // Verifica permissão de localização
    if (navigator.permissions) {
        navigator.permissions.query({ name: 'geolocation' }).then(result => {
            console.log('Permissão de localização:', result.state);
        });
    }
});