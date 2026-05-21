let rowCount = 0;
// Função universal de copiar (melhor compatibilidade)
// Substitua toda a função copyToClipboard por esta:
function copyToClipboard(text, btnElement) {
    if (!text || text.trim() === "") {
        alert("Nada para copiar!");
        return;
    }

    const btn = btnElement;
    if (!btn) {
        console.error("Botão não encontrado para feedback");
        fallbackCopy(text);
        return;
    }

    const originalText = btn.textContent;
    const originalColor = btn.style.background;

    // Tenta Clipboard API primeiro
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showSuccess(btn, originalText, originalColor);
        }).catch(() => {
            fallbackCopy(text, btn, originalText, originalColor);
        });
    } else {
        fallbackCopy(text, btn, originalText, originalColor);
    }
}

function showSuccess(btn, originalText, originalColor) {
    btn.textContent = "✅ Copiado!";
    btn.style.background = "#28a745";
    btn.style.transition = "all 0.2s";

    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = originalColor || "#0066cc";
    }, 2000);
}

function fallbackCopy(text, btn, originalText, originalColor) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand("copy");
        showSuccess(btn, originalText, originalColor);
    } catch (err) {
        console.error("Erro ao copiar:", err);
        alert("Não foi possível copiar automaticamente.\n\nCopie manualmente:\n\n" + text);
    }

    document.body.removeChild(textarea);
}

function createRow() {
    rowCount++;
    const container = document.getElementById('items-container');
    
    const row = document.createElement('div');
    row.className = 'item-row';
    row.id = `row-${rowCount}`;
    row.innerHTML = `
        <div>
            <label>Posição (opcional)</label>
            <input type="text" class="posicao" placeholder="Ex: A1.02 ou Motor">
        </div>

        <div>
            <label>Código de Fábrica</label>
            <input type="text" class="codfab" placeholder="Ex: 9302130138" style="text-transform: uppercase;">
        </div>
        
        <div>
            <label>Quantidade</label>
            <div class="quantity-wrapper" style="display: flex; align-items: center; gap: 5px;">
                <button type="button" class="qty-btn minus" style="width: 40px; height: 40px; font-size: 18px;">–</button>
                <input type="number" class="quantidade" value="1" min="1" style="width: 80px; text-align: center; font-size: 16px;">
                <button type="button" class="qty-btn plus" style="width: 40px; height: 40px; font-size: 18px;">+</button>
            </div>
        </div>
        
        <div>
            <button type="button" class="remove-btn" onclick="removeRow(${rowCount})" 
                    style="padding: 8px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                🗑
            </button>
        </div>
    `;
    
    container.appendChild(row);
    
    // Adiciona eventos para os botões + e -
    const minusBtn = row.querySelector('.minus');
    const plusBtn = row.querySelector('.plus');
    const qtyInput = row.querySelector('.quantidade');
    
    minusBtn.addEventListener('click', () => {
        let value = parseInt(qtyInput.value);
        if (value > 1) qtyInput.value = value - 1;
    });
    
    plusBtn.addEventListener('click', () => {
        let value = parseInt(qtyInput.value);
        qtyInput.value = value + 1;
    });
    
    // Validação ao digitar
    qtyInput.addEventListener('input', () => {
        let value = qtyInput.value.replace(/[^0-9]/g, ''); // só números
        if (value === '' || parseInt(value) < 1) {
            qtyInput.value = 1;
        } else {
            qtyInput.value = parseInt(value);
        }
    });
    
    // Foco no campo de código
    row.querySelector('.codfab').focus();
}

function removeRow(id) {
    const row = document.getElementById(`row-${id}`);
    if (row) row.remove();
}

document.getElementById('add-row').addEventListener('click', createRow);

// Verificar todas
document.getElementById('check-all').addEventListener('click', async () => {
    const rows = document.querySelectorAll('.item-row');
    const resultsDiv = document.getElementById('results');
    
    if (rows.length === 0) {
        alert("Adicione pelo menos uma peça!");
        return;
    }

    resultsDiv.innerHTML = '<p style="text-align:center; color:#666;">Consultando o sistema...</p>';

    const items = [];
    rows.forEach(row => {
        const codfab = row.querySelector('.codfab').value.trim().toUpperCase();
        const quantidade = parseInt(row.querySelector('.quantidade').value);
        const posicao = row.querySelector('.posicao') ? row.querySelector('.posicao').value.trim() : '';
        
        if (codfab) {
            items.push({ 
                codfab, 
                quantidade, 
                posicao 
            });
        }
    });

    if (items.length === 0) {
        alert("Preencha pelo menos um código de fábrica!");
        return;
    }

    try {
        const response = await fetch('/verificar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items })
        });

        const data = await response.json();

        let html = `
            <h2>✅ Resultado da Consulta</h2>
        `;

        let textoEcoCentauro = "";
        let textoKanban = "";

        data.results.forEach(item => {
            let status = '';
            let statusText = '';

            if (!item.cadastrado) {
                status = `<span style="color:red">Não cadastrado</span>`;
                statusText = "(NÃO CADASTRADO)";
            } else if (item.disponivel >= item.quantidade) {
                status = `<span style="color:green">✅ Disponível</span>`;
                statusText = "✅";
            } else if (item.disponivel > 0) {
                status = `<span style="color:orange">⚠️ Parcial (${item.disponivel})</span>`;
                statusText = "⚠️";
            } else {
                status = `<span style="color:red">❌ Sem estoque</span>`;
                statusText = "❌";
            }

            html += `
                <div class="result-item">
                    <strong>${item.codfab}</strong> — 
                    ${item.descricao || '<em>Não encontrado</em>'} 
                    <br>
                    <small>
                        ${item.posicao ? `Posição: <b>${item.posicao}</b> | ` : ''}
                        Solicitado: <b>${item.quantidade}</b> | 
                        Disponível: <b>${item.disponivel}</b> | ${status}
                    </small>
                </div>
            `;

            if (item.cadastrado && item.descricao) {
                const qtd = parseInt(item.quantidade);
                const posicao = item.posicao ? item.posicao.trim() : '';

                // === Texto EcoCentauro (formato atual) ===
                if (qtd > 1) {
                    textoEcoCentauro += `(x${qtd}) ${item.descricao}\n`;
                } else {
                    textoEcoCentauro += `${item.descricao}\n`;
                }

                // === Texto Kanban ===
                let linhaKanban = '';
                if (posicao) {
                    linhaKanban += `Posição: ${posicao} - `;
                }
                if (qtd > 1) {
                    linhaKanban += `(x${qtd}) `;
                }
                linhaKanban += `${item.descricao} ${statusText}\n`;
                
                textoKanban += linhaKanban;
            }
        });

        // Botão de copiar
        html += `
            <div style="margin-top: 25px; text-align: center; display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                <button id="btn-ecocentauro" 
                        style="padding: 12px 20px; font-size: 16px; background:#0066cc; color:white; border:none; border-radius:6px; cursor:pointer;">
                    📋 Copiar Texto (EcoCentauro)
                </button>
                
                <button id="btn-kanban" 
                        style="padding: 12px 20px; font-size: 16px; background:#28a745; color:white; border:none; border-radius:6px; cursor:pointer;">
                    📋 Copiar Texto (Kanban)
                </button>
            </div>
        `;

        resultsDiv.innerHTML = html;

        // Eventos dos botões
        setTimeout(() => {
            const btnEco = document.getElementById('btn-ecocentauro');
            const btnKanban = document.getElementById('btn-kanban');

            if (btnEco) {
                btnEco.addEventListener('click', () => copyToClipboard(textoEcoCentauro.trim(), btnEco));
            }
            if (btnKanban) {
                btnKanban.addEventListener('click', () => copyToClipboard(textoKanban.trim(), btnKanban));
            }
        }, 100);

    } catch (err) {
        resultsDiv.innerHTML = `<p style="color:red; text-align:center;">Erro na comunicação: ${err.message}</p>`;
    }
});

// Inicia com uma linha
window.onload = () => {
    createRow();
};
