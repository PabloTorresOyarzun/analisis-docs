from urllib.parse import urljoin
from flask import Blueprint, jsonify, send_file, Response
from werkzeug.utils import secure_filename
from config import Config
from io import BytesIO
import zipfile
import requests
import base64

despachos_bp = Blueprint('despachos', __name__)

@despachos_bp.route('/despachos/<int:iddespacho>', methods=['GET'])
def obtener_despacho(iddespacho):
    # Construir la URL correctamente
    url = urljoin(Config.BACKEND_URL, str(iddespacho))
    token = Config.AUTH_TOKEN  # Se obtiene el token desde la configuración

    if not token:
        return jsonify({"error": "Token de autorización no configurado"}), 500

    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Lanza una excepción si la respuesta tiene un código de error HTTP

        # Suponiendo que los documentos están en una lista bajo la clave 'data' del JSON
        data = response.json()
        documentos = data.get('data')

        if not documentos or not isinstance(documentos, list):
            return jsonify({"error": "No se encontraron documentos en la respuesta"}), 400

        # Crear un archivo ZIP en memoria
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            errores = []
            # Validar y procesar cada documento
            for idx, documento in enumerate(documentos):
                try:
                    # Extraer el contenido base64 del campo 'documento'
                    documento_base64 = documento.get('documento')
                    if not documento_base64 or not documento_base64.startswith("data:application/pdf;base64,"):
                        return jsonify({"error": f"Formato inválido en el documento {idx + 1}"}), 400

                    # Remover el prefijo "data:application/pdf;base64," y decodificar
                    base64_content = documento_base64.split(",", 1)[1]
                    pdf_content = base64.b64decode(base64_content)

                    # Obtener el nombre del documento o generar uno por defecto
                    nombre_documento = secure_filename(documento.get('nombre_documento', f"despacho_{iddespacho}_{idx + 1}.pdf"))

                    # Agregar el archivo PDF al ZIP
                    zip_file.writestr(nombre_documento, pdf_content)
                except Exception as e:
                    errores.append(f"Documento {idx}: {str(e)}")

            if errores:
                return jsonify({"error": "Errores al procesar algunos documentos", "details": errores}), 400

        zip_buffer.seek(0)

        # Enviar el archivo ZIP como respuesta
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f"despachos_{iddespacho}.zip")

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Error al obtener el despacho", "details": str(e)}), 500
