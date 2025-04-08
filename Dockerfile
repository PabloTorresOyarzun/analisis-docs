# Usa una imagen base de Python
FROM python:3.10.2-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos necesarios
COPY requirements.txt .
COPY app.py .
COPY config.py .
COPY .env .
COPY templates/ ./templates/
COPY services/ ./services/
COPY output/ ./output/

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Variables de entorno para AWS (opcional, usar secrets en producción)
#ENV AWS_ACCESS_KEY_ID=""
#ENV AWS_SECRET_ACCESS_KEY=""
#ENV AWS_DEFAULT_REGION="us-east-1"

# Expone el puerto de Flask
EXPOSE 5000

# Comando para ejecutar la app
CMD ["flask", "--app", "app", "--debug", "run", "--host=0.0.0.0"]