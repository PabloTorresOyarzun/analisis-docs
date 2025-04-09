import secrets
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Genera una clave secreta para tu aplicación
#SECRET_KEY = secrets.token_hex(32)  # 64 caracteres hexadecimales (32 bytes)

# Configuración de API keys (puedes usar token_hex o token_urlsafe)
#API_KEY = secrets.token_urlsafe(32)  # 43 caracteres URL-seguros (32 bytes)

# Configuración de la aplicación
class Config:
    # Claves generales
    #SECRET_KEY = SECRET_KEY
    #API_KEY = API_KEY

    # ----- AWS -----
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Valor por defecto opcional

    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

    # Configuración de Textract Asincrónico
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')  
    TEXTRACT_ROLE_ARN = os.getenv('TEXTRACT_ROLE_ARN')

    # Validación de credenciales AWS
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]):
        raise ValueError("Faltan credenciales de AWS en las variables de entorno")


    # ----- SGD BACKEND API -----
    BACKEND_URL = os.getenv('BACKEND_URL')
    AUTH_TOKEN = os.getenv('AUTH_TOKEN')  # Token de autorización para el backend

    # Validación de credenciales SGD BACKEND API
    if not all([BACKEND_URL, AUTH_TOKEN]):
        raise ValueError("Faltan credenciales de BACKEND en las variables de entorno")


    # ----- DATABASE -----
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'mysql' o 'sqlite'
    
    # Config MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'flask_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'flask_db')
    
    # Config SQLite
    SQLITE_PATH = os.getenv('SQLITE_PATH', '/app/database.db')  