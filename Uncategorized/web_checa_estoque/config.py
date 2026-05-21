# ================== CONFIGURAÇÃO DO FIREBIRD ==================

DB_CONFIG = {
    'dsn': '<IP>/<port>:C:/<path>',  # ou o DSN que você usa
    'user': '<user>',
    'password': '<password>',  # <<< MUDE ISSO
    'charset': 'UTF8'
}

# Opcional: você pode adicionar mais configurações aqui no futuro
APP_CONFIG = {
    'host': '0.0.0.0',
    'port': <port>,
    'debug': True
}
