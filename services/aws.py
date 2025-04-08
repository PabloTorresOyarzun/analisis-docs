import boto3
import json
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from config import Config

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
    def upload_file_to_s3_v2(self, file_content, object_name):
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_content,
                ContentType='application/pdf'
            )
            print(f"PDF subido a s3://{self.bucket_name}/{object_name}")
            return f"s3://{self.bucket_name}/{object_name}"
        except Exception as e:
            print(f"Error subiendo archivo: {e}")
            raise

    def analyze_document_with_textract_sync(self, document_name, output_file):
        """Analyzes a document stored in S3 using Textract (synchronous) and saves the result as JSON."""
        try:
            response = self.textract_client.analyze_document(
                Document={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': document_name
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']
            )
            with open(output_file, 'w') as f:
                json.dump(response, f, indent=4)
            print(f"Textract sync analysis saved to {output_file}")
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