#!/usr/bin/env python3

from decimal import Decimal, getcontext, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
import sys
import json

# Configuração global – suficiente para finanças
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP
centavo = Decimal('0.01')
meio = Decimal('0.5')
zero = Decimal(0)
um = Decimal(1)

def carregar_constantes(caminho_arquivo):
    constantes = {}
    with open(caminho_arquivo, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith('#'):
                chave, valor = linha.split('=')
                constantes[chave.strip()] = Decimal(valor.strip())
    return constantes

def carregar_taxas(caminho_arquivo):
    with open(caminho_arquivo, 'r') as f:
        taxas_raw = json.load(f)
    # Converte tudo para Decimal de forma segura
    return {k: Decimal(str(v)) for k, v in taxas_raw.items()}

def adicionar_taxa(preco: Decimal, chave_taxa: str) -> Decimal:
    taxa = TAXAS[chave_taxa]
    return preco / (um - taxa / Decimal(100))

def remover_taxa(preco: Decimal, chave_taxa: str) -> Decimal:
    taxa = TAXAS[chave_taxa]
    return preco * (um - taxa / Decimal(100))

def formatar_moeda(valor: Decimal, casas: int = 2, arredondar: bool = True) -> str:
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))

    if arredondar:
        q = Decimal('0.' + '0' * casas)
        valor = valor.quantize(q, rounding=ROUND_HALF_UP)

    s = f"{valor:f}"

    if '.' in s:
        inteira, decimal = s.split('.')
        decimal = (decimal + '0' * casas)[:casas]
    else:
        inteira = s
        decimal = '0' * casas

    return f"{inteira},{decimal}"

def media_geometrica(valor1: Decimal, valor2: Decimal):
    return (valor1 * valor2) ** meio

def calcular_parcela_com_entrada(preco: Decimal, numero_parcelas: int) -> tuple[Decimal, Decimal]:
    n = Decimal(numero_parcelas)
    taxa_restante = TAXAS[f"{int(n-1)}x"]
    parcela = preco / (um + (n - 1) * (Decimal(1) - taxa_restante / Decimal(100)))
    total = parcela * n
    return parcela, total

def calcular_preco_padrao(custo: Decimal, quantidade: Decimal = um) -> Decimal:
    custo_final = custo * quantidade
    return A * custo_final + B * (custo_final ** meio) + C

def calcular_preco_peca(custo: Decimal, reposicao: Decimal) -> Decimal:
    preco_minimo = calcular_preco_padrao(custo)
    preco_maximo = calcular_preco_padrao(reposicao)
    preco_medio = (preco_minimo + preco_maximo) / Decimal(2)
    preco = Decimal(2) * reposicao - preco_medio if preco_medio < reposicao else preco_medio
    return adicionar_taxa(preco, '1x').quantize(um, rounding=ROUND_CEILING)

def calcular_preco_maquina(custo_fabrica: Decimal, custo_nota: Decimal, reposicao: Decimal):
    carga = um + CARGA_OPERACIONAL / Decimal(100)
    base = media_geometrica(custo_nota ** meio, custo_nota) * carga + custo_nota
    venda_normal = adicionar_taxa(base, '10x')
    lucro_normal = base - custo_nota

    if custo_nota > custo_fabrica:
        preco_venda = (custo_fabrica + lucro_normal + base) / Decimal(2)
        preco_venda_vista = adicionar_taxa(preco_venda, '1x')
        preco_venda = adicionar_taxa(preco_venda, '10x')
        return venda_normal, True, preco_venda, preco_venda_vista

    venda_normal_vista = adicionar_taxa(base, '1x')
    return venda_normal, False, zero, venda_normal_vista

    base = (Decimal(2) * custo_nota + reposicao) / Decimal(3)
    venda_normal = adicionar_taxa(adicionar_taxa(base, '1x'), '10x')

    # Para exibição posterior vamos arredondar, mas aqui mantemos exato
    lucro_normal = remover_taxa(venda_normal, '10x') - custo_nota

    if custo_nota > custo_fabrica:
        return venda_normal, True, preco_venda, preco_venda_vista

    venda_normal_vista = adicionar_taxa(remover_taxa(venda_normal, '10x'), '1x')
    return venda_normal, False, zero, venda_normal_vista

def calcular_preco_acessorio(custo_fabrica: Decimal, custo_nota: Decimal, reposicao: Decimal) -> Decimal:
    *_, preco_maquina = calcular_preco_maquina(custo_fabrica, custo_nota, reposicao)
    return preco_maquina.quantize(centavo)

def calcular_preco_disco(custo_nota: Decimal, quantidade: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    custo_fabrica = custo_nota
    carga = um + CARGA_OPERACIONAL / Decimal(100)
    reposicao = custo_nota * carga

    #preco_total_unidade, *_ = calcular_preco_maquina(custo_fabrica, custo_nota, reposicao)
    preco_total_unidade = adicionar_taxa(custo_nota * (carga ** meio), '10x')
    preco_total_unidade = preco_total_unidade.quantize(centavo)
    preco_total = (preco_total_unidade * quantidade).quantize(centavo)

    preco_unidade = adicionar_taxa(remover_taxa(preco_total_unidade, '1x'), f'{quantidade if quantidade <= 10 else 10}x')

    for n in range(1, int(quantidade / Decimal('10'))):
        preco_unidade = adicionar_taxa(remover_taxa(preco_unidade, '1x'), '10x')

    r = int(quantidade / Decimal('10'))

    if r:
        preco_unidade = adicionar_taxa(remover_taxa(preco_unidade, '1x'), f'{r}x')

    return preco_unidade.quantize(centavo), preco_total, preco_total_unidade

def calcular_preco_dewalt(minimo_anunciado: Decimal) -> tuple[Decimal, Decimal]:
    preco_vista = remover_taxa(minimo_anunciado, "1x")
    preco_venda = adicionar_taxa(preco_vista, "10x")   # ou '6x' ? confirme no seu caso
    bonus = minimo_anunciado - preco_vista
    return preco_venda, bonus

def preco_maquina(custo_fabrica: Decimal, custo_nota: Decimal, reposicao: Decimal):
    venda_normal, tem_desconto, preco_prazo, preco_vista = calcular_preco_maquina(custo_fabrica, custo_nota, reposicao)

    if tem_desconto:
        print(f"Preço normal:               R$ {formatar_moeda(venda_normal.quantize(centavo))}")
        print(f"PROMOÇÃO: R$ {formatar_moeda(preco_prazo.quantize(centavo))} em até 10x no cartão, "
              f"R$ {formatar_moeda(preco_vista.quantize(centavo))} à vista")
    else:
        print(f"R$ {formatar_moeda(venda_normal.quantize(centavo))} em até 10x no cartão")
        print(f"R$ {formatar_moeda(preco_vista.quantize(centavo))} à vista")

def preco_acessorio(custo_fabrica: Decimal, custo_nota: Decimal, reposicao: Decimal):
    preco = calcular_preco_acessorio(custo_fabrica, custo_nota, reposicao)
    print(f"Preço: R$ {formatar_moeda(preco.quantize(centavo))}")

def comissao_mao_de_obra(mao_de_obra):
    return COMISSAO_MAO_DE_OBRA / Decimal(100) * mao_de_obra

def comissao_pecas(bruto, mao_de_obra, lucro):
    carga_operacional = CARGA_OPERACIONAL / Decimal(100)
    comissao_mao = comissao_mao_de_obra(mao_de_obra)
    return ((bruto - mao_de_obra) * carga_operacional + lucro + comissao_mao - mao_de_obra)/(um + carga_operacional) * Decimal(0.1)

def calcular_comissao_com_desconto(bruto, mao, lucro, desconto):
    bruto = Decimal(bruto)
    mao = Decimal(mao)
    lucro = Decimal(lucro)
    desconto = Decimal(desconto)

    mao_nova = mao * (um - desconto / bruto)
    bruto_nova = bruto - desconto
    lucro_nova = lucro - desconto

    comissao_mao_nova = comissao_mao_de_obra(mao_nova)
    comissao_peca_nova = comissao_pecas(bruto_nova, mao_nova, lucro_nova)

    return comissao_mao_nova + comissao_peca_nova

def encontrar_desconto_maximo(bruto, mao, lucro):
    bruto = Decimal(bruto)
    mao = Decimal(mao)
    lucro = Decimal(lucro)
    comissao_minima = comissao_mao_de_obra(mao)

    if comissao_minima <= 0:
        return 0

    baixo = zero
    alto = bruto.quantize(um, rounding=ROUND_FLOOR) - um
    
    melhor_desconto = zero

    while baixo <= alto:
        meio = (baixo + alto) // Decimal(2)

        comissao_atual = calcular_comissao_com_desconto(bruto, mao, lucro, meio)

        if comissao_atual >= comissao_minima:
            melhor_desconto = meio
            baixo = meio + um
        else:
            alto = meio - um

    return melhor_desconto.quantize(zero, rounding=ROUND_FLOOR)

def imprimir_custos(custo_fabrica: Decimal, custo_nota: Decimal, reposicao: Decimal):
    print(f"- Custo de Fábrica:   R$ {formatar_moeda(custo_fabrica.quantize(Decimal('0.003')), 3)}")
    print(f"- Custo nota:         R$ {formatar_moeda(custo_nota.quantize(Decimal('0.003')), 3)}")
    print(f"- Custo reposição:    R$ {formatar_moeda(reposicao.quantize(Decimal('0.003')), 3)}\n")

def imprimir_ajuda(erro=True):
    if erro:
        print("ERRO: comando inválido. Opções:")
    print("peca [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>%")
    print("maquina [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>%")
    print("acessorio [<custo fabrica>] <custo nota> | <custo fabrica> <ipi>%")
    print("disco <custo_nota> <quantidade>")
    print("dewalt <mínimo anunciado>")
    print("vonder <preço normal> <preço sem impostos> [<preco com impostos>]")
    print("parcelamento <preço> <parcelas>")
    print("os <preço peças> <mão de obra> <lucro>")
    print("ajuda / help")
    print("sair / exit")

def parse_decimal(s: str) -> Decimal:
    """Converte string (aceita , ou .) para Decimal"""
    return Decimal(s.replace(',', '.'))

def processar_comando(argumentos, tipo_anterior=None):
    if not argumentos:
        return tipo_anterior

    tipos_validos = {'peca', 'maquina', 'acessorio', 'disco', 'dewalt', 'vonder', 'parcelamento', 'os', 'sair', 'exit', 'ajuda', 'help'}
    cmd = argumentos[0].lower()

    correspondentes = [t for t in tipos_validos if t.startswith(cmd)]

    if len(correspondentes) == 1:
        tipo = correspondentes[0]
        argumentos = [tipo] + argumentos[1:]
    elif len(correspondentes) > 1:
        print(f"Comando ambíguo: {cmd} pode ser {', '.join(correspondentes)}")
        return tipo_anterior
    elif cmd in tipos_validos:
        tipo = cmd
    elif tipo_anterior:
        tipo = tipo_anterior
        argumentos = [tipo] + argumentos
    else:
        imprimir_ajuda()
        return None

    if tipo in ('sair', 'exit'):
        print("Encerrando o programa.")
        sys.exit(0)

    if tipo in ('ajuda', 'help'):
        imprimir_ajuda(erro=False)
        return tipo

    # dewalt
    if tipo == 'dewalt':
        if len(argumentos) != 2:
            imprimir_ajuda()
            return tipo
        try:
            minimo = parse_decimal(argumentos[1])
            venda, bonus = calcular_preco_dewalt(minimo)
            print(f"Preço de venda:     R$ {formatar_moeda(venda.quantize(centavo))}")
            print(f"À VISTA:            R$ {formatar_moeda(minimo.quantize(centavo))}")
        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    # vonder
    if tipo == 'vonder':
        if len(argumentos) < 3:
            imprimir_ajuda()
            return tipo
        try:
            p_normal = parse_decimal(argumentos[1])
            p_sem = parse_decimal(argumentos[2])
            p_com = p_sem if len(argumentos) < 4 else parse_decimal(argumentos[3])

            p_normal_com = p_normal * p_com / p_sem
            repos = p_normal_com * (um + CARGA_OPERACIONAL / Decimal(100))
            imprimir_custos(p_normal, p_normal_com, repos)
            preco_maquina(p_com, p_normal_com, repos)
        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    # peca / maquina / acessorio
    if tipo in ('peca', 'maquina', 'acessorio'):
        if len(argumentos) not in (2, 3):
            imprimir_ajuda()
            return tipo
        try:
            custo_fab = parse_decimal(argumentos[1])
            custo_nota = custo_fab

            if len(argumentos) == 3:
                arg = argumentos[2]
                if arg.endswith('%'):
                    ipi = parse_decimal(arg[:-1])
                    custo_nota = custo_fab * (um + ipi / Decimal(100))
                else:
                    custo_nota = parse_decimal(arg)

            reposicao = custo_nota * (um + CARGA_OPERACIONAL / Decimal(100))

            imprimir_custos(custo_fab, custo_nota, reposicao)

            if tipo == 'peca':
                venda = calcular_preco_peca(custo_nota, reposicao)
                print(f"Preço de venda:     R$ {formatar_moeda(venda.quantize(centavo))}")
            elif tipo == 'maquina':
                preco_maquina(custo_fab, custo_nota, reposicao)
            elif tipo == 'acessorio':
                preco_acessorio(custo_fab, custo_nota, reposicao)

        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    # disco
    if tipo == 'disco':
        if len(argumentos) != 3:
            imprimir_ajuda()
            return tipo
        try:
            custo_nota = parse_decimal(argumentos[1])
            qtd_str = argumentos[2]
            qtd = Decimal(qtd_str) if '.' in qtd_str else int(qtd_str)

            if qtd <= 0:
                print("Quantidade precisa ser > 0")
                return tipo

            pu, pt, ptu = calcular_preco_disco(custo_nota, qtd)

            print(f"Custo unitário:           R$ {formatar_moeda(pu.quantize(centavo))}")
            print(f"{qtd} unidades:           R$ {formatar_moeda(pt.quantize(centavo))} "
                  f"(R$ {formatar_moeda(ptu.quantize(centavo))} cada)")
        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    # os (versão simplificada – a original tinha fórmula estranha)
    if tipo == 'os':
        if len(argumentos) not in (3, 4):
            imprimir_ajuda()
            return tipo
        try:
            pecas = parse_decimal(argumentos[1])
            mao = parse_decimal(argumentos[2])
            lucro = zero if len(argumentos) == 3 else parse_decimal(argumentos[3])

            if pecas <= 0:
                print("Preço das peças deve ser > 0")
                return tipo
            if mao < 0:
                print("Mão de obra não pode ser negativa")
                return tipo

            bruto = pecas + mao

            if lucro > zero:
                desconto = encontrar_desconto_maximo(bruto, mao, lucro)
            else:
                preco_min = min(mao, pecas)
                preco_max = max(mao, pecas)
                #desconto = (preco_max * preco_min * preco_min) / (bruto * bruto)
                desconto = Decimal('0.14') * preco_min * preco_max / (preco_max + 1)
                desconto = desconto.quantize(um, rounding=ROUND_FLOOR)

            liquido = bruto - desconto

            print(f"Preço bruto:      R$ {formatar_moeda(bruto.quantize(centavo))}")
            print(f"Desconto:         R$ {formatar_moeda(desconto.quantize(centavo))}")
            print(f"Preço líquido:    R$ {formatar_moeda(liquido.quantize(centavo))}")
        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    # parcelamento
    if tipo == 'parcelamento':
        if len(argumentos) != 3:
            imprimir_ajuda()
            return tipo
        try:
            preco = parse_decimal(argumentos[1])
            chave = argumentos[2]

            if preco <= 0:
                print("Preço deve ser > 0")
                return tipo
            if chave not in TAXAS:
                print(f"Parcela inválida. Opções: {', '.join(sorted(TAXAS))}")
                return tipo

            vista = remover_taxa(preco, chave)

            for k in TAXAS:
                final = adicionar_taxa(vista, k)
                if k[0].isdigit():
                    n = int(''.join(c for c in k if c.isdigit()))
                    if n == 1:
                        print(f"{k:<6}: R$ {formatar_moeda(final.quantize(centavo))}")
                    else:
                        p_sem = f"{k} {formatar_moeda(final / Decimal(n))} (R$ {formatar_moeda(final)})"
                        vp, vt = calcular_parcela_com_entrada(vista, n)
                        p_com = f" | 1+{n-1}x R$ {formatar_moeda(vp.quantize(centavo))} (R$ {formatar_moeda(vt.quantize(Decimal('0.01')))})"
                        print(f"{p_sem}{p_com}")
                else:
                    print(f"{k:<6}: R$ {formatar_moeda(final.quantize(centavo))}")
        except Exception as e:
            print(f"Erro: {e}")
        return tipo

    imprimir_ajuda()
    return tipo


if __name__ == "__main__":
    constantes = carregar_constantes('vars.txt')
    A = constantes.get("A", zero)
    B = constantes.get("B", zero)
    C = constantes.get("C", zero)
    CARGA_OPERACIONAL = constantes.get("CARGA_OPERACIONAL", zero)
    COMISSAO_MAO_DE_OBRA = constantes.get("COMISSAO_MAO_DE_OBRA", zero)  # não usada no código atual

    TAXAS = carregar_taxas("taxas.json")

    tipos_validos = {'peca', 'maquina', 'acessorio', 'disco', 'dewalt', 'vonder', 'parcelamento', 'os', 'sair', 'exit', 'ajuda', 'help'}
    tipo = None

    if len(sys.argv) > 1:
        processar_comando(sys.argv[1:])
        sys.exit(0)

    print("Bem-vindo ao calculador. Digite um comando (ou 'sair' para sair):")

    while True:
        try:
            linha = input(f"{tipo or ''}> ").strip()
            if not linha:
                continue
            args = linha.split()
            print()
            tipo = processar_comando(args, tipo)
            print()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break
