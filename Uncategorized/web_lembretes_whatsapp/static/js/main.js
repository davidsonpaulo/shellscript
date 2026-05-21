let entradas = [];
let entradaEditando = null;

async function carregarEntradas() {
  const res = await fetch('/api/entradas');
  entradas = await res.json();
  renderTabela();
}

let templatesDisponiveis = [];

async function carregarTemplates() {
  const res = await fetch('/api/templates');
  templatesDisponiveis = await res.json();
}

function renderTabela() {
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';

  const sorted = [...entradas].sort((a, b) => new Date(a.proximo_envio) - new Date(b.proximo_envio));

  sorted.forEach(ent => {
    const tr = document.createElement('tr');
    tr.className = ent.hoje ? 'due-today' : 'future';

    let options = templatesDisponiveis.map(t => 
      `<option value="${t}" ${t === ent.template ? 'selected' : ''}>${t}</option>`
    ).join('');

    tr.innerHTML = `
      <td class="px-6 py-4 font-medium">
        <div class="flex items-center gap-2">
          ${ent.os}
          ${ent.os_fechada ? 
            `<span title="OS ${ent.os} foi fechada em ${ent.data_fechamento || 'data desconhecida'}" 
                   class="text-green-600 cursor-help">✅</span>` : 
            `<span title="OS ${ent.os} ainda está aberta" 
                   class="text-amber-600 cursor-help">⏳</span>`}
        </div>
      </td>

      <td class="px-6 py-4">
        <a href="whatsapp://send?phone=${ent.telefone}" 
           target="_blank"
           title="Abrir conversa no WhatsApp com ${ent.nome}"
           class="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer transition">
          ${ent.nome}
        </a>
      </td>

      <td class="px-6 py-4">
        <select onchange="selecionarNovoTemplate(${ent.idx_linha}, this.value)" 
                class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500">
          ${options}
        </select>
      </td>

      <td class="px-6 py-4">
        <button onclick="editarParametros(${ent.idx_linha})" 
                class="text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 p-3 rounded-xl transition">
          <i class="fas fa-edit fa-lg"></i>
        </button>
      </td>

      <!-- resto da tabela igual... -->
      <td class="px-6 py-4">
        <div class="flex items-center gap-1">
          <button onclick="alterarIntervalo(${ent.idx_linha}, -1)" class="w-8 h-8 flex items-center justify-center hover:bg-gray-200 rounded-lg">-</button>
          <span class="w-10 text-center font-semibold">${ent.intervalo}</span>
          <button onclick="alterarIntervalo(${ent.idx_linha}, 1)" class="w-8 h-8 flex items-center justify-center hover:bg-gray-200 rounded-lg">+</button>
        </div>
      </td>

      <td class="px-6 py-4">
          <input type="date" value="${ent.proximo_envio}" 
          onchange="mudouDataProximo(${ent.idx_linha}, this.value)"
          class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500">
      </td>

      <td class="px-4 py-4">
        <div class="flex items-center justify-center gap-1">
          <button onclick="previewMensagem(${ent.idx_linha})" title="Ver Preview" 
                  class="text-blue-600 hover:text-blue-700 p-2 hover:bg-blue-50 rounded-lg transition">
            <i class="fas fa-magnifying-glass"></i>
          </button>
          <button onclick="enviarMensagem(${ent.idx_linha})" title="Enviar agora" 
                  class="text-green-600 hover:text-green-700 p-2 hover:bg-green-50 rounded-lg transition">
            <i class="fas fa-paper-plane"></i>
          </button>
          <button onclick="desativarEntrada(${ent.idx_linha})" title="Desativar" 
                  class="text-orange-600 hover:text-orange-700 p-2 hover:bg-orange-50 rounded-lg transition">
            <i class="fas fa-circle-pause"></i>
          </button>
          <button onclick="excluirEntrada(${ent.idx_linha})" title="Excluir" 
                  class="text-red-600 hover:text-red-700 p-2 hover:bg-red-50 rounded-lg transition">
            <i class="fas fa-ban"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function selecionarNovoTemplate(idx, novoTemplate) {
  const ent = entradas.find(e => e.idx_linha === idx);
  if (!ent) return;

  if (novoTemplate === ent.template) return;

  if (!confirm(`Alterar template de "${ent.template}" para "${novoTemplate}"?`)) {
    carregarEntradas();
    return;
  }

  const res = await fetch('/api/trocar_template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idx, novo_template: novoTemplate })
  });

  const data = await res.json();
  
  if (data.status === "success") {
    alert(data.message);
    
    // Aguarda atualizar os dados antes de abrir o modal
    await carregarEntradas();
    
    // Agora abre o modal com os dados atualizados
    setTimeout(() => editarParametros(idx), 100);
  } else {
    alert("Erro ao alterar template");
    carregarEntradas();
  }
}

// ==================== MODAIS ====================
let previewIdxAtual = null;

async function previewMensagem(idx) {
  previewIdxAtual = idx;   // Salva o idx para poder enviar depois

  const res = await fetch(`/api/preview/${idx}`);
  const data = await res.json();
  
  document.getElementById('previewTitle').textContent = `Preview - ${data.template}`;
  document.getElementById('previewContent').textContent = data.mensagem;
  document.getElementById('modalPreview').classList.remove('hidden');
}

async function enviarDoPreview() {
  if (!previewIdxAtual) return;
  
  fecharModal('modalPreview');
  await enviarMensagem(previewIdxAtual);   // Reusa a função principal de envio
}

function editarParametros(idx) {
  entradaEditando = entradas.find(e => e.idx_linha === idx);
  if (!entradaEditando) return;

  document.getElementById('modalNomeCliente').textContent = 
    `${entradaEditando.nome} → ${entradaEditando.template}`;

  let html = `<div class="space-y-5">`;

  // Variáveis que o template atual realmente usa (baseado na análise do common.py)
  const varsRelevantes = new Set(entradaEditando.obrigatorias || []);
  (entradaEditando.opcionais || []).forEach(v => varsRelevantes.add(v));

  // Sempre incluir OS e CLIENTE
  varsRelevantes.add("OS");
  varsRelevantes.add("CLIENTE");

  // Filtrar os parâmetros salvos para mostrar apenas os relevantes
  Object.keys(entradaEditando.params_dict)
    .filter(key => varsRelevantes.has(key))
    .sort()
    .forEach(key => {
      const value = entradaEditando.params_dict[key] || '';
      
      const isObrigatoria = entradaEditando.obrigatorias ? 
                           entradaEditando.obrigatorias.includes(key) : false;

      html += `
        <div class="flex gap-3 items-start">
          <div class="flex-1">
            <label class="block text-sm font-medium mb-1">
              ${key}
              ${isObrigatoria ? 
                '<span class="ml-2 text-red-600 text-xs font-medium">(obrigatório)</span>' : 
                '<span class="ml-2 text-green-600 text-xs font-medium">(opcional)</span>'}
            </label>
            <input type="text" id="param_${key}" value="${value}" 
                   class="w-full border ${isObrigatoria ? 
                     'border-red-300 focus:border-red-500' : 
                     'border-gray-300 focus:border-blue-500'} 
                   rounded-xl px-4 py-3 focus:outline-none transition">
          </div>
        </div>`;
    });

  html += `</div>`;
  document.getElementById('formParametros').innerHTML = html;
  document.getElementById('modalParametros').classList.remove('hidden');
}

async function salvarParametros() {
  if (!entradaEditando) return;

  const novosParams = {...entradaEditando.params_dict};
  
  Object.keys(novosParams).forEach(key => {
    const input = document.getElementById(`param_${key}`);
    if (input) novosParams[key] = input.value;
  });

  // TODO: Enviar para backend
  const res = await fetch('/api/salvar_parametros', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idx: entradaEditando.idx_linha,
      parametros: novosParams
    })
  });

  alert("✅ Parâmetros salvos com sucesso!");
  fecharModal('modalParametros');
  carregarEntradas();
}

function fecharModal(modalId) {
  document.getElementById(modalId).classList.add('hidden');
}

// ==================== OUTRAS FUNÇÕES ====================
async function enviarMensagem(idx) {
  const ent = entradas.find(e => e.idx_linha === idx);
  if (!ent) return;

  const res = await fetch(`/api/enviar/${idx}`, { method: "POST" });
  const data = await res.json();

  if (data.status !== "success") {
    alert("Erro ao preparar mensagem: " + (data.message || ""));
    return;
  }

  // Abre o WhatsApp diretamente (sem confirmação)
  const textoCodificado = encodeURIComponent(data.mensagem);
  const url = `whatsapp://send?phone=${data.telefone}&text=${textoCodificado}`;
  window.open(url, '_blank');

  // Pequeno delay para dar tempo de o WhatsApp abrir
  await new Promise(resolve => setTimeout(resolve, 800));

  // ÚNICA confirmação importante
  const enviadoSucesso = confirm(`✅ Mensagem aberta no WhatsApp para ${ent.nome}.\n\nVocê enviou a mensagem com sucesso?`);

  if (!enviadoSucesso) {
    alert("❌ Operação cancelada. Nenhuma alteração foi feita.");
    return;
  }

  // Prossegue com one-shot, atualização de data, etc.
  await aplicarAposEnvioSucesso(idx, data.template_atual);
}

async function aplicarAposEnvioSucesso(idx, templateAtual) {
  console.log("🔄 Aplicando pós-envio para idx:", idx);

  const res = await fetch('/api/aplicar_apos_envio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idx: idx, template_atual: templateAtual })
  });

  const result = await res.json();

  if (result.status === "success") {
    let mensagem = "✅ Envio registrado com sucesso!";
    
    if (result.novo_template && result.novo_template !== templateAtual) {
      mensagem += `\n\n🔄 Template alterado automaticamente para: ${result.novo_template}`;
    }
    
    alert(mensagem);
    
    // FORÇA reload completo dos dados antes de abrir o modal
    await carregarEntradas();
    
    // Agora sim abre o modal com os dados atualizados
    if (result.novo_template) {
      setTimeout(() => editarParametros(idx), 300);
    } else {
      carregarEntradas(); // apenas atualiza a tabela
    }
  } else {
    alert("Erro ao registrar envio: " + (result.message || "Desconhecido"));
  }
}

// ==================== FUNÇÕES DE INTERVALO E DATA ====================

async function alterarIntervalo(idx, delta) {
  const ent = entradas.find(e => e.idx_linha === idx);
  if (!ent) return;

  let novoIntervalo = Math.max(1, ent.intervalo + delta);

  if (!confirm(`Alterar intervalo para ${novoIntervalo} dias?`)) return;

  const res = await fetch('/api/salvar_intervalo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idx, intervalo: novoIntervalo })
  });

  const data = await res.json();
  alert(data.message);
  carregarEntradas();
}

async function mudouDataProximo(idx, novaData) {
  const ent = entradas.find(e => e.idx_linha === idx);
  if (!ent) return;

  if (!confirm(`Definir próximo envio para ${novaData}?`)) {
    // Recarrega para voltar ao valor anterior
    carregarEntradas();
    return;
  }

  const res = await fetch('/api/salvar_proximo_envio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idx, proximo_envio: novaData })
  });

  const data = await res.json();
  alert(data.message);
  carregarEntradas();
}

function mudouTemplate(idx, novoTemplate) {
  alert(`Template alterado para ${novoTemplate} (em breve)`);
}

async function excluirEntrada(idx) {
  const ent = entradas.find(e => e.idx_linha === idx);
  if (!ent) return;

  const confirmacao = confirm(`⚠️ Tem certeza que deseja EXCLUIR permanentemente a entrada de ${ent.nome} (OS: ${ent.os})?\n\nEsta ação não pode ser desfeita!`);

  if (!confirmacao) return;

  try {
    const res = await fetch(`/api/excluir/${idx}`, { 
      method: "DELETE" 
    });
    const data = await res.json();

    if (data.status === "success") {
      alert(data.message);
      carregarEntradas(); // Atualiza a tabela
    } else {
      alert("Erro: " + data.message);
    }
  } catch (e) {
    alert("Erro ao excluir entrada.");
  }
}

function desativarEntrada(idx) {
  if (confirm("Desativar esta entrada?")) {
    alert("Entrada desativada (em breve)");
    carregarEntradas();
  }
}

function novaEntrada() {
  let html = `
    <div class="space-y-6">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Telefone (com DDD)</label>
          <input type="text" id="novo_telefone" class="w-full border border-gray-300 rounded-xl px-4 py-3" placeholder="5566991234567">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Nome do Contato</label>
          <input type="text" id="novo_nome" class="w-full border border-gray-300 rounded-xl px-4 py-3">
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium mb-1">Template</label>
        <select id="novo_template" onchange="carregarParametrosNovaEntrada()" 
                class="w-full border border-gray-300 rounded-xl px-4 py-3">
          ${templatesDisponiveis.map(t => `<option value="${t}">${t}</option>`).join('')}
        </select>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Intervalo (dias)</label>
          <input type="number" id="novo_intervalo" value="7" min="1" 
                 class="w-full border border-gray-300 rounded-xl px-4 py-3">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Data da Primeira Execução</label>
          <input type="date" id="nova_data_primeira" value="${new Date().toISOString().split('T')[0]}" 
                 class="w-full border border-gray-300 rounded-xl px-4 py-3">
        </div>
      </div>

      <div id="parametrosNovaEntrada" class="space-y-4 border-t pt-4"></div>
    </div>
  `;

  document.getElementById('formNovaEntrada').innerHTML = html;
  document.getElementById('modalNovaEntrada').classList.remove('hidden');
  
  setTimeout(carregarParametrosNovaEntrada, 150);
}

async function carregarParametrosNovaEntrada() {
  const template = document.getElementById('novo_template').value;
  if (!template) return;

  const container = document.getElementById('parametrosNovaEntrada');
  container.innerHTML = `<p class="text-gray-500 py-4">Carregando campos do template...</p>`;

  try {
    const res = await fetch(`/api/variaveis_template/${template}`);
    const data = await res.json();

    let html = `<h4 class="font-medium text-gray-700 mb-3">Parâmetros</h4><div class="grid grid-cols-2 gap-4">`;

    data.todas.forEach(key => {
      const isObrigatoria = data.obrigatorias.includes(key);
      html += `
        <div>
          <label class="block text-sm font-medium mb-1">
            ${key}
            ${isObrigatoria ? 
              '<span class="text-red-600 text-xs">(obrigatório)</span>' : 
              '<span class="text-green-600 text-xs">(opcional)</span>'}
          </label>
          <input type="text" id="novo_param_${key}" 
                 class="w-full border ${isObrigatoria ? 'border-red-300' : 'border-gray-300'} rounded-xl px-4 py-3 focus:outline-none">
        </div>`;
    });

    html += `</div>`;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<p class="text-red-500">Erro ao carregar parâmetros</p>`;
  }
}

async function salvarNovaEntrada() {
  const telefone = document.getElementById('novo_telefone').value.trim();
  const nome = document.getElementById('novo_nome').value.trim();
  const template = document.getElementById('novo_template').value;
  const intervalo = parseInt(document.getElementById('novo_intervalo').value) || 7;
  const data_primeira = document.getElementById('nova_data_primeira').value;

  if (!telefone || !nome || !template) {
    alert("❌ Telefone, Nome e Template são obrigatórios!");
    return;
  }

  const parametros = {};
  document.querySelectorAll('#parametrosNovaEntrada input').forEach(input => {
    const key = input.id.replace('novo_param_', '');
    parametros[key] = input.value.trim();
  });

  const res = await fetch('/api/nova_entrada', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      telefone, 
      nome, 
      template, 
      parametros, 
      intervalo,
      data_primeira 
    })
  });

  const data = await res.json();
  
  if (data.status === "success") {
    alert(data.message);
    fecharModal('modalNovaEntrada');
    
    await carregarEntradas(); // Atualiza e reordena a lista

    // === Destaca a nova entrada (procura pelo nome + telefone) ===
    setTimeout(() => destacarNovaEntrada(nome, telefone), 300);

    // Pergunta se quer enviar agora
    if (data.pode_enviar_agora && confirm(`✅ Entrada de ${nome} criada com sucesso!\n\nEsta mensagem pode ser enviada hoje.\nDeseja enviar agora?`)) {
      const ultimaIdx = Math.max(...entradas.map(e => e.idx_linha));
      await enviarMensagem(ultimaIdx);
    }
  } else {
    alert("Erro: " + data.message);
  }
}

// Função auxiliar para destacar a nova entrada
function destacarNovaEntrada(nome, telefone) {
  const linhas = document.querySelectorAll('#tbody tr');
  
  for (let tr of linhas) {
    if (tr.textContent.includes(nome) && tr.textContent.includes(telefone)) {
      tr.classList.add('bg-blue-100', 'ring-2', 'ring-blue-400');
      tr.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Remove destaque após 4 segundos
      setTimeout(() => {
        tr.classList.remove('bg-blue-100', 'ring-2', 'ring-blue-400');
      }, 4000);
      break;
    }
  }
}

async function recarregar() {
    if (!confirm("Recarregar templates, snippets e config.txt?")) {
        return;
    }

    try {
        const response = await fetch('/api/reload');
        const data = await response.json();

        if (data.status === "success") {
            alert(data.message);
            // Recarrega a tabela automaticamente
            await carregarEntradas();
        } else {
            alert("Erro: " + data.message);
        }
    } catch (error) {
        alert("Erro ao recarregar: " + error.message);
    }
}

function enviarTodasHoje() { alert("Enviando todas as mensagens de hoje... (em breve)"); }

function fazerBackup() { window.location.href = "/api/backup"; }

async function debugOneShot() {
  const res = await fetch('/api/debug_one_shot');
  const data = await res.json();
  console.log("One-shot configurados:", data);
}

/// Inicialização
document.addEventListener('DOMContentLoaded', async () => {
  await carregarTemplates();   // ← Adicionado
  await carregarEntradas();
});
