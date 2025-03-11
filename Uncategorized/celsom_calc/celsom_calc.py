#!/usr/bin/env python3

from math import floor, ceil, sqrt
import sys
import json

def load_constants(file_path):
    constants = {}
    with open(file_path, 'r') as f:
        for line in f:
            # Skip empty lines and comments
            if line.strip() and not line.startswith('#'):
                key, value = line.split('=')
                constants[key.strip()] = float(value.strip())
    return constants

def load_taxas(file_path):
    with open(file_path, 'r') as f:
        taxas = json.load(f)
    return taxas

def add_fee(price, fee):
    return price * (1 + fee / 100)

def add_taxa(price, taxa):
    return price / (1 - TAXAS[taxa] / 100)

def get_cash_price(price, taxa):
    return price * (1 - TAXAS[taxa] / 100)

def round_price(price):
    floored, ceiled = floor(price), ceil(price)
    return ceiled if price - floored > ceiled - price else floored

def upfront_installment(price, number_of_installments):
    installment = price / (1 + (number_of_installments - 1) * (1 - TAXAS[f"{number_of_installments - 1}x"] / 100))
    total = installment * number_of_installments
    return installment, total

def price_standard(cost, quantity=1):
    final_cost = cost * quantity
    return A * final_cost + B * sqrt(final_cost) + C

def price_peca(cost, restock):
    price1 = price_standard(cost)
    price2 = price_standard(restock)
    average = (price1 + price2) / 2
    return add_taxa(2 * restock - average if average < restock else average, '1x')

def price_maquina(factory, invoice, restock):
    return add_taxa((factory + invoice + restock) / 3, '10x')

def print_help(error = True):
    if error:
        print("ERRO: comando inválido. Opções:")

    print("peca <custo de fábrica> <custo reposição>")
    print("peca-dewalt <custo sem impostos> <custo com impostos / ipi%>")
    print("maquina <custo de fábrica> <custo reposição>")
    print("parcelamento <preço> <parcelas>")
    print("os <lucro total> <% lucro>")
    print("ajuda / help")
    print("sair / exit")

def get_tipo(tipo, tipos_validos):
    matched = [t for t in tipos_validos if t.startswith(tipo)]

    if len(matched) == 1:
        return matched[0]
    else:
        return tipo

def add_minimum_unit(num):
    # Convert to string to easily inspect decimal places
    num_str = str(num)

    # Check if the number is integer or float
    if '.' in num_str:
        # Find the position of the decimal point
        decimal_pos = num_str.index('.')
        # Check for trailing zeros after the decimal
        decimal_places = 0 if num_str.endswith('.0') else len(num_str) - decimal_pos - 1

        # If number ends in .0, treat as integer
        if decimal_places == 0:
            return num + 1

        # Calculate the smallest unit based on decimal places
        unit = 10 ** -decimal_places
        return num + unit
    else:
        # If it's an integer, just add 1
        return num + 1

def process_command(args, tipo = None):
    if len(args) == 0:
        return

    args0 = get_tipo(args[0], tipos_validos)

    if tipo and args0 not in tipos_validos:
        args = [tipo] + args
    elif args0 in tipos_validos:
        tipo = args0
    else:
        print_help()
        return

    if tipo in ( 'sair', 'exit' ):
        print("Encerrando o programa.")
        sys.exit(0)

    if tipo in ('help', 'ajuda'):
        print_help(False)
        return

    if tipo in ('peca', 'peca-dewalt', 'maquina'):
        if len(args) != 3:
            print_help()
            return tipo
        try:
            custo = float(args[1])

            if tipo == 'peca-dewalt':
                custo = custo * (1 + DEWALT_FEE / 100)

            is_percentage = args[2][-1] == "%"

            if is_percentage:
                ipi = float(args[2][:-1])
                custo_nota = custo * (1 + ipi / 100)
            else:
                custo_nota = float(args[2])

            if add_minimum_unit(custo_nota) < custo * (1 + CARGA_OPERACIONAL / 100):
                reposicao = custo_nota * (1 + CARGA_OPERACIONAL / 100)
            else:
                reposicao = custo_nota
                custo_nota = reposicao / (1 + CARGA_OPERACIONAL / 100)

                if custo_nota < custo:
                    custo_nota = custo

        except ValueError:
            print("Custo e reposição devem ser números.")
            return tipo

        if tipo in ( 'peca', 'peca-dewalt' ):
            venda = round_price(price_peca(custo, reposicao))

            print(f"- Custo de Fábrica:\tR$ {custo:.3f}\n- Custo nota:\t\tR$ {custo_nota:.3f}\n- Custo reposição:\tR$ {reposicao:.3f}\n")
            print(f"Preço de venda:\t\tR$ {venda:.2f}")
        elif tipo == 'maquina':
            venda = round_price(price_maquina(custo, custo_nota, reposicao))
            print(f"- Custo de Fábrica:\tR$ {custo:.3f}\n- Custo nota:\t\tR$ {custo_nota:.3f}\n- Custo reposição:\tR$ {reposicao:.3f}\n")
            print(f"Preço de venda:\t\tR$ {venda:.2f}")
    elif tipo == 'os':
        if len(args) != 3:
            print_help()
            return tipo
        try:
            lucro = float(args[1])
            margem = float(args[2])
        except ValueError:
            print("Preço e margem devem ser números.")
            return tipo

        if lucro < 0 or margem < 0:
            print("Preço e margem devem ser maiores que zero.")
            return tipo

        desconto = round_price(0.15 * (margem / 100) * lucro)

        print(f"Desconto: R$ {desconto:.2f}")
    elif tipo == 'parcelamento':
        if len(args) != 3:
            print_help()
            return tipo
        try:
            preco = float(args[1])
            parcela = args[2]
        except ValueError:
            print("Preço deve ser um número.")
            return tipo

        if preco <= 0:
            print("O preço deve ser maior que zero.")
            return tipo

        if parcela not in TAXAS:
            print(f"Parcela inválida: '{parcela}'. Opções: {', '.join(TAXAS.keys())}")
            return tipo

        # Handle parcelamento
        preco_a_vista = get_cash_price(preco, parcela)
        for taxa, valor_taxa in TAXAS.items():
            preco_final = add_taxa(preco_a_vista, taxa)

            if taxa[0].isdigit():
                number_of_installments = int(''.join(filter(str.isdigit, taxa)))

                if number_of_installments == 1:
                    # Special case for 1x (one-time payment)
                    print(f"{taxa}: R$ {preco_final:.2f}")
                else:
                    sem_entrada = f"{taxa} {preco_final / number_of_installments:.2f} (R$ {preco_final:.2f})"
                    valor_parcela, valor_total = upfront_installment(preco_a_vista, number_of_installments)
                    com_entrada = f" | 1+{number_of_installments - 1}x R$ {valor_parcela:.2f} (R$ {valor_total:.2f})"
                    print(f"{sem_entrada}{com_entrada}")
            else:
                # For non-digit-based options like 'debito' and 'dinheiro'
                print(f"{taxa}: R$ {preco_final:.2f}")

    return tipo

if __name__ == "__main__":
    # Load the constants
    constants = load_constants('vars.txt')

    A = constants.get("A")
    B = constants.get("B")
    C = constants.get("C")
    CARGA_OPERACIONAL = constants.get("CARGA_OPERACIONAL")
    DEWALT_FEE = constants.get("DEWALT_FEE")
    TAXAS = load_taxas("taxas.json")

    # Check if arguments are passed
    if len(sys.argv) > 1:
        # Process the arguments directly if any are provided
        process_command(sys.argv[1:])
        sys.exit(0)  # Exit after processing the command-line arguments

    # Interactive mode if no arguments are passed
    print("Bem-vindo ao calculador. Digite um comando (ou 'sair' para sair):")

    tipos_validos = ( 'peca', 'peca-dewalt', 'maquina', 'parcelamento', 'os', 'sair', 'exit', 'ajuda', 'help' )
    tipo = None

    while True:
        try:
            user_input = input(f"{tipo if tipo else ''}> ").strip().lower()  # Wait for user input
        except EOFError:
            break  # Handle Ctrl+D for exit

        args = user_input.split()
        print()
        tipo = process_command(args, tipo)
        print()
