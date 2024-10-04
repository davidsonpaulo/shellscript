#!/usr/bin/env python3

from math import floor, ceil, sqrt
import sys
import json

"""
A = 980 / 891
B = 262 / 81
C = 593 / 891

CARGA_OPERACIONAL = 43.76
DEWALT_FEE = 3

TAXAS = {
    'dinheiro': 0,
    'debito': 0.88,
    '1x': 3.78,
    '2x': 2.7 + 2.18,
    '3x': 2.7 + 2.88,
    '4x': 2.7 + 3.6,
    '5x': 2.7 + 4.29,
    '6x': 2.7 + 4.98,
    '7x': 2.9 + 5.67,
    '8x': 2.9 + 6.34,
    '9x': 2.9 + 7.01,
    '10x': 2.9 + 7.68
}
"""

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

def price_maquina(cost, restock):
    return add_taxa((cost + restock) / 2, '10x')

def print_help():
    print("ERRO: comando inválido. Opções:")
    print("peca <preço custo> <preço reposição>")
    print("peca-dewalt <preço custo> <ipi>")
    print("ipi <preço custo> <ipi>")
    print("maquina <preço custo> <preço reposição>")
    print("parcelamento <preço> <parcelas>")
    print("exit")

def process_command(args):
    if len(args) == 0:
        return

    tipo = args[0]

    if tipo in ('help', 'ajuda'):
        print_help()
        return

    if tipo in ('peca', 'peca-dewalt', 'maquina', 'ipi'):
        if len(args) != 3:
            print_help()
            return
        try:
            custo = float(args[1])

            if tipo in ('ipi', 'peca-dewalt'):
                is_percentage = args[2][-1] == "%"
                ipi = float(args[2]) if not is_percentage else float(args[2][:-1])

                if tipo == 'peca-dewalt':
                    custo = custo * (1 + DEWALT_FEE / 100)

                custo_nota = custo * (1 + ipi / 100) if is_percentage else ipi
                reposicao = custo_nota * (1 + CARGA_OPERACIONAL / 100)
            else:
                reposicao = float(args[2])

                # If reposicao is 0, calculate it based on CARGA_OPERACIONAL
                if reposicao == 0:
                    reposicao = custo * (1 + CARGA_OPERACIONAL / 100)
        except ValueError:
            print("Custo e reposição devem ser números.")
            return

        if tipo in ( 'ipi', 'peca', 'peca-dewalt' ):
            venda = round_price(price_peca(custo, reposicao))

            if tipo in ('ipi', 'peca-dewalt'):
                print(f"- Custo de Fábrica:\tR$ {custo:.3f}\n- Custo nota:\t\tR$ {custo_nota:.3f}\n- Custo reposição:\tR$ {reposicao:.3f}\n")

            print(f"Preço de venda:\t\tR$ {venda:.2f}")
        elif tipo == 'maquina':
            venda = round_price(price_maquina(custo, reposicao))
            print(f"Preço de venda:\t\tR$ {venda:.2f}")
        elif tipo == 'ipi':
            custo_nota = custo

    elif tipo == 'parcelamento':
        if len(args) != 3:
            print_help()
            return
        try:
            preco = float(args[1])
            parcela = args[2]
        except ValueError:
            print("Preço deve ser um número.")
            return

        if preco <= 0:
            print("O preço deve ser maior que zero.")
            return

        if parcela not in TAXAS:
            print(f"Parcela inválida: '{parcela}'. Opções: {', '.join(TAXAS.keys())}")
            return

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
    print("Bem-vindo ao calculador. Digite um comando (ou 'exit' para sair):")

    while True:
        try:
            user_input = input("> ").strip()  # Wait for user input
        except EOFError:
            break  # Handle Ctrl+D for exit

        if user_input.lower() == 'exit':
            print("Encerrando o programa.")
            break

        args = user_input.split()
        print()
        process_command(args)
        print()
