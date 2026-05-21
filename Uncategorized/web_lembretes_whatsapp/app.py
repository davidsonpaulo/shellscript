from flask import Flask, render_template, jsonify, request, send_file
import os
from datetime import date, timedelta
import zipfile
import io

# No topo, após os outros imports
try:
    from lib.firebird_connect import firebird_connect
    from lib.firebird_connect import load_query  # se existir
except ImportError:
    firebird_connect = None
    print("⚠️ Módulo firebird_connect não encontrado. Check de OS fechada desativado.")

app = Flask(__name__)

# Importar lógica existente
from common import (
    carregar_templates_globais, 
    carregar_snippets_globais,
    carregar_one_shot_templates,
    TEMPLATES, 
    SNIPPETS, 
    ONE_SHOT_TEMPLATES,
    parse_parametros,
    processar_snippets,
    processar_mensagem, 
    pode_enviar,
    extrair_variaveis_e_opcionais   # ← Adicionado
)

carregar_templates_globais()
carregar_snippets_globais()
carregar_one_shot_templates()

def carregar_config():
    if not os.path.exists("config.txt"):
        return []
    with open("config.txt", "r", encoding="utf-8") as f:
        return f.readlines()

def salvar_config(linhas):
    with open("config.txt", "w", encoding="utf-8") as f:
        f.writelines(linhas)

def obter_os_status(os_list):
    """Busca status de múltiplas OS em uma única query"""
    if not os_list or not firebird_connect:
        return {}
    
    os_list = [os_num for os_num in os_list if os_num]
    if not os_list:
        return {}
    
    try:
        con = firebird_connect()
        cur = con.cursor()
        
        # Cria placeholders para IN clause
        placeholders = ','.join(['?'] * len(os_list))
        query = f"""
            SELECT CODIGO, DATAFECHAMENTO 
            FROM TVENPEDIDO 
            WHERE TRIM(LEADING '0' FROM CODIGO) IN ({placeholders})
        """
        cur.execute(query, os_list)
        rows = cur.fetchall()
        
        status = {}
        for row in rows:
            os_num = str(row[0]).lstrip('0')
            fechada = row[1] is not None
            data_fech = row[1].strftime('%d/%m/%Y') if row[1] and hasattr(row[1], 'strftime') else None
            status[os_num] = (fechada, data_fech)
        
        return status
    except Exception as e:
        print(f"Erro no batch OS status: {e}")
        return {}
    finally:
        if 'cur' in locals(): cur.close()
        if 'con' in locals(): con.close()

def obter_entradas():
    linhas = carregar_config()
    entradas = []
    hoje = date.today()

    todas_os = []
    for linha in linhas:
        if not linha.strip() or linha.strip().startswith("TELEFONE"):
            continue
        partes = [p.strip() for p in linha.strip().split("\t")]
        if len(partes) > 3:
            params = parse_parametros(partes[3])
            os_num = params.get("OS", "")
            if os_num:
                todas_os.append(os_num)

    os_status = obter_os_status(todas_os)

    for i, linha in enumerate(linhas):
        if not linha.strip() or linha.strip().startswith("TELEFONE"):
            continue
        partes = [p.strip() for p in linha.strip().split("\t")]
        if len(partes) < 6:
            continue
            
        params_str = partes[3]
        params_dict = parse_parametros(params_str)
        os_num = params_dict.get("OS", "")

        os_fechada = False
        data_fechamento = None
        if os_num:
            status = os_status.get(os_num.lstrip('0'), (False, None))
            os_fechada, data_fechamento = status

        intervalo = 7
        try:
            if "/" in partes[4]:
                intervalo = int(partes[4].split("/")[1])
            ultimo_str = partes[5]
            ultimo = date.fromisoformat(ultimo_str) if ultimo_str else hoje - timedelta(days=1)
            proximo = ultimo + timedelta(days=intervalo)
        except:
            proximo = hoje
            intervalo = 7

        # === NOVO: Informações de obrigatórias/opcionais ===
        template = partes[2]
        opcionais = []
        obrigatorias = []
        if template in TEMPLATES:
            info = extrair_variaveis_e_opcionais(TEMPLATES[template])
            opcionais = info['opcionais']
            obrigatorias = info['obrigatorias']

        entradas.append({
            "id": i,
            "idx_linha": i,
            "telefone": partes[0],
            "nome": partes[1],
            "template": template,
            "parametros_str": params_str,
            "params_dict": params_dict,
            "intervalo": intervalo,
            "ultimo_envio": partes[5],
            "proximo_envio": proximo.isoformat(),
            "hoje": proximo <= hoje,
            "os": os_num,
            "os_fechada": os_fechada,
            "data_fechamento": data_fechamento,
            "opcionais": opcionais,
            "obrigatorias": obrigatorias,
            "linha_original": linha
        })
    return entradas

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/entradas")
def api_entradas():
    return jsonify(obter_entradas())

@app.route("/api/preview/<int:idx>")
def api_preview(idx):
    entradas = obter_entradas()
    ent = next((e for e in entradas if e["idx_linha"] == idx), None)
    if not ent or ent["template"] not in TEMPLATES:
        return jsonify({"error": "Não encontrado"}), 404
    
    mensagem = processar_mensagem(TEMPLATES[ent["template"]], ent["params_dict"])
    return jsonify({
        "template": ent["template"],
        "mensagem": mensagem,
        "nome": ent["nome"]
    })

@app.route("/api/salvar_parametros", methods=["POST"])
def api_salvar_parametros():
    data = request.json
    idx = data.get("idx")
    novos_params = data.get("parametros", {})

    if idx is None:
        return jsonify({"status": "error", "message": "Índice não informado"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    # Reconstruir a linha com novos parâmetros
    linha = linhas[idx]
    partes = [p.strip() for p in linha.strip().split("\t")]
    while len(partes) < 6:
        partes.append("")

    # Montar nova string de parâmetros
    params_str = ",".join([f"{k}={v}" for k, v in novos_params.items()])
    partes[3] = params_str

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({"status": "success", "message": "Parâmetros salvos com sucesso!"})

@app.route("/api/enviar/<int:idx>", methods=["POST"])
def api_enviar(idx):
    entradas = obter_entradas()
    ent = next((e for e in entradas if e["idx_linha"] == idx), None)
    
    if not ent or ent["template"] not in TEMPLATES:
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    mensagem = processar_mensagem(TEMPLATES[ent["template"]], ent["params_dict"])

    return jsonify({
        "status": "success",
        "mensagem": mensagem,
        "telefone": ent["telefone"],
        "nome": ent["nome"],
        "template_atual": ent["template"],
        "idx": idx
    })

@app.route("/api/backup")
def api_backup():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for arquivo in ["config.txt", "templates.txt", "snippets.txt"]:
            if os.path.exists(arquivo):
                zf.write(arquivo)
    memory_file.seek(0)
    return send_file(memory_file, download_name="backup_lembretes.zip", as_attachment=True)

@app.route("/api/templates")
def api_templates():
    return jsonify(list(TEMPLATES.keys()))

@app.route("/api/trocar_template", methods=["POST"])
def api_trocar_template():
    data = request.json
    idx = data.get("idx")
    novo_template = data.get("novo_template")

    if idx is None or not novo_template or novo_template not in TEMPLATES:
        return jsonify({"status": "error", "message": "Dados inválidos"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    partes = [p.strip() for p in linhas[idx].strip().split("\t")]
    while len(partes) < 6:
        partes.append("")
    
    params_antigos = parse_parametros(partes[3])

    template_texto = TEMPLATES[novo_template]
    info = extrair_variaveis_e_opcionais(template_texto)

    params_novos = {**params_antigos}
    for var in info['todas']:
        if var not in params_novos:
            params_novos[var] = ""

    params_str = ",".join(f"{k}={v}" for k, v in sorted(params_novos.items()))

    partes[2] = novo_template
    partes[3] = params_str

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({
        "status": "success",
        "message": f"Template alterado para {novo_template}",
        "parametros": params_novos,
        "opcionais": info['opcionais'],
        "obrigatorias": info['obrigatorias']
    })

@app.route("/api/configurar_parametros_template", methods=["POST"])
def api_configurar_parametros_template():
    data = request.json
    idx = data.get("idx")
    novo_template = data.get("novo_template")

    if idx is None or not novo_template or novo_template not in TEMPLATES:
        return jsonify({"status": "error", "message": "Dados inválidos"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    # Pegar parâmetros antigos
    partes = [p.strip() for p in linhas[idx].strip().split("\t")]
    params_antigos_str = partes[3] if len(partes) > 3 else ""
    params_antigos = parse_parametros(params_antigos_str)

    template_texto = TEMPLATES[novo_template]
    info = extrair_variaveis_e_opcionais(template_texto)

    # Manter parâmetros comuns + adicionar novos
    params_novos = {**params_antigos}

    # Adicionar variáveis novas que não existiam
    for var in info['todas']:
        if var not in params_novos:
            params_novos[var] = ""  # vazio para ser preenchido

    # Montar nova linha
    params_str = ",".join(f"{k}={v}" for k, v in params_novos.items() if v or k in info['todas'])

    partes[2] = novo_template
    partes[3] = params_str

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({
        "status": "success",
        "message": f"Template alterado para {novo_template}",
        "parametros": params_novos,
        "opcionais": info['opcionais']
    })

@app.route("/api/salvar_intervalo", methods=["POST"])
def api_salvar_intervalo():
    data = request.json
    idx = data.get("idx")
    novo_intervalo = data.get("intervalo")

    if idx is None or novo_intervalo is None:
        return jsonify({"status": "error", "message": "Dados inválidos"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    partes = [p.strip() for p in linhas[idx].strip().split("\t")]
    while len(partes) < 6:
        partes.append("")

    partes[4] = f"1/{novo_intervalo}"  # Mantemos formato x/y

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({"status": "success", "message": f"Intervalo alterado para {novo_intervalo} dias"})


@app.route("/api/salvar_proximo_envio", methods=["POST"])
def api_salvar_proximo_envio():
    data = request.json
    idx = data.get("idx")
    nova_data = data.get("proximo_envio")

    if idx is None or not nova_data:
        return jsonify({"status": "error", "message": "Dados inválidos"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    partes = [p.strip() for p in linhas[idx].strip().split("\t")]
    while len(partes) < 6:
        partes.append("")

    # Calcula novo ULTIMO_ENVIO = nova_data - intervalo
    try:
        proximo = date.fromisoformat(nova_data)
        intervalo = int(partes[4].split("/")[1]) if len(partes) > 4 and "/" in partes[4] else 7
        ultimo = proximo - timedelta(days=intervalo)
        partes[5] = ultimo.isoformat()
    except:
        partes[5] = date.today().isoformat()

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({"status": "success", "message": f"Próximo envio alterado para {nova_data}"})

@app.route("/api/nova_entrada", methods=["POST"])
def api_nova_entrada():
    data = request.json
    telefone = data.get("telefone")
    nome = data.get("nome")
    template = data.get("template")
    parametros = data.get("parametros", {})
    intervalo = data.get("intervalo", 7)
    data_primeira = data.get("data_primeira", date.today().isoformat())

    if not telefone or not nome or not template:
        return jsonify({"status": "error", "message": "Telefone, Nome e Template são obrigatórios"}), 400

    params_str = ",".join(f"{k}={v}" for k, v in parametros.items() if v)

    # Calcula ultimo_envio
    try:
        primeira = date.fromisoformat(data_primeira)
        ultimo_envio = (primeira - timedelta(days=intervalo)).isoformat()
    except:
        ultimo_envio = (date.today() - timedelta(days=1)).isoformat()

    nova_linha = f"{telefone}\t{nome}\t{template}\t{params_str}\t1/{intervalo}\t{ultimo_envio}\n"

    with open("config.txt", "a", encoding="utf-8") as f:
        f.write(nova_linha)

    return jsonify({
        "status": "success", 
        "message": "Nova entrada criada com sucesso!",
        "pode_enviar_agora": date.fromisoformat(data_primeira) <= date.today()
    })

@app.route("/api/variaveis_template/<string:template>")
def api_variaveis_template(template):
    if template not in TEMPLATES:
        return jsonify({"error": "Template não encontrado"}), 404
    
    info = extrair_variaveis_e_opcionais(TEMPLATES[template])
    return jsonify({
        "todas": info['todas'],
        "opcionais": info['opcionais'],
        "obrigatorias": info['obrigatorias']
    })

@app.route("/api/aplicar_apos_envio", methods=["POST"])
def api_aplicar_apos_envio():
    data = request.json
    idx = data.get("idx")
    template_atual = data.get("template_atual")

    if idx is None:
        return jsonify({"status": "error", "message": "Índice não informado"}), 400

    linhas = carregar_config()
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    partes = [p.strip() for p in linhas[idx].strip().split("\t")]
    while len(partes) < 6:
        partes.append("")

    # 1. Atualiza ULTIMO_ENVIO
    partes[5] = date.today().isoformat()

    novo_template = None

    # 2. Verifica e aplica One-shot
    from common import ONE_SHOT_TEMPLATES
    proximo_template = ONE_SHOT_TEMPLATES.get(template_atual)

    if proximo_template and proximo_template in TEMPLATES:
        novo_template = proximo_template
        partes[2] = novo_template

        # Reconfigura parâmetros para o novo template
        params_antigos = parse_parametros(partes[3])
        template_texto = TEMPLATES[novo_template]
        info = extrair_variaveis_e_opcionais(template_texto)

        params_novos = {**params_antigos}
        for var in info['todas']:
            if var not in params_novos:
                params_novos[var] = ""

        partes[3] = ",".join(f"{k}={v}" for k, v in sorted(params_novos.items()))

    linhas[idx] = "\t".join(partes) + "\n"
    salvar_config(linhas)

    return jsonify({
        "status": "success",
        "message": "Envio registrado com sucesso",
        "novo_template": novo_template,
        "template_alterado": novo_template is not None
    })

@app.route("/api/excluir/<int:idx>", methods=["DELETE"])
def api_excluir(idx):
    linhas = carregar_config()
    
    if idx >= len(linhas):
        return jsonify({"status": "error", "message": "Entrada não encontrada"}), 404

    # Remove a linha
    linha_removida = linhas.pop(idx)
    salvar_config(linhas)

    # Tenta extrair nome para mensagem amigável
    partes = [p.strip() for p in linha_removida.strip().split("\t")]
    nome = partes[1] if len(partes) > 1 else "entrada"

    return jsonify({
        "status": "success", 
        "message": f"Entrada de {nome} excluída com sucesso!"
    })

@app.route("/api/debug_template/<string:template_nome>")
def api_debug_template(template_nome):
    if template_nome not in TEMPLATES:
        return jsonify({"error": "Template não encontrado"}), 404

    template_texto = TEMPLATES[template_nome]
    
    # Expansão manual de snippets (para evitar dependência de ordem)
    texto_expandido = template_texto
    for _ in range(20):
        novo = processar_snippets(texto_expandido)  # deve existir no common.py
        if novo == texto_expandido:
            break
        texto_expandido = novo

    # Extração
    info = extrair_variaveis_e_opcionais(template_texto)

    return jsonify({
        "template": template_nome,
        "texto_original": template_texto[:500] + "..." if len(template_texto) > 500 else template_texto,
        "texto_expandido": texto_expandido,
        "todas": info.get('todas', []),
        "opcionais": info.get('opcionais', []),
        "obrigatorias": info.get('obrigatorias', []),
        "count_todas": len(info.get('todas', [])),
        "count_opcionais": len(info.get('opcionais', [])),
        "count_obrigatorias": len(info.get('obrigatorias', []))
    })

@app.route("/api/reload")
def api_reload():
    try:
        carregar_templates_globais()
        carregar_snippets_globais()
        carregar_one_shot_templates()

        # Também recarrega as entradas (config.txt)
        entradas = obter_entradas()  # se sua função estiver definida

        return jsonify({
            "status": "success",
            "message": "✅ Arquivos recarregados com sucesso!",
            "templates_count": len(TEMPLATES),
            "snippets_count": len(SNIPPETS),
            "one_shot_count": len(ONE_SHOT_TEMPLATES)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao recarregar: {str(e)}"
        }), 500

if __name__ == "__main__":
    print("Servidor rodando em http://0.0.0.0:5000")
    app.run(host='0.0.0.0', debug=True, port=5000)
