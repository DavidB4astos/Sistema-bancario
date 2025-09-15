const fmt = (n) => (n || 0).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});

const ui = {
  saldo: document.getElementById('saldoView'),
  saques: document.getElementById('saquesView'),
  valor: document.getElementById('valorInput'),
  msg: document.getElementById('mensagem'),
  extratoBox: document.getElementById('extratoBox'),
  extratoView: document.getElementById('extratoView'),
  depositarBtn: document.getElementById('depositarBtn'),
  sacarBtn: document.getElementById('sacarBtn'),
  extratoBtn: document.getElementById('extratoBtn'),
  resetBtn: document.getElementById('resetBtn'),
};

function showMsg(texto, tipo='ok'){
  ui.msg.textContent = texto;
  ui.msg.className = `msg ${tipo}`;
  ui.msg.style.display = 'block';
}
function hideMsg(){ ui.msg.style.display='none'; }

function valToNumber(raw){
  if (!raw) return NaN;
  raw = raw.trim().replace(/\s+/g,'').replace('.', '').replace(',', '.');
  return Number(raw);
}

async function loadExtract(){
  const res = await fetch('/api/extract');
  if (!res.ok){
    showMsg('Falha ao carregar extrato.', 'err');
    return;
  }
  const data = await res.json();
  const saldo = data.balance || 0;
  ui.saldo.textContent = fmt(saldo);

  if (!data.operations || data.operations.length === 0){
    ui.extratoView.textContent = 'Não foram realizadas operações.';
  } else {
    const linhas = data.operations.map(o => {
      const tipo = o.type === 'deposit' ? 'Depósito' : 'Saque';
      return `${tipo}: ${fmt(o.amount)} — ${o.created_at}`;
    });
    ui.extratoView.innerHTML = '<ul>' + linhas.map(li => `<li>${li}</li>`).join('') + '</ul>';
  }

  const hoje = new Date().toISOString().slice(0,10);
  const saquesHoje = (data.operations || []).filter(o => o.type === 'withdraw' && (o.created_at||'').startsWith(hoje)).length;
  ui.saques.textContent = String(Math.max(0, 3 - saquesHoje));
}

async function depositar(){
  hideMsg();
  const valor = valToNumber(ui.valor.value);
  if (!(valor > 0)){
    showMsg('Operação falhou! O valor informado é inválido.', 'err');
    return;
  }
  const res = await fetch('/api/deposit', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ amount: valor })
  });
  const data = await res.json();
  if (!res.ok){
    showMsg(data.error || 'Falha no depósito.', 'err');
    return;
  }
  ui.valor.value='';
  showMsg(data.message || 'Depósito realizado.', 'ok');
  await loadExtract();
}

async function sacar(){
  hideMsg();
  const valor = valToNumber(ui.valor.value);
  if (!(valor > 0)){
    showMsg('Operação falhou! O valor informado é inválido.', 'err');
    return;
  }
  const res = await fetch('/api/withdraw', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ amount: valor })
  });
  const data = await res.json();
  if (!res.ok){
    showMsg(data.error || 'Falha no saque.', 'err');
    return;
  }
  ui.valor.value='';
  showMsg(data.message || 'Saque realizado.', 'ok');
  await loadExtract();
}

async function resetar(){
  const res = await fetch('/api/reset', { method:'POST' });
  if (res.ok){
    showMsg('Sistema reiniciado com sucesso.', 'warn');
    await loadExtract();
  } else {
    showMsg('Falha ao reiniciar.', 'err');
  }
}

ui.depositarBtn.addEventListener('click', depositar);
ui.sacarBtn.addEventListener('click', sacar);
ui.extratoBtn.addEventListener('click', async ()=>{
  ui.extratoBox.open = true;
  await loadExtract();
});
ui.resetBtn.addEventListener('click', resetar);
ui.valor.addEventListener('keydown', (e)=>{ if (e.key==='Enter') depositar(); });

loadExtract();
