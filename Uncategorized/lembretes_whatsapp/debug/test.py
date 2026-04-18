import re
from datetime import datetime

# ===================== CARREGAMENTO =====================

def carregar_snippets():
    snippets = {}
    with open("snippets.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            nome, texto = [x.strip() for x in linha.split("=", 1)]
            snippets[nome] = texto
    return snippets

def carregar_template():
    with open("templates.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("RETIRADA_MULTIPLA ="):
                return linha.split("=", 1)[1].strip()
    raise ValueError("Template não encontrado")

def parse_parametros(param_str):
    params = {}
    if not param_str:
        return params
    items = re.split(r',(?=[A-Z_][A-Z0-9_]*=)', param_str)
    for item in items:
        if "=" in item:
            chave, valor = [x.strip() for x in item.split("=", 1)]
            params[chave] = valor
    return params

# ===================== PROCESSAMENTO =====================

def processar_snippets(texto, snippets):
    def substituir(match):
        nome = match.group(1).strip()
        return snippets.get(nome, f"[SNIPPET NÃO ENCONTRADO: {nome}]")
    padrao = r'\{\{snippet:([^}]+)\}\}'
    for _ in range(10):
        novo = re.sub(padrao, substituir, texto)
        if novo == texto:
            break
        texto = novo
    return texto

def processar_condicionais(texto, params):
    def substituir(match):
        negacao = match.group(1) or ""
        condicao = match.group(2).strip()
        true_part = match.group(3) or ""
        false_part = match.group(4) or "" if match.group(4) is not None else ""

        valor = str(params.get(condicao, "")).strip().lower()
        condicao_verdadeira = valor not in ("", "false", "0", "não", "nao", "falso")

        resultado = (not condicao_verdadeira) if negacao == "!" else condicao_verdadeira
        return true_part if resultado else false_part

    padrao = r'\{\{if:\s*(!?)\s*([A-Z0-9_]+)\s*\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{endif\}\}'
    texto = re.sub(padrao, substituir, texto, flags=re.DOTALL)
    return texto

def processar_mensagem(template, params, snippets):
    texto = template

    # 1. Expandir snippets
    texto = processar_snippets(texto, snippets)

    # 2. Substituir variáveis
    for chave, valor in params.items():
        texto = texto.replace(f"{{{{{chave}}}}}", str(valor))

    # 3. Macro
    hora = datetime.now().hour
    if 7 <= hora < 12:
        saudacao = "Bom dia"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    macro = f"{saudacao}, tudo bem? Essa é uma *MENSAGEM AUTOMÁTICA* da Celsom Ferramentas."
    texto = texto.replace("{{macro:bom_dia_tarde_noite}}", macro)

    # 4. Processar condicionais
    texto = processar_condicionais(texto, params)

    # 5. Remoção final dos marcadores
    texto = texto.replace("{{endif}}", "").replace("{{else}}", "")

    # 6. Limpeza específica para evitar duplicação do preço
    # Remove qualquer resíduo do ORCAMENTO quando PRECO_BRUTO não existe
    texto = re.sub(r'{{if:PRECO_BRUTO}}R\$ {{PRECO_BRUTO}}, com descontos ficou ', '', texto)
    
    # Garante que "Valor do conserto:" apareça apenas uma vez com o preço correto
    if "Valor do conserto:" in texto:
        preco = params.get("PRECO", "0")
        texto = re.sub(r'Valor do conserto:.*?(\*R\$ [^ *]+\*)?.*?(?=\.| Qual)', 
                      f'Valor do conserto: *R$ {preco}*', texto)

    # Limpeza final de espaços e pontuação
    texto = re.sub(r'\s+', ' ', texto).strip()
    texto = re.sub(r'\*\.\s*', '*. ', texto)   # corrige "*." 

    return texto

# ===================== EXECUÇÃO =====================

if __name__ == "__main__":
    with open("config.txt", "r", encoding="utf-8") as f:
        linha = f.readline().strip()

    partes = [p.strip() for p in linha.split("\t")]
    param_str = partes[3]

    params = parse_parametros(param_str)
    template = carregar_template()
    snippets = carregar_snippets()

    mensagem = processar_mensagem(template, params, snippets)
    print(mensagem)
