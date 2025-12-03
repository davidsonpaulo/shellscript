#!/usr/bin/env python3
from math import floor, ceil, sqrt
import sys
import json

def carregar_constantes(caminho_arquivo):
    constantes = {}
    with open(caminho_arquivo, 'r') as f:
        for linha in f:
            # Ignora linhas vazias e comentários
            if linha.strip() and not linha.startswith('#'):
                chave, valor = linha.split('=')
                constantes[chave.strip()] = float(valor.strip())
    return constantes

def carregar_taxas(caminho_arquivo):
    with open(caminho_arquivo, 'r') as f:
        taxas = json.load(f)
    return taxas

def adicionar_taxa(preco, chave_taxa):
    return preco / (1 - TAXAS[chave_taxa] / 100)

def remover_taxa(preco, chave_taxa):
    return preco * (1 - TAXAS[chave_taxa] / 100)

def arredondar_preco(preco):
    piso = floor(preco)
    teto = ceil(preco)
    return teto if preco - piso >= teto - preco else piso

def calcular_parcela_com_entrada(preco, numero_parcelas):
    parcela = preco / (1 + (numero_parcelas - 1) * (1 - TAXAS[f"{numero_parcelas - 1}x"] / 100))
    total = parcela * numero_parcelas
    return parcela, total

def calcular_preco_padrao(custo, quantidade=1):
    custo_final = custo * quantidade
    return A * custo_final + B * sqrt(custo_final) + C

def calcular_preco_peca(custo, reposicao):
    preco_minimo = calcular_preco_padrao(custo)
    preco_maximo = calcular_preco_padrao(reposicao)
    preco_medio = (preco_minimo + preco_maximo) / 2
    if preco_medio < reposicao:
        preco = 2 * reposicao - preco_medio
    else:
        preco = preco_medio
    return adicionar_taxa(preco, '1x')

def calcular_preco_maquina(custo_fabrica, custo_nota, reposicao):
    venda_normal = ceil(adicionar_taxa((2 * custo_nota + reposicao) / 3, '10x'))
    lucro_normal = venda_normal - custo_nota

    if custo_nota > custo_fabrica:
        venda_desconto = custo_fabrica + lucro_normal
        diferenca_precos = venda_normal - venda_desconto
        preco_venda = ceil(venda_desconto + diferenca_precos / 2)
        preco_venda_vista = ceil(remover_taxa(preco_venda, '1x'))

        return(venda_normal, True, preco_venda, preco_venda_vista)

    venda_normal_vista = ceil(remover_taxa(venda_normal, '1x'))

    return(venda_normal, False, 0, venda_normal_vista)

def calcular_preco_acessorio(custo_fabrica, custo_nota, reposicao):
    preco_maquina, *_ = calcular_preco_maquina(custo_fabrica, custo_nota, reposicao)
    preco_peca = calcular_preco_peca(custo_nota, reposicao)
    return sqrt(preco_maquina * preco_peca)

def preco_maquina(custo_fabrica, custo_nota, reposicao):
    preco_normal, desconto, preco_a_prazo, preco_a_vista  = calcular_preco_maquina(custo_fabrica, custo_nota, reposicao)

    if desconto:
        print(f"Preço normal: R$ {preco_normal}")
        print(f"PROMOÇÃO: R$ {preco_a_prazo} em até 10x no cartão, R$ {preco_a_vista} à vista")
    else:
        print(f"R$ {preco_normal} em até 10x no cartão")
        print(f"R$ {preco_a_vista} à vista")

def preco_acessorio(custo_fabrica, custo_nota, reposicao):
    preco = calcular_preco_acessorio(custo_fabrica, custo_nota, reposicao)
    
    print(f"Preço: R$ {preco:.2f}")

def calcular_preco_dewalt(minimo_anunciado):
    preco_vista = remover_taxa(minimo_anunciado, "1x")
    preco_venda = adicionar_taxa(preco_vista, "6x")
    bonus = minimo_anunciado - preco_vista
    return ceil(preco_venda), floor(bonus)

def imprimir_custos(custo_fabrica, custo_nota, reposicao):
    print(f"- Custo de Fábrica:\tR$ {custo_fabrica:.3f}\n- Custo nota:\t\tR$ {custo_nota:.3f}\n- Custo reposição:\tR$ {reposicao:.3f}\n")

def imprimir_ajuda(erro=True):
    if erro:
        print("ERRO: comando inválido. Opções:")
    print("peca [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>%")
    print("maquina [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>% | <custo com desconto> <custo sem desconto>")
    print("acessorio [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>%")
    print("dewalt <mínimo anunciado>")
    print("vonder <preço normal>, <preço sem impostos>, <preco com impostos>")
    print("parcelamento <preço> <parcelas>")
    print("os <preço bruto>")
    print("ajuda / help")
    print("sair / exit")

def obter_tipo(tipo, tipos_validos):
    correspondentes = [t for t in tipos_validos if t.startswith(tipo)]
    if len(correspondentes) == 1:
        return correspondentes[0]
    else:
        return tipo

def adicionar_unidade_minima(numero):
    # Converte para string para inspecionar casas decimais
    num_str = str(numero)
    # Verifica se o número é inteiro ou float
    if '.' in num_str:
        # Encontra a posição do ponto decimal
        pos_decimal = num_str.index('.')
        # Verifica zeros à direita após o decimal
        casas_decimais = 0 if num_str.endswith('.0') else len(num_str) - pos_decimal - 1

        # Se termina em .0, trata como inteiro
        if casas_decimais == 0:
            return numero + 1

        # Calcula a menor unidade baseada nas casas decimais
        unidade = 10 ** -casas_decimais
        return numero + unidade
    else:
        # Se for inteiro, adiciona 1
        return numero + 1

def processar_comando(argumentos, tipo_anterior=None):
    if len(argumentos) == 0:
        return tipo_anterior

    arg0 = obter_tipo(argumentos[0], tipos_validos)

    if tipo_anterior and arg0 not in tipos_validos:
        argumentos = [tipo_anterior] + argumentos
    elif arg0 in tipos_validos:
        tipo = arg0
    else:
        imprimir_ajuda()
        return tipo_anterior

    if tipo in ('sair', 'exit'):
        print("Encerrando o programa.")
        sys.exit(0)

    if tipo in ('help', 'ajuda'):
        imprimir_ajuda(erro=False)
        return tipo

    if tipo == 'dewalt':
        if len(argumentos) != 2:
            imprimir_ajuda()
            return tipo

        try:
            minimo_anunciado = float(argumentos[1])
            venda, bonus = calcular_preco_dewalt(minimo_anunciado)
            print(f"Preço de venda, R$ {venda:.2f}")
            print(f"À VISTA: R$ {minimo_anunciado:.2f}")
            print(f"PROMOÇÃO: R$ {bonus:.2f} EM ACESSÓRIOS")
        except ValueError:
            print("<mínimo anunciado> deve ser um número")

        return tipo

    if tipo == 'vonder':
        if len(argumentos) < 3:
            imprimir_ajuda()
            return tipo

        try:
            preco_normal = float(argumentos[1])
            preco_sem_impostos = float(argumentos[2])
            preco_com_impostos = preco_sem_impostos

            if len(argumentos) == 4:
                preco_com_impostos = float(argumentos[3])

            preco_normal_com_impostos = preco_normal * preco_com_impostos / preco_sem_impostos
            reposicao = preco_normal_com_impostos * (1 + CARGA_OPERACIONAL / 100)
            imprimir_custos(preco_sem_impostos, preco_com_impostos, reposicao)
            preco_maquina(preco_com_impostos, preco_normal_com_impostos, reposicao)
        except ValueError:
            print("Todos os valores precisam ser números")

        return tipo

    if tipo in ('peca', 'maquina', 'acessorio'):
        if len(argumentos) not in (2, 3):
            imprimir_ajuda()
            return tipo

        try:
            custo_fabrica = float(argumentos[1])
            custo_nota = custo_fabrica

            if len(argumentos) == 3:
                if argumentos[2][-1] == "%":
                    ipi = float(argumentos[2][:-1])
                    custo_nota *= (1 + ipi / 100)
                else:
                    custo_nota = float(argumentos[2])

            reposicao = custo_nota * (1 + CARGA_OPERACIONAL / 100)
        except ValueError:
            print("Custo e reposição devem ser números.")
            return tipo

        imprimir_custos(custo_fabrica, custo_nota, reposicao)

        match tipo:
            case 'peca':
                venda = arredondar_preco(calcular_preco_peca(custo_nota, reposicao))
                print(f"Preço de venda:\t\tR$ {venda:.2f}")
            case 'maquina':
                preco_maquina(custo_fabrica, custo_nota, reposicao)
            case 'acessorio':
                preco_acessorio(custo_fabrica, custo_nota, reposicao)

        return tipo

    if tipo == 'os':
        if len(argumentos) != 2:
            imprimir_ajuda()
            return tipo

        try:
            preco_bruto = int(argumentos[1])
        except ValueError:
            print("Preço bruto deve ser um número.")
            return tipo

        if preco_bruto <= 0:
            print("Preço bruto deve ser maior que zero.")
            return tipo

        preco_a_vista = floor(adicionar_taxa(remover_taxa(preco_bruto, '3x'), '1x'))
        desconto = preco_bruto - preco_a_vista

        print(f'R$ {preco_bruto} em até 3x no cartão')
        print(f'R$ {preco_a_vista} à vista')
        print(f'Desconto: R$ {desconto}')

        return tipo

    if tipo == 'parcelamento':
        if len(argumentos) != 3:
            imprimir_ajuda()
            return tipo

        try:
            preco = float(argumentos[1])
            chave_parcela = argumentos[2]
        except ValueError:
            print("Preço deve ser um número.")
            return tipo

        if preco <= 0:
            print("O preço deve ser maior que zero.")
            return tipo

        if chave_parcela not in TAXAS:
            print(f"Parcela inválida: '{chave_parcela}'. Opções: {', '.join(TAXAS.keys())}")
            return tipo

        # Calcula preço à vista
        preco_a_vista = remover_taxa(preco, chave_parcela)
        for chave_taxa, valor_taxa in TAXAS.items():
            preco_final = adicionar_taxa(preco_a_vista, chave_taxa)

            if chave_taxa[0].isdigit():
                numero_parcelas = int(''.join(filter(str.isdigit, chave_taxa)))

                if numero_parcelas == 1:
                    print(f"{chave_taxa}: R$ {preco_final:.2f}")
                else:
                    sem_entrada = f"{chave_taxa} {preco_final / numero_parcelas:.2f} (R$ {preco_final:.2f})"
                    valor_parcela, valor_total = calcular_parcela_com_entrada(preco_a_vista, numero_parcelas)
                    com_entrada = f" | 1+{numero_parcelas - 1}x R$ {valor_parcela:.2f} (R$ {valor_total:.2f})"
                    print(f"{sem_entrada}{com_entrada}")
            else:
                print(f"{chave_taxa}: R$ {preco_final:.2f}")

        return tipo

if __name__ == "__main__":
    # Carrega as constantes
    constantes = carregar_constantes('vars.txt')
    A = constantes.get("A")
    B = constantes.get("B")
    C = constantes.get("C")
    CARGA_OPERACIONAL = constantes.get("CARGA_OPERACIONAL")
    TAXAS = carregar_taxas("taxas.json")

    tipos_validos = ('peca', 'maquina', 'acessorio', 'dewalt', 'vonder', 'parcelamento', 'os', 'sair', 'exit', 'ajuda', 'help')
    tipo = None

    # Verifica se argumentos foram passados via linha de comando
    if len(sys.argv) > 1:
        processar_comando(sys.argv[1:])
        sys.exit(0)

    # Modo interativo se não houver argumentos
    print("Bem-vindo ao calculador. Digite um comando (ou 'sair' para sair):")

    while True:
        try:
            entrada_usuario = input(f"{tipo if tipo else ''}> ").strip().lower()
        except EOFError:
            break

        argumentos = entrada_usuario.split()
        print()
        tipo = processar_comando(argumentos, tipo)
        print()
