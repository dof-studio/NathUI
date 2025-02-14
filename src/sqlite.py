# sqlite.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import os
import sqlite3
import logging
import queue
import threading
from typing import Any, Optional, List, Dict, Union, Iterator
from contextlib import contextmanager

# SQLite General Error
class SQLiteError(Exception):
    """
    Base exception class for SQLite operations
    """
    pass

# SQLite Connection Error
class ConnectionError(SQLiteError):
    """
    Exception raised for connection-related errors
    """
    pass

# SQLite Query Execution Error
class QueryExecutionError(SQLiteError):
    """
    Exception raised for query execution errors
    """
    pass

# SQLite Pool Error
class PoolError(SQLiteError):
    """
    Exception raised for connection pool errors
    """
    pass

# Logger Configuration
def setup_logger(name: str = 'sqlite_client', level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# Global logger initialization
logger = setup_logger()

# SQLite Connection Pool - Allowing multiple connections
class ConnectionPool:
    """
    Thread-safe SQLite connection pool implementation
    """
    
    def __init__(self, database: str, pool_size: int = 5, **kwargs: Any):
        """
        Initialize connection pool
        
        :param database: Database file path
        :param pool_size: Maximum number of connections in the pool
        :param kwargs: Additional SQLite connection parameters
        """
        self.database = database
        self.pool_size = pool_size
        self.kwargs = kwargs
        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        self._connections_created = 0
        self._lock = threading.Lock()
        
        for _ in range(pool_size):
            self._create_connection()

    def _create_connection(self) -> None:
        """
        Create a new connection and add it to the pool
        """
        try:
            conn = sqlite3.connect(self.database, **self.kwargs)
            conn.row_factory = sqlite3.Row
            self._pool.put(conn)
            with self._lock:
                self._connections_created += 1
        except sqlite3.Error as e:
            logger.error(f"Connection creation failed: {str(e)}")
            raise ConnectionError(f"Failed to create connection: {str(e)}") from e

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """
        Get a connection from the pool with timeout
        
        :param timeout: Maximum wait time in seconds
        :return: SQLite connection object
        """
        try:
            return self._pool.get(block=True, timeout=timeout)
        except queue.Empty as e:
            logger.error("Connection pool exhausted")
            raise PoolError("No available connections in the pool") from e

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool
        
        :param conn: Connection to return
        """
        if conn is not None:
            try:
                self._pool.put(conn, block=False)
            except queue.Full:
                logger.warning("Connection pool full, closing connection")
                conn.close()

    def close_all(self) -> None:
        """
        Close all connections in the pool
        """
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            conn.close()

# SQLite Client Instance - API
class SQLiteClient:
    """Main client class for SQLite database operations"""
    
    def __init__(self, database: str, pool_size: int = 5, **kwargs: Any):
        """
        Initialize SQLite client
        
        :param database: Database file path
        :param pool_size: Connection pool size
        :param kwargs: Additional connection parameters
        """
        # If database notexiting, create
        if os.path.exists(os.path.dirname(database)) == False:
            os.makedirs(os.path.dirname(database))
        
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        
        self.pool = ConnectionPool(
            database=database,
            pool_size=pool_size,
            check_same_thread=False,
            **kwargs
        )
        logger.info(f"Initialized SQLite client for database: {database}")

    @contextmanager
    def _get_cursor(self, conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
        """
        Context manager for cursor handling
        """
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager for connection handling
        """
        conn = self.pool.get_connection()
        try:
            yield conn
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Operation failed: {str(e)}")
            raise QueryExecutionError(str(e)) from e
        finally:
            self.pool.return_connection(conn)

    # Execute a SQL query but not SELECT query
    def execute(
        self,
        query: str,
        params: Optional[Union[tuple, Dict[str, Any]]] = None,
        commit: bool = False
    ) -> Optional[int]:
        """
        Execute a SQL query
        
        :param query: SQL query string
        :param params: Query parameters
        :param commit: Whether to commit transaction
        :return: Last row ID if applicable
        """
        with self.connection() as conn:
            try:
                with self._get_cursor(conn) as cursor:
                    cursor.execute(query, params or ())
                    if commit:
                        conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"Query failed: {query} - {str(e)}")
                conn.rollback()
                raise QueryExecutionError(str(e)) from e
                
    # Execute multiple SQL queries but not SELECT queries
    def executemany(
        self,
        query: str,
        params: List[Union[tuple, Dict[str, Any]]],
        commit: bool = False
    ) -> None:
        """
        Execute multiple SQL queries
        
        :param query: SQL query string
        :param params: List of query parameters
        :param commit: Whether to commit transaction
        """
        with self.connection() as conn:
            try:
                with self._get_cursor(conn) as cursor:
                    cursor.executemany(query, params)
                    if commit:
                        conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Bulk operation failed: {query} - {str(e)}")
                conn.rollback()
                raise QueryExecutionError(str(e)) from e
                
    # Execute a SELECT querys and return fetched data
    def fetch_all(
        self,
        query: str,
        params: Optional[Union[tuple, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all results from query
        
        :param query: SQL query string
        :param params: Query parameters
        :return: List of result rows as dictionaries
        """
        with self.connection() as conn:
            try:
                with self._get_cursor(conn) as cursor:
                    cursor.execute(query, params or ())
                    return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                logger.error(f"Fetch failed: {query} - {str(e)}")
                raise QueryExecutionError(str(e)) from e
                
    # Return a transaction manager for atomic operations
    def transaction(self) -> 'TransactionManager':
        """
        Return a transaction manager for atomic operations
        """
        return TransactionManager(self)

# SQLite Internal Value Translator
class TransactionManager:
    """
    Context manager for handling database transactions
    """
    
    def __init__(self, client: SQLiteClient):
        self.client = client
        self.conn: Optional[sqlite3.Connection] = None
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"

    def __enter__(self) -> 'TransactionManager':
        self.conn = self.client.pool.get_connection()
        self.conn.execute('BEGIN')
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.conn:
            try:
                if exc_type:
                    self.conn.rollback()
                else:
                    self.conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Transaction failed: {str(e)}")
                raise QueryExecutionError(str(e)) from e
            finally:
                self.client.pool.return_connection(self.conn)

    def execute(self, query: str, params: Optional[Union[tuple, Dict[str, Any]]] = None) -> sqlite3.Cursor:
        """
        Execute within transaction context
        Translate ?, ?, ... into specified param values
        """
        if not self.conn:
            raise ConnectionError("Not in transaction context")
        
        try:
            with self.client._get_cursor(self.conn) as cursor:
                cursor.execute(query, params or ())
                return cursor
        except sqlite3.Error as e:
            logger.error(f"Transactional query failed: {query} - {str(e)}")
            raise QueryExecutionError(str(e)) from e

# Usage Example
if __name__ == '__main__':
    # Initialize client
    db_client = SQLiteClient('./__database__/test_example.db', pool_size=5)
    
    # Create table
    db_client.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)",
        commit=True
    )
    
    # Insert record
    user_id = db_client.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        ('Alice', 'alice@example.com'),
        commit=True
    )
    
    # Query records
    users = db_client.fetch_all("SELECT * FROM users")
    print(users)
    
    # Transaction example
    with db_client.transaction() as tx:
        tx.execute("UPDATE users SET email = ? WHERE id = ?", ('alice_new@example.com', user_id))
        tx.execute("INSERT INTO users (name, email) VALUES (?, ?)", ('Bob', 'bob@example.com'))
