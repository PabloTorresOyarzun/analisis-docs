from config import Config
from contextlib import contextmanager
import mysql.connector
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_type = Config.DB_TYPE
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        if self.db_type == 'mysql':
            conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB
            )
        else:  # SQLite
            conn = sqlite3.connect(Config.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == 'mysql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS line_blocks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        document_id VARCHAR(100),
                        page INT,
                        block_id VARCHAR(100),
                        text TEXT,
                        confidence FLOAT,
                        top FLOAT,
                        left_pos FLOAT,
                        width FLOAT,
                        height FLOAT
                    )
                """)
            else:  # SQLite
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS line_blocks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT,
                        page INTEGER,
                        block_id TEXT,
                        text TEXT,
                        confidence REAL,
                        top REAL,
                        left_pos REAL,
                        width REAL,
                        height REAL
                    )
                """)
            conn.commit()
    
    def insert_line_block(self, document_id, page, block_data):
        """
        Inserta un bloque de texto en la base de datos
        block_data debe contener: id, text, confidence, geometry (con posiciones)
        """
        query = """
            INSERT INTO line_blocks (
                document_id, page, block_id, text, confidence, 
                top, left_pos, width, height
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """ if self.db_type == 'mysql' else """
            INSERT INTO line_blocks (
                document_id, page, block_id, text, confidence, 
                top, left_pos, width, height
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            document_id,
            page,
            block_data['id'],
            block_data['text'],
            block_data['confidence'],
            block_data['top'],
            block_data['left'],
            block_data['width'],
            block_data['height']
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def insert_from_json(self, json_data, page=1):
        """Inserta bloques de texto desde un JSON de Textract"""
        blocks = json_data.get('Blocks', [])
        inserted_ids = []
        
        for block in blocks:
            if block['BlockType'] == 'LINE':
                geometry = block['Geometry']['BoundingBox']
                block_data = {
                    'id': block['Id'],
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'top': geometry['Top'],
                    'left': geometry['Left'],
                    'width': geometry['Width'],
                    'height': geometry['Height']
                }
                inserted_ids.append(
                    self.insert_line_block(
                        document_id="",  # En blanco como solicitaste
                        page=page,
                        block_data=block_data
                    )
                )
        return inserted_ids

    def get_all_blocks(self):
        """Obtiene todos los bloques de texto"""
        query = "SELECT * FROM line_blocks"
        
        with self._get_connection() as conn:
            # Crear cursor adecuado para cada tipo de base de datos
            if self.db_type == 'mysql':
                cursor = conn.cursor(dictionary=True)  # Para MySQL
            else:
                cursor = conn.cursor()  # Para SQLite (ya tiene row_factory configurado)
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Convertir resultados a diccionario para SQLite
            if self.db_type != 'mysql' and results:
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in results]
            
            cursor.close()
            return results
    
    def delete_all_blocks(self):
        """Elimina todos los registros de la tabla"""
        query = "DELETE FROM line_blocks"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            return cursor.rowcount