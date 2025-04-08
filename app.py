from flask import Flask, render_template, request, redirect, url_for, flash
from services.backend import despachos_bp
from services.aws import AWSService
from io import BytesIO
from config import Config
import zipfile
import time
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para mensajes flash
app.register_blueprint(despachos_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    iddespacho = request.form.get('iddespacho')
    metodo = request.form.get('metodo')
    
    if not iddespacho or not metodo:
        flash('Faltan campos requeridos', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Obtener el ZIP usando el test client
        with app.test_client() as client:
            response = client.get(f'/despachos/{iddespacho}')
            
        if response.status_code != 200:
            flash(f'Error al obtener despacho: {response.json.get("error")}', 'danger')
            return redirect(url_for('index'))
        
        # Procesar el ZIP
        zip_buffer = BytesIO(response.data)
        resultados = []
        aws_service = AWSService()
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            for file_info in zip_file.infolist():
                # Verificar extensión y contenido del PDF
                if file_info.filename.lower().endswith('.pdf'):
                    try:
                        pdf_content = zip_file.read(file_info)
                        # Verificar firma del PDF (primeros bytes)
                        if not pdf_content.startswith(b'%PDF-'):
                            raise ValueError("El archivo no es un PDF válido")
                        temp_file = f"/app/output/pdf/{file_info.filename}"
                        with open(temp_file, 'wb') as f:
                             f.write(pdf_content)
                        
                        # Forzar extensión .pdf en el nombre del archivo
                        safe_filename = file_info.filename.replace(" ", "_")
                        if not safe_filename.lower().endswith('.pdf'):
                            safe_filename += '.pdf'

                        # Subir a S3 con nombre seguro
                        s3_path = f"despachos/{iddespacho}/{safe_filename}"
                        aws_service.upload_file_to_s3_v2(pdf_content, s3_path)  # Función modificada (ver aws.py)

                        # Ejecutar Textract
                        if metodo == 'sync':
                            output_file = f"/app/output/json/{file_info.filename}_analysis.json"
                            aws_service.analyze_document_with_textract_sync(
                                f"despachos/{iddespacho}/{file_info.filename}",
                                output_file
                            )
                            resultados.append(f"Análisis sincrónico completado: {output_file}")
                        # En el bloque donde se procesa el método async:
                        else:
                            job_id = aws_service.analyze_document_with_textract_async(
                                f"despachos/{iddespacho}/{safe_filename}"
                            )
                            
                            # Esperar hasta que el análisis esté completo
                            while True:
                                status = aws_service.textract_client.get_document_analysis(JobId=job_id)
                                if status['JobStatus'] in ['SUCCEEDED', 'FAILED']:
                                    break
                                time.sleep(5)
                            
                            if status['JobStatus'] == 'FAILED':
                                resultados.append(f"Error en análisis de {safe_filename}")
                                continue
                            
                            # Obtener resultados completos
                            analysis_result = aws_service.get_async_results(job_id)
                            
                            # Guardar JSON
                            json_filename = f"/app/output/json/{safe_filename}_async_analysis.json"
                            with open(json_filename, 'w') as f:
                                json.dump(analysis_result, f, indent=4)
                            
                            resultados.append(f"Análisis async completado: {json_filename}")
                            
                    except Exception as e:
                        resultados.append(f"Error en {file_info.filename}: {str(e)}")
                        continue
    
        flash('Proceso completado exitosamente', 'success')
        return render_template('index.html', resultados=resultados)
    
    except Exception as e:
        flash(f'Error en el proceso: {str(e)}', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)