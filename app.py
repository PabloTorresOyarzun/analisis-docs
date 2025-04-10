from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from services.sgd import despachos_bp
from services.aws import AWSService
from services.database import DatabaseManager
from io import BytesIO
from config import Config
import zipfile
import time
import json
import os
from werkzeug.utils import secure_filename

# Inicializar DatabaseManager después de crear la app
db_manager = DatabaseManager()

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para mensajes flash
app.jinja_env.globals.update(json=json)  # Permitir usar json en templates

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

        # Ruta base para SGD
        sgd_base = f"/app/output/sgd-results/{iddespacho}"
        os.makedirs(f"{sgd_base}/documents", exist_ok=True)
        os.makedirs(f"{sgd_base}/analysis", exist_ok=True)

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
                        temp_file = f"{sgd_base}/documents/{file_info.filename}"
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
                            output_file = f"{sgd_base}/analysis/{safe_filename}_analysis.json"
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
                            json_filename = f"{sgd_base}/analysis/{safe_filename}_async_analysis.json"
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

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No se subieron archivos'}), 400
    
    files = request.files.getlist('files')
    metodo = request.form.get('metodo')
    
    if not files or not metodo:
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    
    resultados = []
    aws_service = AWSService()
    
    # Crear carpeta con fecha y hora para Manual
    from datetime import datetime
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    manual_base = f"/app/output/manual-results/{current_time}"
    os.makedirs(f"{manual_base}/documents", exist_ok=True)
    os.makedirs(f"{manual_base}/analysis", exist_ok=True)

    for file in files:
        if file.filename == '':
            continue
            
        try:
            filename = file.filename
            file_content  = file.read()
            
            # Validar extensiones permitidas
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff'}
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                raise ValueError(f"Formato no soportado: {file_ext}. Formatos permitidos: PDF, JPG, PNG, TIFF")
            
            # Determinar content_type según extensión
            if file_ext == '.pdf':
                content_type = 'application/pdf'
            elif file_ext in ('.jpg', '.jpeg'):
                content_type = 'image/jpeg'
            elif file_ext == '.png':
                content_type = 'image/png'
            elif file_ext == '.tiff':
                content_type = 'image/tiff'
            else:  # Esto nunca debería ejecutarse por la validación anterior
                raise ValueError("Tipo de archivo no manejado")
            
            # Subir a S3
            safe_filename = filename.replace(" ", "_")
            if file_ext == '.pdf' and not safe_filename.lower().endswith('.pdf'):
                safe_filename += '.pdf'
            
            s3_path = f"manual/{safe_filename}"
            aws_service.upload_file_to_s3_v2(file_content, s3_path,content_type=content_type)
            
            # Determinar tipo de contenido
            content_type = 'application/pdf' if file_ext == '.pdf' else 'image/jpeg'
            
            # Guardar documento
            doc_path = f"{manual_base}/documents/{safe_filename}"
            with open(doc_path, 'wb') as f:
                f.write(file_content)

            # Procesar con Textract
            if metodo == 'sync':
                output_file = f"{manual_base}/analysis/{safe_filename}_analysis.json"
                aws_service.analyze_document_with_textract_sync(
                    s3_path, 
                    output_file,
                    content_type=content_type  # Nuevo parámetro
                )
                resultados.append(f"Análisis sincrónico completado: {output_file}")
            else:
                job_id = aws_service.analyze_document_with_textract_async(s3_path)
                
                # Esperar completar
                while True:
                    status = aws_service.textract_client.get_document_analysis(JobId=job_id)
                    if status['JobStatus'] in ['SUCCEEDED', 'FAILED']:
                        break
                    time.sleep(5)
                
                if status['JobStatus'] == 'FAILED':
                    resultados.append(f"Error en análisis de {safe_filename}")
                    continue
                
                analysis_result = aws_service.get_async_results(job_id)
                json_filename = f"{manual_base}/analysis/{safe_filename}_async_analysis.json"
                with open(json_filename, 'w') as f:
                    json.dump(analysis_result, f, indent=4)
                resultados.append(f"Análisis asincrónico completado: {json_filename}")
                
        except Exception as e:
            resultados.append(f"Error en {filename}: {str(e)}")
            continue
    
    return jsonify({'saved_files': resultados})

@app.route('/blocks')
def view_blocks():
    blocks = db_manager.get_all_blocks()
    return render_template('index.html', blocks=blocks)

@app.route('/upload-blocks', methods=['POST'])
def upload_blocks():
    if 'json_files' not in request.files:
        flash('No se seleccionaron archivos', 'danger')
        return redirect(url_for('view_blocks'))
    
    files = request.files.getlist('json_files')
    inserted_total = 0
    aws_service = AWSService()  # <-- Añade esta línea
    
    for file in files:
        if file.filename.endswith('.json'):
            try:
                data = json.load(file)
                # Procesar bloques y relaciones
                blocks, relationships = aws_service.process_textract_blocks(data)  # <-- Usa la instancia
                
                # Insertar bloques
                # Insertar bloques con manejo de duplicados
                for block in blocks.values():
                    db_manager.insert_line_block(
                        document_id=secure_filename(file.filename),
                        block_data=block
                    )
                
                # Insertar relaciones
                for rel in relationships:
                    try:
                        db_manager.insert_relationship(
                            rel['parent_id'],
                            rel['child_id'],
                            rel['type']
                        )
                    except Exception as e:
                        if 'Duplicate entry' not in str(e):
                            raise
                
                inserted_total += len(blocks)
            
            except Exception as e:
                flash(f'Error procesando {file.filename}: {str(e)}', 'warning')
    
    flash(f'Insertados {inserted_total} nuevos bloques', 'success')
    return redirect(url_for('view_blocks'))

@app.route('/clear-blocks', methods=['POST'])
def clear_blocks():
    deleted_count = db_manager.delete_all_blocks()
    flash(f'Se eliminaron {deleted_count} registros', 'info')
    return redirect(url_for('view_blocks'))

if __name__ == '__main__':
    app.run(debug=True)