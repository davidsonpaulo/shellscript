#!/usr/bin/python3
from flask import Flask, render_template, request, jsonify
import fdb
import os

# Importa configuração externa
from config import DB_CONFIG, APP_CONFIG

app = Flask(__name__)

def firebird_connect():
    return fdb.connect(**DB_CONFIG)

QUERY = """
SELECT 
    pdg.codigo AS codigo_interno,
    pdg.descricao,
    COALESCE(principal.estdisponivel / pdg.qtdeembalagem, 0) AS disponivel
FROM testprodutogeral pdg
LEFT JOIN testproduto principal ON pdg.produtoprincipal = principal.produto
WHERE pdg.codigofabrica = ?
  AND pdg.produtoprincipal = pdg.codigo
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verificar', methods=['POST'])
def verificar():
    data = request.get_json()
    items = data.get('items', [])
    results = []

    try:
        con = firebird_connect()
        cur = con.cursor()

        for item in items:
            codfab = item['codfab'].strip().upper()
            cur.execute(QUERY, (codfab,))
            row = cur.fetchone()

            if row:
                codigo, descricao, disponivel = row
                results.append({
                    'codfab': codfab,
                    'cadastrado': True,
                    'codigo': codigo,
                    'descricao': descricao,
                    'disponivel': float(disponivel) if disponivel is not None else 0,
                    'quantidade': item['quantidade'],
                    'posicao': item.get('posicao', '')
                })
            else:
                results.append({
                    'codfab': codfab,
                    'cadastrado': False,
                    'descricao': None,
                    'codigo': None,
                    'disponivel': 0,
                    'quantidade': item['quantidade'],
                    'posicao': item.get('posicao', '')
                })

        cur.close()
        con.close()

    except Exception as e:
        print("Erro Firebird:", e)
        return jsonify({'error': str(e)}), 500

    return jsonify({'results': results})

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    host = APP_CONFIG['host']
    port = APP_CONFIG['port']
    
    print("=== Checa Estoque - Celsom Ferramentas ===")
    print(f"Servidor iniciado em http://{host}:{port}")
    print("Acesse de outros computadores usando o IP local")
    print("=============================================")
    
    app.run(
        host=host, 
        port=port, 
        debug=APP_CONFIG['debug']
    )
