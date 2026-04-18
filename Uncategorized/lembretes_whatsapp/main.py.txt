import os
import sys
from datetime import date
import urllib.parse
import subprocess
import platform

from common import (
    carregar_templates_globais,
    carregar_snippets_globais,
    TEMPLATES,
    SNIPPETS,
    parse_parametros,
    processar_mensagem,
    pode_enviar
)

# ===================== MAIN =====================
def main():
    carregar_templates_globais()
    carregar_snippets_globais()

    print("=== Sistema de Lembretes WhatsApp ===\n")

    while True:
        linhas = []
        if os.path.exists("config.txt"):
            with open("config.txt", "r", encoding="utf-8") as f:
                linhas = f.readlines()

        candidatos = []
        for i, linha in enumerate(linhas):
            if i == 0 and linha.strip().startswith("TELEFONE"):
                continue
            partes = [p.strip() for p in linha.strip().split("\t") if p.strip()]
            if len(partes) < 6:
                continue

            telefone, nome, template_nome, param_str, freq, ultimo = partes[:6]

            if template_nome not in TEMPLATES:
                continue

            if pode_enviar(freq, ultimo):
                candidatos.append({
                    "idx": i,
                    "telefone": telefone,
                    "nome": nome,
                    "template": template_nome,
                    "params": parse_parametros(param_str),
                    "freq": freq,
                    "ultimo": ultimo,
                    "linha_original": linha
                })

        if not candidatos:
            print("Nenhuma mensagem disponível no momento.")
            escolha = input("\nEnter → verificar | r → recarregar | c → sair → ").strip().lower()

            if escolha in ["r", "recarregar"]:
                print("\n🔄 Reiniciando via launcher.bat...")
                sys.exit(42)

            if escolha in ["c", "sair", "q"]:
                break
            continue

        print(f"{len(candidatos)} mensagem(s) pronta(s):\n")
        for i, cand in enumerate(candidatos, 1):
            print(f"{i:2d}. {cand['nome']} → {cand['template']}")

        escolha = input("\nNúmero ou Enter (primeira) | r = recarregar | c = sair → ").strip().lower()

        if escolha in ["r", "recarregar"]:
            print("\n🔄 Reiniciando via launcher.bat...")
            sys.exit(42)
        if escolha in ["c", "sair", "q"]:
            break

        idx = 0 if escolha == "" else int(escolha) - 1
        if idx < 0 or idx >= len(candidatos):
            continue

        cand = candidatos[idx]
        mensagem = processar_mensagem(TEMPLATES[cand["template"]], cand["params"])

        print(f"\nEnviando para {cand['nome']}...")
        print("-" * 60)
        print(mensagem)
        print("-" * 60)

        # Abrir WhatsApp
        texto_codificado = urllib.parse.quote(mensagem)
        url = f"whatsapp://send?phone={cand['telefone']}&text={texto_codificado}"
        system = platform.system()
        if system == "Windows":
            os.startfile(url)
        elif system == "Darwin":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])

        # Atualizar data
        hoje_str = date.today().isoformat()
        nova_linha = cand["linha_original"].strip()
        partes = nova_linha.split("\t")
        partes[5] = hoje_str
        nova_linha = "\t".join(partes) + "\n"

        with open("config.txt", "w", encoding="utf-8") as f:
            for linha in linhas:
                if linha.strip() == cand["linha_original"].strip():
                    f.write(nova_linha)
                else:
                    f.write(linha)

        print(f"✅ Enviado e atualizado para {hoje_str}")
        input("\nPressione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSistema encerrado.")
