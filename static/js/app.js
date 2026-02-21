let timer = null;

function startPress(){
 timer = setTimeout(enviarAlerta,2000);
}

function cancelPress(){
 clearTimeout(timer);
}

function enviarAlerta(){

 navigator.geolocation.getCurrentPosition(pos=>{

   const alerta = {
     nome: document.getElementById("nome").value,
     mensagem: document.getElementById("mensagem").value,
     lat: pos.coords.latitude,
     lng: pos.coords.longitude,
     data: new Date().toLocaleString()
   };

   localStorage.setItem("ultimo_alerta", JSON.stringify(alerta));

   alert("ALERTA ENVIADO COM SUCESSO!");
 });

}

function reiniciar(){
 document.getElementById("nome").value="";
 document.getElementById("mensagem").value="";
}

function limpar(){
 document.getElementById("mensagem").value="";
}

function sair(){
 window.close();
}