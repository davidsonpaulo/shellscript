from flask import Flask, render_template, request
from lib.firebird_connect import firebird_connect, load_query
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def osinfo():
    os_num = request.args.get('os', '').strip()
    
    if not os_num:
        return render_template('index.html')
    
    # Consulta no banco
    try:
        con = firebird_connect()
        cur = con.cursor()
        query = load_query('queries/obter_dados_da_os_para_notificacao.sql')
        
        cur.execute(query, (os_num,))
        dados = cur.fetchall()
        
        if not dados or not dados[0]:
            return render_template('index.html', 
                                 error=f"Nenhum registro encontrado para a OS {os_num}")
        
        row = dados[0]
        cols = [desc[0] for desc in cur.description]
        dados_dict = dict(zip(cols, row))

        # Processamento
        os_numero = int(dados_dict.get('CODIGO', 0))
        
        nome = dados_dict.get('NOME', '')
        fantasia = dados_dict.get('FANTASIA', '')
        cliente = nome if nome == fantasia else f"{nome} ({fantasia})" if fantasia else nome

        objeto_codigo = dados_dict.get('OBJETO_CODIGO')
        
        if objeto_codigo == 1:
            equipamento = f"({objeto_codigo}) {dados_dict.get('DESCRICAO_OBJETO', '')}"
        else:
            equipamento = f"({objeto_codigo}) {dados_dict.get('OBJETO_DESCRICAO', '')} " \
                         f"{dados_dict.get('OBJETO_MARCA', '')} {dados_dict.get('OBJETO_MODELO', '')}".strip()

        resultado = {
            'os': os_numero,
            'telefone': f"55{dados_dict.get('FONE', '')}",
            'cliente': cliente,
            'cliente_obs': dados_dict.get('CLIENTE_OBS', ''),
            'equipamento': equipamento,
            'numero_serie': dados_dict.get('OBJETO_SERIE', ''),
            'preco_bruto': dados_dict.get('PRECO_BRUTO'),
            'preco': dados_dict.get('PRECO'),
            'objeto_obs': dados_dict.get('OBJETO_OBS', ''),           # ← Campo correto
            'abertura': dados_dict.get('ABERTURA'),
            'fechamento': dados_dict.get('FECHAMENTO'),
            'situacao': dados_dict.get('SITUACAO')
        }

        return render_template('index.html', resultado=resultado)

    except Exception as e:
        return render_template('index.html', error=str(e)[:400])
    finally:
        if 'cur' in locals(): cur.close()
        if 'con' in locals(): con.close()


if __name__ == '__main__':
    print("=== Consulta OS - Celsom Ferramentas ===")
    print("Acesse: http://localhost:5003")
    print("Exemplo: http://localhost:5003/?os=33566")
    app.run(host='0.0.0.0', port=5003, debug=True)
