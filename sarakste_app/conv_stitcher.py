import environ

env = environ.Env()
environ.Env.read_env(overwrite=True)
# Get the IP address of this host
DEBUG = env.bool('debug', default=False)
import socket
hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)
HOSTED = env.bool('HOSTED', default=False)
print('HOSTED:',HOSTED)
if HOSTED:
    # .envfilestatesthisenvironmentishosted,sousetheretrievedIPaddress.
    host_ip = IP
    db_name = env.str('MYSQL_PROD_DB_NAME')
    db_user = env.str('MYSQL_PROD_DB_USER')
    db_pwd = env.str('MYSQL_PROD_PWD')
else:
    host_ip = '127.0.0.1'
    db_name = env.str('MYSQL_LOCAL_DB_NAME')
    db_user = env.str('MYSQL_LOCAL_DB_USER')
    db_pwd = env.str('MYSQL_LOCAL_PWD')

