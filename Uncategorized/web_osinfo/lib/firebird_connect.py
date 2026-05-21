import fdb

def firebird_connect():
    host_ip = '<IP>'
    porta = <port>
    caminho_banco = 'C:/<path>'
    usuario  = '<user>'
    senha = '<password>'
    charset = 'UTF8'

    dsn = f'{host_ip}/{porta}:{caminho_banco}'

    try:
        con = fdb.connect(dsn=dsn, user=usuario, password=senha, charset=charset)
        #print("Conexão estabelecida com sucesso!")

        return con
    except Exception as e:
        print(f"Erro na conexão: {e}")

def load_query(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        return f.read().strip()
