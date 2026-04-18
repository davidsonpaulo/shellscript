import os
import sys
from datetime import datetime, date, timedelta

# ===================== IMPORTS DO ARQUIVO COMPARTILHADO =====================
from common import (
    carregar_templates_globais,
    carregar_snippets_globais,
    TEMPLATES,
    SNIPPETS,
    parse_parametros,
    extrair_variaveis_e_opcionais,
    editar_parametros
)

# ===================== MENU PRINCIPAL =====================
def main():
    carregar_templates_globais()
    carregar_snippets_globais()

    print("=== Gerenciador de Agendamentos WhatsApp (editor) ===\n")

    while True:
        print("\n" + "="*60)
        print("1. Listar entradas")
        print("2. Criar nova entrada")
        print("3. Editar entrada")
        print("4. Excluir entrada")
        print("5. Desativar entrada")
        print("r. Recarregar / Reiniciar")
        print("6. Sair")
        print("="*60)

        opcao = input("\nEscolha (1-6 ou r): ").strip().lower()

        if opcao in ["r", "recarregar"]:
            print("\n🔄 Reiniciando via launcher.bat...")
            sys.exit(42)

        # ===================== LISTAR =====================
        if opcao == "1":
            linhas = carregar_config()
            entradas = obter_entradas(linhas)
            if not entradas:
                print("Nenhuma entrada cadastrada.")
                continue
            print(f"\n{len(entradas)} entrada(s) encontrada(s):\n")
            for i, e in enumerate(entradas, 1):
                print(f"{i:2d}. {e['telefone']} | {e['nome'][:30]:30} | {e['template']:20} | Freq: {e['frequencia']}")

        # ===================== CRIAR NOVA ENTRADA (VERSÃO FINAL CORRIGIDA) =====================
        elif opcao == "2":
            linhas = carregar_config()

            telefone = input("\nTELEFONE: ").strip()
            while not telefone.isdigit() or len(telefone) < 10:
                telefone = input("TELEFONE inválido: ").strip()

            nome = input("NOME: ").strip()
            while not nome:
                nome = input("NOME (obrigatório): ").strip()

            temp_list = sorted(TEMPLATES.keys())
            print("\nTemplates disponíveis:")
            for i, t in enumerate(temp_list, 1):
                print(f"{i:2d}. {t}")

            try:
                idx_t = int(input("\nNúmero do TEMPLATE: ")) - 1
                template_nome = temp_list[idx_t]
            except:
                print("Template inválido.")
                continue

            template_texto = TEMPLATES[template_nome]
            info_vars = extrair_variaveis_e_opcionais(template_texto)

            params_dict = {}

            print(f"\nConfigurando parâmetros para template '{template_nome}':")

            # Lista todas as variáveis do template
            todas_vars = sorted(info_vars['todas'])

            for var in todas_vars:
                # É opcional se for raiz opcional OU se for usado dentro de algum if (condicional)
                is_opcional = (var in info_vars['opcionais_raiz']) or \
                              any(var in deps for deps in info_vars['condicionais'].values())

                status = "(opcional - Enter = pular)" if is_opcional else "(OBRIGATÓRIO)"
                val = input(f"  {var} {status}: ").strip()

                while not val and not is_opcional:
                    val = input(f"  {var} (OBRIGATÓRIO): ").strip()

                if val:
                    params_dict[var] = val

            # Pergunta variáveis dependentes das condições que foram preenchidas
            for var_cond, deps in info_vars['condicionais'].items():
                if var_cond in params_dict and params_dict[var_cond]:
                    print(f"\n→ '{var_cond}' foi definido → preencha as dependentes:")
                    for var_dep in sorted(set(deps)):
                        if var_dep in params_dict:
                            continue
                        val = input(f"  {var_dep} : ").strip()
                        while not val:
                            val = input(f"  {var_dep} (obrigatório): ").strip()
                        params_dict[var_dep] = val

            parametros_str = ",".join(f"{k}={v}" for k, v in params_dict.items()) if params_dict else ""

            # Frequência e data
            freq = input("\nFREQUENCIA (ex: 1/1): ").strip()
            data_str = input("Data da PRIMEIRA execução (dd/mm/yyyy): ").strip()
            try:
                primeira = datetime.strptime(data_str, "%d/%m/%Y").date()
            except:
                primeira = date.today()

            ultimo_envio = (primeira - timedelta(days=1)).isoformat()

            nova_linha = f"{telefone}\t{nome}\t{template_nome}\t{parametros_str}\t{freq}\t{ultimo_envio}\n"
            linhas.append(nova_linha)
            salvar_config(linhas)
            print(f"\n✅ Nova entrada criada com sucesso!")

        # ===================== EDITAR ENTRADA (VERSÃO FINAL CORRIGIDA) =====================
        elif opcao == "3":
            linhas = carregar_config()
            entradas = obter_entradas(linhas)
            if not entradas:
                print("Nenhuma entrada cadastrada.")
                continue

            for i, e in enumerate(entradas, 1):
                print(f"{i:2d}. {e['telefone']} - {e['nome']} ({e['template']})")

            try:
                idx = int(input("\nNúmero da entrada para editar: ")) - 1
                if not (0 <= idx < len(entradas)):
                    print("Número inválido.")
                    continue
                ent = entradas[idx]                    # Referência ao dict
            except:
                print("Entrada inválida.")
                continue

            print(f"\nEditando: {ent['nome']} ({ent['telefone']})")

            while True:
                print("\nCampos disponíveis:")
                print("1. TELEFONE")
                print("2. NOME")
                print("3. TEMPLATE")
                print("4. PARÂMETROS")
                print("5. FREQUENCIA")
                print("6. ULTIMO_ENVIO")
                print("   (Pressione Enter vazio para finalizar a edição)")

                campo = input("\nQual campo deseja editar? (1-6 ou Enter para sair): ").strip()

                if not campo:
                    break

                if campo == "1":
                    novo = input(f"Novo TELEFONE [{ent.get('telefone', '')}]: ").strip()
                    if novo:
                        ent["telefone"] = novo

                elif campo == "2":
                    novo = input(f"Novo NOME [{ent.get('nome', '')}]: ").strip()
                    if novo:
                        ent["nome"] = novo

                elif campo == "3":   # Mudar template
                    temp_list = sorted(TEMPLATES.keys())
                    print("\nTemplates disponíveis:")
                    for i, t in enumerate(temp_list, 1):
                        print(f"{i:2d}. {t}")
                    try:
                        t_idx = int(input("\nNovo TEMPLATE (número): ")) - 1
                        if 0 <= t_idx < len(temp_list):
                            novo_template = temp_list[t_idx]
                            if novo_template != ent.get("template"):
                                print(f"Template alterado para: {novo_template}")
                                ent["template"] = novo_template
                                print("\nIniciando edição dos parâmetros do novo template...")
                                editar_parametros(ent)
                            else:
                                print("Template não foi alterado.")
                    except:
                        print("Entrada inválida.")

                elif campo == "4":
                    editar_parametros(ent)

                elif campo == "5":
                    novo = input(f"Nova FREQUENCIA (atual: {ent.get('frequencia', '1/1')}): ").strip()
                    if "/" in novo:
                        try:
                            x, y = map(int, novo.split("/"))
                            if x >= 0 and y > 0:
                                ent["frequencia"] = novo
                        except:
                            print("Formato inválido.")

                elif campo == "6":
                    novo = input(f"Novo ULTIMO_ENVIO (YYYY-MM-DD, atual: {ent.get('ultimo_envio', '')}): ").strip()
                    try:
                        date.fromisoformat(novo)
                        ent["ultimo_envio"] = novo
                    except:
                        print("Formato inválido.")

                else:
                    print("Opção inválida.")

            # ===================== SALVAR AS ALTERAÇÕES =====================
            # Reconstrói a linha completa com os valores atualizados do dict 'ent'
            nova_linha = (
                f"{ent.get('telefone', '')}\t"
                f"{ent.get('nome', '')}\t"
                f"{ent.get('template', '')}\t"
                f"{ent.get('parametros_str', '')}\t"
                f"{ent.get('frequencia', '1/1')}\t"
                f"{ent.get('ultimo_envio', '')}\n"
            )

            linhas[ent["idx_linha"]] = nova_linha
            salvar_config(linhas)
            print("✅ Edição finalizada e salva com sucesso no config.txt!")

        # ===================== EXCLUIR ENTRADA =====================
        elif opcao == "4":
            linhas = carregar_config()
            entradas = obter_entradas(linhas)
            if not entradas:
                print("Nenhuma entrada para excluir.")
                continue

            for i, e in enumerate(entradas, 1):
                print(f"{i:2d}. {e['telefone']} - {e['nome']} ({e['template']})")

            try:
                idx = int(input("\nNúmero da entrada para EXCLUIR: ")) - 1
                if 0 <= idx < len(entradas):
                    if input(f"Confirmar exclusão de '{entradas[idx]['nome']}'? (s/n): ").lower() == "s":
                        del linhas[entradas[idx]["idx_linha"]]
                        salvar_config(linhas)
                        print("✅ Entrada excluída com sucesso.")
                    else:
                        print("Exclusão cancelada.")
                else:
                    print("Número inválido.")
            except:
                print("Entrada inválida.")

        # ===================== DESATIVAR ENTRADA =====================
        elif opcao == "5":
            linhas = carregar_config()
            entradas = obter_entradas(linhas)
            if not entradas:
                print("Nenhuma entrada para desativar.")
                continue

            for i, e in enumerate(entradas, 1):
                print(f"{i:2d}. {e['telefone']} - {e['nome']} ({e['template']})")

            try:
                idx = int(input("\nNúmero da entrada para DESATIVAR: ")) - 1
                if 0 <= idx < len(entradas):
                    if input(f"Confirmar desativação de '{entradas[idx]['nome']}'? (s/n): ").lower() == "s":
                        ent = entradas[idx]
                        nova_linha = f"{ent['telefone']}\t{ent['nome']}\t{ent['template']}\t{ent['parametros_str']}\t0/1\t2099-12-31\n"
                        linhas[ent["idx_linha"]] = nova_linha
                        salvar_config(linhas)
                        print("✅ Entrada desativada com sucesso (não será mais enviada).")
                    else:
                        print("Desativação cancelada.")
                else:
                    print("Número inválido.")
            except:
                print("Entrada inválida.")
        elif opcao == "6":
            print("Encerrando gerenciador.")
            break

        else:
            print("Opção inválida.")

# ===================== FUNÇÕES AUXILIARES (mantidas) =====================
def carregar_config():
    if not os.path.exists("config.txt"):
        return []
    with open("config.txt", "r", encoding="utf-8") as f:
        return f.readlines()

def obter_entradas(linhas):
    # (sua função original mantida)
    entradas = []
    for i, linha in enumerate(linhas):
        if not linha.strip() or linha.strip().startswith("TELEFONE"):
            continue
        partes = [p.strip() for p in linha.strip().split("\t")]
        if len(partes) >= 6:
            entradas.append({
                "idx_linha": i,
                "telefone": partes[0],
                "nome": partes[1],
                "template": partes[2],
                "parametros_str": partes[3],
                "frequencia": partes[4],
                "ultimo_envio": partes[5] if len(partes) > 5 else "",
                "linha_original": linha
            })
    return entradas

def salvar_config(linhas):
    # (sua função de formatação mantida)
    # ... (cole aqui sua função reformatar_config + salvar_config original se quiser)
    with open("config.txt", "w", encoding="utf-8") as f:
        f.writelines(linhas)
    print("✅ config.txt salvo.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGerenciador encerrado pelo usuário.")
