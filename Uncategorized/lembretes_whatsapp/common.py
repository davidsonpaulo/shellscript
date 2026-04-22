import os
import re
from datetime import datetime, date, timedelta

# ===================== ONE-SHOT TEMPLATES =====================
ONE_SHOT_TEMPLATES = {}

def carregar_one_shot_templates():
    global ONE_SHOT_TEMPLATES
    ONE_SHOT_TEMPLATES.clear()

    if not os.path.exists("templates.txt"):
        print("⚠️  Arquivo templates.txt não encontrado. One-shot desativado.")
        return

    with open("templates.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if " -> " in linha:
                partes = [p.strip() for p in linha.split(" -> ", 1)]
                if len(partes) == 2:
                    original = partes[0]
                    proximo = partes[1] if partes[1] else None
                    ONE_SHOT_TEMPLATES[original] = proximo

    if ONE_SHOT_TEMPLATES:
        print(f"✅ {len(ONE_SHOT_TEMPLATES)} templates one-shot carregados.")
    else:
        print("ℹ️  Nenhum template one-shot configurado.")

# ===================== SNIPPETS =====================
SNIPPETS = {}

def carregar_snippets_globais():
    global SNIPPETS
    SNIPPETS.clear()
    if not os.path.exists("snippets.txt"):
        print("⚠️  Arquivo snippets.txt não encontrado.")
        return
    with open("snippets.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "=" in linha:
                nome, texto = linha.split("=", 1)
                SNIPPETS[nome.strip()] = texto.strip()
    print(f"✅ {len(SNIPPETS)} snippets carregados.")

# ===================== TEMPLATES GLOBAIS =====================
TEMPLATES = {}

def carregar_templates_globais():
    global TEMPLATES
    TEMPLATES.clear()
    if not os.path.exists("templates.txt"):
        print("⚠️  Arquivo templates.txt não encontrado.")
        return
    with open("templates.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "=" in linha:
                nome, texto = linha.split("=", 1)
                TEMPLATES[nome.strip()] = texto.strip()
    print(f"✅ {len(TEMPLATES)} templates carregados.")


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


# ===================== SNIPPETS =====================
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

# ===================== PROCESSAMENTO DE CONDICIONAIS =====================

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
    """Processamento linear com stack - ignora bloco se QUALQUER nível for False."""
    texto = template

    # 1. Snippets
    texto = processar_snippets(texto)

    # 2. Variáveis
    for chave, valor in params.items():
        texto = texto.replace(f"{{{{{chave}}}}}", str(valor))

    # 3. Macro
    texto = texto.replace("{{macro:bom_dia_tarde_noite}}", MACROS["bom_dia_tarde_noite"]())

    # 4. Avaliar condicionais
    cond_dict = avaliar_condicionais(texto, params)

    # 5. Processamento linear
    resultado = []
    i = 0
    n = len(texto)
    stack = []   # lista de booleanos

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

        # REGRA FORTE: se QUALQUER nível for False, pular tudo
        if stack and any(not nivel for nivel in stack):
            i += 1
            continue

        resultado.append(texto[i])
        i += 1

    texto_final = ''.join(resultado)
    texto_final = re.sub(r'\s+', ' ', texto_final).strip()

    return texto_final

# ===================== FUNÇÃO DE EDIÇÃO DE PARÂMETROS =====================
def editar_parametros(ent):
    """Edita parâmetros de forma contínua."""
    if ent["template"] not in TEMPLATES:
        print("Template não encontrado no templates.txt.")
        return

    template_texto = TEMPLATES[ent["template"]]
    info_vars = extrair_variaveis_e_opcionais(template_texto)

    todas = info_vars['todas']
    opcionais_raiz = info_vars['opcionais_raiz']
    condicionais = info_vars['condicionais']

    params_dict = parse_parametros(ent.get("parametros_str", ""))

    while True:
        print(f"\n=== Editando PARÂMETROS do template '{ent['template']}' ===")

        print("\nParâmetros atuais:")
        if params_dict:
            for k, v in sorted(params_dict.items()):
                print(f"   {k:20} = {v}")
        else:
            print("   (nenhum parâmetro definido)")

        print("\nVariáveis disponíveis:")
        # CORREÇÃO: incluir também as variáveis condicionais
        todas_vars = sorted(info_vars['todas'] | set(info_vars['opcionais_raiz']))

        print("  Variáveis principais:")
        for var in todas_vars:
            status = "(opcional)" if var in info_vars['opcionais_raiz'] else "(obrigatória)"
            atual = params_dict.get(var, "(não definido)")
            print(f"    {var:20} → {atual:30} {status}")

        if condicionais:
            print("\n  Variáveis condicionais:")
            for var_cond, deps in sorted(condicionais.items()):
                status = "✅ Definida" if params_dict.get(var_cond) else "❌ Não definida"
                print(f"    {{if:{var_cond}}} ou {{if:!{var_cond}}} → {', '.join(deps)}  [{status}]")

        param_nome = input("\nDigite o nome da variável para editar (Enter = finalizar): ").strip()
        if not param_nome:
            break

        if param_nome not in todas:
            if input(f"Variável '{param_nome}' não existe. Adicionar mesmo assim? (s/n): ").lower() != "s":
                continue

        is_condicional = any(param_nome in deps for deps in condicionais.values())
        var_cond_pai = None
        for vc, deps in condicionais.items():
            if param_nome in deps:
                var_cond_pai = vc
                break

        current = params_dict.get(param_nome, "")
        if var_cond_pai and not params_dict.get(var_cond_pai):
            print(f"Atenção: '{param_nome}' depende de '{var_cond_pai}' que não está definido.")
            if input("Deseja definir mesmo assim? (s/n): ").lower() != "s":
                continue

        novo_val = input(f"Novo valor para '{param_nome}' (atual: '{current}'): ").strip()

        if novo_val == "":
            if param_nome in opcionais_raiz or is_condicional:
                params_dict.pop(param_nome, None)
                print(f"Variável '{param_nome}' removida.")
            else:
                print("Não é possível remover variável obrigatória.")
        else:
            params_dict[param_nome] = novo_val
            print(f"✅ '{param_nome}' atualizado.")

    ent["parametros_str"] = ",".join(f"{k}={v}" for k, v in sorted(params_dict.items())) if params_dict else ""
    print("✅ Parâmetros salvos com sucesso.")


def extrair_variaveis_e_opcionais(template_texto):
    """Versão mantida exatamente como estava (sem alterações)."""
    texto_expandido = processar_snippets(template_texto)

    padrao_var = r'\{\{([A-Z_][A-Z0-9_]*)\}\}'
    padrao_if = r'\{\{if:(!?)([^}]+)\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{endif\}\}'

    todas = set(re.findall(padrao_var, texto_expandido))

    opcionais_raiz = set()
    condicionais = {}

    for match in re.finditer(padrao_if, texto_expandido, re.DOTALL):
        negacao = match.group(1)
        condicao = match.group(2).strip()
        conteudo_true = match.group(3) or ""
        conteudo_false = match.group(4) or "" if match.group(4) else ""

        chave = condicao
        opcionais_raiz.add(chave)

        vars_no_true = re.findall(padrao_var, conteudo_true)
        vars_no_false = re.findall(padrao_var, conteudo_false)

        if vars_no_true or vars_no_false:
            if chave not in condicionais:
                condicionais[chave] = set()
            condicionais[chave].update(vars_no_true)
            condicionais[chave].update(vars_no_false)

    return {
        'todas': todas,
        'opcionais_raiz': opcionais_raiz,
        'condicionais': {k: sorted(list(v)) for k, v in condicionais.items()}
    }


def pode_enviar(frequencia, ultimo_envio_str):
    """Verifica se a mensagem pode ser enviada."""
    if not ultimo_envio_str:
        return True
    try:
        ultimo = datetime.strptime(ultimo_envio_str, "%Y-%m-%d").date()
    except:
        return True
    
    hoje = date.today()
    if frequencia == "1/1":
        return ultimo < hoje
    elif "/" in frequencia:
        try:
            vezes, dias = map(int, frequencia.split("/"))
            delta = (hoje - ultimo).days
            return delta >= dias
        except:
            return True
    return True

# ===================== CONFIGURAÇÃO DE PARÂMETROS PARA NOVO TEMPLATE (VERSÃO CORRIGIDA) =====================
def configurar_parametros_para_template(template_nome, parametros_antigos_str=""):
    """Versão corrigida: inclui também variáveis que aparecem apenas em condições {{if:}}"""
    if template_nome not in TEMPLATES:
        print(f"❌ Template '{template_nome}' não encontrado.")
        return ""

    template_texto = TEMPLATES[template_nome]
    info_vars = extrair_variaveis_e_opcionais(template_texto)

    params_dict = parse_parametros(parametros_antigos_str) if parametros_antigos_str else {}

    print(f"\n=== Configurando PARÂMETROS para o NOVO template '{template_nome}' ===")
    print("Os valores antigos serão mostrados. Pressione Enter para manter ou digite novo valor.\n")

    # CORREÇÃO: unir variáveis simples + variáveis condicionais
    todas_vars = sorted(info_vars['todas'] | set(info_vars['opcionais_raiz']))

    for var in todas_vars:
        is_opcional = (var in info_vars['opcionais_raiz']) or \
                      any(var in deps for deps in info_vars['condicionais'].values())

        valor_antigo = params_dict.get(var, "")
        status = "(opcional)" if is_opcional else "(OBRIGATÓRIO)"

        if valor_antigo:
            print(f"  {var} = {valor_antigo}  ← valor antigo")

        novo_val = input(f"  {var} {status}: ").strip()

        if novo_val == "":
            if valor_antigo:
                print(f"     → mantido valor antigo")
                pass
            elif not is_opcional:
                while not novo_val:
                    novo_val = input(f"  {var} (OBRIGATÓRIO - digite um valor): ").strip()
                params_dict[var] = novo_val
            else:
                params_dict.pop(var, None)
                print(f"     → removido (não informado)")
        else:
            params_dict[var] = novo_val
            print(f"     → atualizado")

    # Variáveis condicionais dependentes (mantido)
    for var_cond, deps in info_vars['condicionais'].items():
        if var_cond in params_dict and params_dict[var_cond]:
            print(f"\n→ '{var_cond}' definido → verificando dependentes:")
            for var_dep in sorted(set(deps)):
                if var_dep in params_dict and params_dict.get(var_dep):
                    continue
                val = input(f"  {var_dep} (dependente): ").strip()
                while not val:
                    val = input(f"  {var_dep} (obrigatório): ").strip()
                params_dict[var_dep] = val

    parametros_str = ",".join(f"{k}={v}" for k, v in sorted(params_dict.items())) if params_dict else ""
    print("✅ Parâmetros configurados com sucesso.\n")
    return parametros_str
