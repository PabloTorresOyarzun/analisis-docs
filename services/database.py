from config import Config
from contextlib import contextmanager
import mysql.connector
import sqlite3
import logging
import json

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
            
            # Modificar la creación de la tabla blocks
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS blocks (
                    id VARCHAR(100) {'PRIMARY KEY' if self.db_type == 'mysql' else ''},
                    document_id VARCHAR(100),
                    block_type VARCHAR(50),
                    text TEXT,
                    confidence FLOAT,
                    page INT,
                    geometry {'JSON' if self.db_type == 'mysql' else 'TEXT'}
                    {', PRIMARY KEY (id)' if self.db_type == 'mysql' else ''})
                """)
            
            # Tabla block_relationships
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS block_relationships (
                    parent_id VARCHAR(100),
                    child_id VARCHAR(100),
                    type VARCHAR(20),
                    PRIMARY KEY (parent_id, child_id))
                """)
            
            conn.commit()

    def insert_line_block(self, document_id, block_data):
        """Inserta un bloque con su geometría"""
        query = """
            INSERT INTO blocks (
                id, document_id, block_type, text, 
                confidence, page, geometry
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """ if self.db_type == 'mysql' else """
            INSERT INTO blocks (
                id, document_id, block_type, text, 
                confidence, page, geometry
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            block_data['id'],
            document_id,
            block_data['block_type'],
            block_data.get('text', ''),
            block_data.get('confidence', 0),
            block_data.get('page', 1),
            block_data['geometry']  # <-- Quitar json.dumps, ya está serializado
        )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def insert_relationship(self, parent_id, child_id, rel_type):
        """Inserta una relación entre bloques"""
        query = """
            INSERT INTO block_relationships 
            (parent_id, child_id, type)
            VALUES (%s, %s, %s)
        """ if self.db_type == 'mysql' else """
            INSERT INTO block_relationships 
            (parent_id, child_id, type)
            VALUES (?, ?, ?)
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (parent_id, child_id, rel_type))
            conn.commit()

    def get_all_blocks(self):
        query = """
            SELECT 
                b.id,
                b.document_id,
                b.block_type,
                b.text,
                b.confidence,
                b.page,
                b.geometry,
                GROUP_CONCAT(
                    CASE 
                        WHEN br.type IS NOT NULL THEN br.type || '->' || br.child_id 
                        ELSE NULL 
                    END
                ) as relationships
            FROM blocks b
            LEFT JOIN block_relationships br ON b.id = br.parent_id
            GROUP BY b.id
        """ if self.db_type == 'sqlite' else """
            SELECT 
                b.id,
                b.document_id,
                b.block_type,
                b.text,
                b.confidence,
                b.page,
                b.geometry,
                GROUP_CONCAT(CONCAT(br.type, '->', br.child_id)) as relationships
            FROM blocks b
            LEFT JOIN block_relationships br ON b.id = br.parent_id
            GROUP BY b.id
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Convertir a diccionario
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        
    def delete_all_blocks(self):
        """Elimina todos los registros de la tabla blocks"""
        query = "DELETE FROM blocks"  # Cambiar de line_blocks a blocks
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            return cursor.rowcount