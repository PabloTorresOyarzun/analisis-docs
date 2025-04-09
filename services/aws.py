from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from config import Config
import boto3
import json

class AWSService:
    def __init__(self):
        # Configuración de credenciales de AWS
        try:
            # Usar valores de Config directamente
            self.aws_access_key_id = Config.AWS_ACCESS_KEY_ID
            self.aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY
            self.region_name = Config.AWS_REGION
            self.bucket_name = Config.S3_BUCKET_NAME  # Obtener bucket_name de Config

            # Configurar clientes de AWS
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            self.textract_client = boto3.client(
                'textract',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Error de credenciales: {e}")
            raise
        except Exception as e:
            print(f"Error inesperado: {e}")
            raise

    # En la clase AWSService, modificar los métodos de subida:
    def upload_file_to_s3_v2(self, file_content, object_name, content_type='application/pdf'):
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_content,
                ContentType=content_type  # <-- Usar el parámetro
            )
            return f"s3://{self.bucket_name}/{object_name}"
        except Exception as e:
            print(f"Error subiendo archivo: {e}")
            raise

    def analyze_document_with_textract_sync(self, document_name, output_file, content_type='application/pdf'):
        """Analyzes documents and images"""
        try:
            # Configuración común
            doc_config = {
                'FeatureTypes': ['TABLES', 'FORMS']
            }

            # Manejar diferente entre PDF e imágenes
            if content_type == 'application/pdf':
                doc_config['Document'] = {
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': document_name
                    }
                }
            else:
                # Obtener bytes de la imagen desde S3
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=document_name
                )
                doc_config['Document'] = {
                    'Bytes': response['Body'].read()
                }

            response = self.textract_client.analyze_document(**doc_config)
            
            with open(output_file, 'w') as f:
                json.dump(response, f, indent=4)
            return response
    
        except Exception as e:
            print(f"Error analyzing document (sync): {e}")
            raise

    def analyze_document_with_textract_async(self, document_name):
        """Inicia análisis asincrónico y devuelve JobId"""
        try:
            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': document_name
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']
            )
            return response['JobId']
        except Exception as e:
            print(f"Error iniciando análisis async: {e}")
            raise

    def get_async_results(self, job_id):
        """Obtiene resultados paginados del análisis"""
        try:
            blocks = []
            next_token = None
            
            while True:
                kwargs = {'JobId': job_id}
                if next_token:
                    kwargs['NextToken'] = next_token
                    
                response = self.textract_client.get_document_analysis(**kwargs)
                blocks.extend(response.get('Blocks', []))
                next_token = response.get('NextToken', None)
                
                if not next_token:
                    break
            
            return {'Blocks': blocks}
        except Exception as e:
            print(f"Error obteniendo resultados: {e}")
            raise