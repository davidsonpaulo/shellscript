import os
import re
from datetime import datetime, date, timedelta

# ===================== SNIPPETS =====================
SNIPPETS = {}

def carregar_snippets_globais():
    """Carrega os snippets uma única vez."""
    global SNIPPETS
    SNIPPETS.clear()
    if not os.path.exists("snippets.txt"):
        print("⚠️  Arquivo snippets.txt não encontrado. Snippets desativados.")
        return
    with open("snippets.txt", "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "=" in linha:
                nome, texto = linha.split("=", 1)
                SNIPPETS[nome.strip()] = texto.strip()
    print(f"✅ {len(SNIPPETS)} snippets carregados com sucesso.")


# ===================== TEMPLATES GLOBAIS =====================
TEMPLATES = {}

def carregar_templates_globais():
    """Carrega os templates uma única vez."""
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
    print(f"✅ {len(TEMPLATES)} templates carregados com sucesso.")


# ===================== MACROS (agora genérico e extensível) =====================
def registrar_macros():
    """Registre aqui todas as macros do sistema."""
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

    # ← Adicione novas macros aqui no futuro (ex: moeda, plural, data_extenso, etc.)
    # macros["moeda"] = macro_moeda
    # macros["plural"] = macro_plural

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


def processar_snippets(texto):
    """Substitui {{snippet:NOME}} pelo conteúdo do snippet."""
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
    """Fase 1: Cria dicionário de todas as tags condicionais → 'true' ou 'false'."""
    padrao = r'(\{\{if:\s*(!?)\s*([^}]+?)\s*\}\})'
    matches = re.findall(padrao, texto)

    cond_dict = {}
    for full_tag, negacao, condicao in matches:
        valor_real = str(params.get(condicao.strip(), "")).strip().lower()
        condicao_verdadeira = valor_real not in ("", "false", "0", "não", "nao", "falso")
        resultado = (not condicao_verdadeira) if negacao == "!" else condicao_verdadeira
        cond_dict[full_tag] = 'true' if resultado else 'false'

    return cond_dict


def processar_mensagem(template, params):
    """Processa template seguindo o fluxo validado por você."""
    texto = template

    # 1. Snippets
    texto = processar_snippets(texto)

    # 2. Variáveis
    for chave, valor in params.items():
        texto = texto.replace(f"{{{{{chave}}}}}", str(valor))

    # 3. Macro (usando sistema genérico)
    texto = texto.replace("{{macro:bom_dia_tarde_noite}}", MACROS["bom_dia_tarde_noite"]())

    # 4. Avaliar condicionais → dicionário
    cond_dict = avaliar_condicionais(texto, params)

    # Substituir cada {{if:...}} por {{true}} ou {{false}}
    for tag, valor in cond_dict.items():
        texto = texto.replace(tag, "{{" + valor + "}}")

    # 5. Tratar os {{else}} sequencialmente (invertendo o valor anterior)
    ultimo_valor = None
    while "{{else}}" in texto:
        pos = texto.find("{{else}}")
        if pos == -1:
            break

        antes = texto[:pos]
        ultimo_true = antes.rfind("{{true}}")
        ultimo_false = antes.rfind("{{false}}")
        ultimo_pos = max(ultimo_true, ultimo_false)

        if ultimo_pos != -1:
            ultimo_valor = "true" if ultimo_true > ultimo_false else "false"
        else:
            ultimo_valor = "false"

        inverso = "{{false}}" if ultimo_valor == "true" else "{{true}}"
        texto = texto[:pos] + inverso + texto[pos + 8:]

    # 6. Remover blocos falsos
    texto = re.sub(r'{{false}}.*?({{true}}|{{endif}})', '', texto, flags=re.DOTALL)

    # 7. Limpeza final de todos os marcadores
    texto = texto.replace("{{true}}", "").replace("{{false}}", "").replace("{{endif}}", "").replace("{{else}}", "")

    # Limpeza de espaços
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto


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
        vars_raiz = sorted(todas - set().union(*[set(v) for v in condicionais.values()]))

        print("  Variáveis principais:")
        for var in sorted(vars_raiz):
            status = "(opcional)" if var in opcionais_raiz else "(obrigatória)"
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
