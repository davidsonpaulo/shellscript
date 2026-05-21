# common.py - Versão completa e limpa para uso com Flask
import os
import re
from datetime import datetime, date, timedelta

# ===================== TEMPLATES E SNIPPETS =====================
TEMPLATES = {}
SNIPPETS = {}
ONE_SHOT_TEMPLATES = {}

def carregar_one_shot_templates():
    global ONE_SHOT_TEMPLATES
    ONE_SHOT_TEMPLATES.clear()
    if not os.path.exists("templates.txt"):
        return
    with open("templates.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if " -> " in linha:
                partes = [p.strip() for p in linha.split(" -> ", 1)]
                if len(partes) == 2:
                    ONE_SHOT_TEMPLATES[partes[0]] = partes[1]

def carregar_snippets_globais():
    global SNIPPETS
    SNIPPETS.clear()
    if not os.path.exists("snippets.txt"):
        return
    with open("snippets.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "=" in linha:
                nome, texto = linha.split("=", 1)
                SNIPPETS[nome.strip()] = texto.strip()

def carregar_templates_globais():
    global TEMPLATES
    TEMPLATES.clear()
    if not os.path.exists("templates.txt"):
        return
    with open("templates.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or " -> " in linha:
                continue
            if "=" in linha:
                nome, texto = linha.split("=", 1)
                TEMPLATES[nome.strip()] = texto.strip()

# ===================== MACROS =====================
def registrar_macros():
    macros = {}
    def bom_dia_tarde_noite():
        hora = datetime.now().hour
        padrao = ", tudo bem? Essa é uma *MENSAGEM AUTOMÁTICA* da Celsom Ferramentas."
        if 7 <= hora < 12:
            return f"Bom dia{padrao}"
        elif 12 <= hora < 18:
            return f"Boa tarde{padrao}"
        else:
            return f"Boa noite{padrao}"
    macros["bom_dia_tarde_noite"] = bom_dia_tarde_noite
    return macros

MACROS = registrar_macros()

# ===================== FUNÇÕES AUXILIARES =====================
def parse_parametros(param_str):
    """Lê parâmetros, restaurando vírgulas escapadas."""
    params = {}
    if not param_str:
        return params
    items = re.split(r',(?=[A-Z_][A-Z0-9_]*=)', param_str)
    for item in items:
        if "=" in item:
            chave, valor = item.split("=", 1)
            valor = valor.strip().replace("%2C", ",")
            params[chave.strip()] = valor
    return params

# ===================== PROCESSAMENTO =====================
def processar_snippets(texto):
    def substituir(match):
        nome = match.group(1).strip()
        return SNIPPETS.get(nome, f"[SNIPPET NÃO ENCONTRADO: {nome}]")
    padrao = r'\{\{snippet:([^}]+)\}\}'
    for _ in range(10):
        novo_texto = re.sub(padrao, substituir, texto)
        if novo_texto == texto:
            break
        texto = novo_texto
    return texto

def avaliar_condicionais(texto, params):
    padrao = r'(\{\{if:\s*(!?)\s*([^}]+?)\s*\}\})'
    matches = re.findall(padrao, texto)
    cond_dict = {}
    for full_tag, negacao, condicao in matches:
        valor_real = str(params.get(condicao.strip(), "")).strip().lower()
        verdade = valor_real not in ("", "false", "0", "não", "nao", "falso")
        resultado = (not verdade) if negacao == "!" else verdade
        cond_dict[full_tag] = resultado
    return cond_dict

def processar_mensagem(template, params):
    """Processamento completo de template"""
    texto = template

    # Snippets
    texto = processar_snippets(texto)

    # Variáveis
    for chave, valor in params.items():
        texto = texto.replace(f"{{{{{chave}}}}}", str(valor))

    # Macro
    texto = texto.replace("{{macro:bom_dia_tarde_noite}}", MACROS["bom_dia_tarde_noite"]())

    # Condicionais (simplificado por enquanto - versão completa depois)
    cond_dict = avaliar_condicionais(texto, params)

    # Processamento básico dos ifs (melhorado depois)
    resultado = []
    i = 0
    n = len(texto)
    stack = []

    while i < n:
        if texto[i:i+5] == '{{if:':
            fim = texto.find('}}', i)
            if fim != -1:
                full_tag = texto[i:fim + 2]
                is_true = cond_dict.get(full_tag, False)
                stack.append(is_true)
                i = fim + 2
                continue

        elif texto[i:i+8] == '{{else}}':
            if stack:
                stack[-1] = not stack[-1]
            i += 8
            continue

        elif texto[i:i+9] == '{{endif}}':
            if stack:
                stack.pop()
            i += 9
            continue

        if stack and any(not nivel for nivel in stack):
            i += 1
            continue

        resultado.append(texto[i])
        i += 1

    texto_final = ''.join(resultado)
    texto_final = re.sub(r'\s+', ' ', texto_final).strip()
    return texto_final

# ===================== FUNÇÃO AUXILIAR PARA O FLASK =====================
def pode_enviar(frequencia, ultimo_envio_str):
    if not ultimo_envio_str:
        return True
    try:
        ultimo = datetime.strptime(ultimo_envio_str, "%Y-%m-%d").date()
    except:
        return True
    hoje = date.today()
    if "/" in frequencia:
        try:
            _, dias = map(int, frequencia.split("/"))
            delta = (hoje - ultimo).days
            return delta >= dias
        except:
            return True
    return True

def extrair_variaveis_e_opcionais(template_texto):
    """Versão conforme instrução: todas = opcionais + obrigatorias."""
    # Expansão completa de snippets
    texto_expandido = template_texto
    for _ in range(30):
        novo = processar_snippets(texto_expandido)
        if novo == texto_expandido:
            break
        texto_expandido = novo

    padrao_var = r'\{\{([A-Z_][A-Z0-9_]*)\}\}'

    # Captura TODAS as variáveis
    todas_raw = set(re.findall(padrao_var, texto_expandido))

    opcionais = set()

    # Identifica variáveis opcionais
    for match in re.finditer(r'\{\{if:(!?)([^}]+)\}\}', texto_expandido):
        condicao = match.group(2).strip()
        opcionais.add(condicao)

    for match in re.finditer(r'\{\{if:(!?)([^}]+)\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{endif\}\}', texto_expandido, re.DOTALL):
        conteudo_true = match.group(3) or ""
        conteudo_false = match.group(4) or ""
        opcionais.update(re.findall(padrao_var, conteudo_true))
        opcionais.update(re.findall(padrao_var, conteudo_false))

    # === Conforme sua instrução ===
    obrigatorias = todas_raw - opcionais
    todas = sorted(opcionais | obrigatorias)   # todas = opcionais + obrigatorias

    return {
        'todas': todas,
        'opcionais': sorted(opcionais),
        'obrigatorias': sorted(obrigatorias)
    }
