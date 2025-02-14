# sqlparse.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################

import re
import logging
import pandas as pd
from typing import List, Dict, Union, Optional, Any
from sqlite import SQLiteClient, QueryExecutionError

# Global sqlite logger
logger = logging.getLogger('sqlite_parser')

class SQLiteParser:
    """
    DSL parser for SQLite operations with safe query generation
    """
    
    # Scalar type Mapping
    TYPE_MAPPING = {
        str:   "TEXT",
        int:   "INTEGER",
        float: "REAL",
        bytes: "BLOB",
        bool:  "INTEGER",  # SQLite doesn't have native BOOLEAN
        None:  "NULL"
    }
    
    # Constructor
    def __init__(self, client: SQLiteClient, default_table: str):
        """
        Initialize parser with connected client and default table
        
        :param client: Initialized SQLiteClient instance
        :param default_table: Default table name for operations
        """
        # Version
        self.version = 1
        
        # NathMath@bili+bili ~ DOF-S?tudio!
        self.client = client
        self.default_table = default_table
        self.table_schemas: Dict[str, dict] = {}
        
        # Initialize schema cache
        self._refresh_schema_cache()
        
        # Tags? Haha
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        
        # It is a FREE and OPEN SOURCED software
        # See github.com/dof-studio/NathUI

    # Cache table schema information from database
    def _refresh_schema_cache(self) -> None:
        """
        Cache table schema information from database
        """
        tables = self.client.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        for table in tables:
            table_name = table['name']
            schema = self.client.fetch_all(
                f"PRAGMA table_info({table_name})"
            )
            # NathMath@bilibili and DOF-Studio
            self.table_schemas[table_name] = {
                'columns': {col['name']: col for col in schema},
                'primary_key': [col['name'] for col in schema if col['pk']]
            }

    # Get primary key columns for a table
    def _get_primary_key(self, table_name: str) -> List[str]:
        """
        Get primary key columns for a table
        """
        if table_name not in self.table_schemas:
            self._refresh_schema_cache()
        return self.table_schemas[table_name]['primary_key']
    
    # Validate column names against table schema.
    def _validate_columns(self, table: str, columns: List[str]) -> None:
        """
        Validate column names against table schema.
        
        :param table: Target table name
        :param columns: List of columns to validate
        :raises ValueError: For invalid columns
        """
        valid_columns = self.table_schemas[table]['columns']
        for col in columns:
            if col not in valid_columns:
                raise ValueError(f"Invalid column '{col}' in table '{table}'")
    
    # Create table with schema definition (specified)
    def create_table(self, table_name: str, columns: List[Dict[str, Any]], safemode: bool = True) -> None:
        """
        Create table with schema definition
        
        :param table_name: Name of the table to create
        :param columns: List of column definitions
        """
        table_name = table_name.strip()
        column_defs = []
        primary_keys = []
        
        for col in columns:
            col_name = col['name']
            col_type = self.TYPE_MAPPING.get(col['type'], 'TEXT')
            constraints = []
            
            if col.get('primary', False):
                constraints.append('PRIMARY KEY')
                primary_keys.append(col_name)
                
            if col.get('unique', False):
                constraints.append('UNIQUE')
                
            if col.get('not_null', False):
                constraints.append('NOT NULL')
                
            column_def = f"{col_name} {col_type} {' '.join(constraints)}"
            column_defs.append(column_def)
            
            # It is a FREE and OPEN SOURCED software
            # See github.com/dof-studio/NathUI
        
        # Handle composite primary keys
        if primary_keys and len(primary_keys) > 1:
            column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        # Create sql
        if safemode:
            create_sql = (
                f"CREATE TABLE IF NOT EXISTS {table_name} (\n" +
                ',\n'.join(column_defs) +
                "\n)"
            )
        else:
            create_sql = (
                f"CREATE TABLE {table_name} (\n" +
                ',\n'.join(column_defs) +
                "\n)"
            )
            # In this circumstance it may raise an error
        
        self.client.execute(create_sql, commit=True)
        self._refresh_schema_cache()
        logger.info(f"Created table {table_name} with schema: {columns}")
        
    # Insert data into specified table
    def insert(self, data: Union[List, Dict, List[Union[List, Dict]]], 
               table_name: Optional[str] = None) -> List[Optional[int]]:
        """
        Insert data into specified table
        
        :param data: Data to insert (single record or batch)
        :param table_name: Target table name (defaults to configured table)
        :return: List of inserted row IDs
        """
        table = table_name or self.default_table
        table = table.strip()
        schema = self.table_schemas[table]['columns']
        col_names = list(schema.keys())
        
        # Normalize input format
        if isinstance(data, dict):
            data = [data]
        elif isinstance(data, list) and len(data) > 0:
            data = data
        else:
            raise ValueError("Data must be a dictionary or a list of dictionaries.")
             
        # Validate and convert data
        validated_data = []
        for item in data:
            # For a dict
            if isinstance(item, dict):
                ordered_values = []
                for col in col_names:
                    if col not in item:
                        raise ValueError(f"Missing value for column {col}")
                    ordered_values.append(self._convert_value(item[col], schema[col]['type']))
                validated_data.append(ordered_values)
            # For a list
            elif isinstance(item, list):
                if len(item) != len(col_names):
                    raise ValueError(f"Expected {len(col_names)} values, got {len(item)}")
                validated_data.append([self._convert_value(v, schema[col]['type']) 
                                      for v, col in zip(item, col_names)])
        
        # Generate parameter placeholders
        placeholders = ', '.join(['?'] * len(col_names))
        sql = f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({placeholders})"
        
        # Execute batch insert
        try:
            with self.client.transaction() as tx:
                row_ids = []
                for values in validated_data:
                    try:
                        # Get cursor and return inserted row_ids
                        cursor = tx.execute(sql, values)
                        row_ids.append(cursor.rowcount)
                    except QueryExecutionError as e:
                        # Only log but not raise
                        logger.error(f"Insert failed: {str(e)}")
                return row_ids
        except Exception as e:
            logger.error(f"Insert failed: {str(e)}")
            raise

    # Update data into specified table
    def update(self, data: Union[Dict, List[Dict]], table_name: Optional[str] = None, coerce: bool = True) -> List[int]:
        """
        Update existing record(s) in the specified table.
        
        Each record must be a dictionary containing at least the primary key field(s) to identify the row.
        Only non-primary key fields present in the record will be updated.
        
        :param data: Data to update (a dict or a list of dicts).
        :param table_name: Target table name (defaults to the configured table).
        :param coerce: If it not exists, then insert if coerce is True.
        :return: List of affected row counts.
        :raises ValueError: If primary key fields are missing or no columns to update are provided.
        """
        table = (table_name or self.default_table).strip()
        schema = self.table_schemas[table]['columns']
        primary_keys = self._get_primary_key(table)
        
        if coerce == True:
            # Get the existing pk values
            pkvalues = self.client.fetch_all(f"SELECT {', '.join(primary_keys)} FROM {table}")
            pkvalues = pd.DataFrame(pkvalues)
        
        if not primary_keys:
            raise ValueError(f"Table '{table}' does not have a primary key defined, cannot perform update.")
    
        # Normalize input to a list of dictionaries
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list) and len(data) > 0:
            records = data
        else:
            raise ValueError("Data must be a dictionary or a list of dictionaries.")
        
        affected_rows = []
        
        with self.client.transaction() as tx:
            for record in records:
                # Validate that all provided columns exist in table schema
                self._validate_columns(table, list(record.keys()))
                
                # Ensure the record contains the primary key fields
                for pk in primary_keys:
                    if pk not in record:
                        raise ValueError(f"Missing primary key field '{pk}' in update data.")
                
                # Prepare SET clause: only update non-primary key columns
                set_clauses = []
                set_values = []
                for col, val in record.items():
                    if col in primary_keys:
                        continue
                    set_clauses.append(f"{col} = ?")
                    set_values.append(self._convert_value(val, schema[col]['type']))
                
                if not set_clauses:
                    raise ValueError("No columns to update provided (only primary key fields found).")
                
                # Prepare WHERE clause using primary key fields
                where_clauses = []
                where_values = []
                for pk in primary_keys:
                    where_clauses.append(f"{pk} = ?")
                    where_values.append(self._convert_value(record[pk], schema[pk]['type']))
                
                sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
                
                try:
                    # In the table
                    count = 0
                    for pk in primary_keys:
                        if record[pk] in pkvalues[pk]:
                            count += 1
                    if count == len(primary_keys):
                        cursor = tx.execute(sql, set_values + where_values)
                        affected_rows.append(cursor.rowcount)  
                    
                    # Not in the table, insert
                    else:
                        ret = self.insert([record], table)[0]
                        affected_rows.append(ret)
                    
                except Exception as e:
                    logger.error(f"Update failed for record {record}: {str(e)}")
                    
                    # If coerce, use insert to insert it again
                    if coerce == True:
                        ret = 0
                        try:
                            ret = self.insert([record], table)[0]
                            affected_rows.append(ret)
                        except Exception as e:
                            logger.error(f"Coerced update failed for record {record}: {str(e)}")
                            raise
                    else:
                        raise
        
        return affected_rows

    # Value conversion (for SQLite Types)
    def _convert_value(self, value: Any, col_type: str) -> Any:
        """Convert value to appropriate SQLite type"""
        if value is None:
            return None
            
        type_map = {
            'INTEGER': int,
            'REAL': float,
            'TEXT': str,
            'BLOB': bytes
        }
        
        try:
            # strip process
            converted = type_map[col_type](value)
            if isinstance(converted, str):
                return converted.strip()
            else:
                return converted
            return 
        except (ValueError, TypeError):
            logger.warning(f"Type conversion failed for {value} to {col_type}")
            return value

    # (Deprecated) Execute DSL query (\select ... \select syntax) and return results
    def _select_legacy(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute DSL query and return results
        
        :param query: DSL query string
        :return: List of result rows as dictionaries
        By NathMath@bilibili/DOF Studio
        """
        # Parse query structure
        query = query.strip()
        table_match = re.search(r'\\from\s+(\w+)\\select', query)
        table_name = table_match.group(1) if table_match else self.default_table
        
        # Extract query conditions
        conditions_part = re.search(
            r'\\select(.*?)(\\from|\\select)', 
            query, 
            re.DOTALL
        ).group(1).strip()
        
        # Split into individual conditions
        condition_groups = [cg.strip() for cg in conditions_part.split(',')]
        
        results = []
        primary_key = self._get_primary_key(table_name)
        if len(primary_key) != 1:
            raise ValueError("DSL queries currently support single-column primary keys only")
        
        pk_column = primary_key[0]
        
        for group in condition_groups:
            # Split into candidate values
            candidates = [c.strip() for c in group.split('|')]
            
            for candidate in candidates:
                # Convert value to proper type
                col_type = self.table_schemas[table_name]['columns'][pk_column]['type']
                converted_val = self._convert_value(candidate, col_type)
                
                # Execute lookup
                result = self.client.fetch_all(
                    f"SELECT * FROM {table_name} WHERE {pk_column} = ?",
                    (converted_val,)
                )
                
                if result:
                    results.extend(result)
                    break  # Short-circuit on first match
                    
        return results

    # Execute DSL query (\select ... \select syntax) and return results
    def select(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute enhanced DSL query with fuzzy matching and column selection.
        
        Syntax:
                 Must        Optional            Optional
                             
        \\select CONDITIONS [\\columns COLUMNS] [\\from TABLE] \\select
        
        Example:
        \\select id123, name? \\columns id, name \\from users \\select
        
        :param query: DSL query string
        :return: Query results as dictionaries
        """
        # Parse query components with ordered clause handling
        components = {
            'conditions': '',
            'columns': None,
            'table': self.default_table
        }
        
        # Enhanced regex pattern with ordered clause handling
        pattern = r'''
            \\select\s+       # Start with \select
            (?P<conditions>.*?)  # Capture conditions (non-greedy)
            (?=               # Lookahead for possible clauses
                \\columns\b   # \columns marker
                | \\from\b    # \from marker
                | \\select\b  # End marker
            )
            (?:               # Non-capturing group for optional clauses
                (\\columns\s+(?P<columns>.*?))?  # Columns clause
                (?:\\from\s+(?P<table>.*?))?     # Table clause
                | (\\from\s+(?P<table2>.*?))?    # Table clause alternative order
                (?:\\columns\s+(?P<columns2>.*?))? 
            )
            \\select          # End marker
        '''
        
        match = re.search(
            pattern,
            query,
            re.DOTALL | re.IGNORECASE | re.VERBOSE
        )
        
        if not match:
            raise ValueError("Invalid query syntax")
        
        # Extract components with priority for first occurrence
        components['conditions'] = match.group('conditions').strip()
        components['columns'] = match.group('columns') or match.group('columns2')
        components['table'] = (
            match.group('table') or 
            match.group('table2') or 
            self.default_table
        )
        
        # Process column list if present
        if components['columns']:
            components['columns'] = [
                c.strip() 
                for c in components['columns'].split(',')
                if c.strip()
            ]
            
        # Strip cleaning
        components['table'] = components['table'].strip()
        
        # Validate table exists
        table = components['table']
        if table not in self.table_schemas:
            self._refresh_schema_cache()
            if table not in self.table_schemas:
                raise ValueError(f"Table '{table}' does not exist")

        # Process column selection
        if components['columns']:
            self._validate_columns(table, components['columns'])
            columns_sql = ', '.join(components['columns'])
        else:
            columns_sql = '*'

        # Process primary key conditions
        pk = self._get_primary_key(table)
        if len(pk) != 1:
            raise ValueError("Fuzzy queries require single-column primary keys")
        pk_column = pk[0]
        pk_type = self.table_schemas[table]['columns'][pk_column]['type']

        # Parse condition groups
        results = []
        condition_groups = [g.strip() for g in components['conditions'].split(',') if g.strip()]

        for group in condition_groups:
            candidates = [c.strip() for c in group.split('|') if c.strip()]
            for candidate in candidates:
                # Handle fuzzy query syntax
                if candidate.endswith('?'):
                    fuzzy = True
                    candidate = "'" + candidate[:-1].strip() + "%" + "'"
                elif candidate.startswith('?'):
                    fuzzy = True
                    candidate = "'" + "%" + candidate[1:].strip() + "'"
                elif candidate.find("?") > 0:
                    fuzzy = True
                    candidate = candidate.replace("?", "%")
                # Not fuzzy
                else:
                    fuzzy = False

                try:
                    converted = self._convert_value(candidate, pk_type)
                except ValueError as e:
                    logger.warning(f"Value conversion failed: {str(e)}")
                    continue

                # Build parameterized query
                if fuzzy:
                    # ONLY IN THIS WAY, IT IS TRICKY
                    sql = f"SELECT {columns_sql} FROM {table} WHERE {pk_column} LIKE {converted}"
                    params = ()
                else:
                    sql = f"SELECT {columns_sql} FROM {table} WHERE {pk_column} = ?"
                    params = (converted,)
                
                try:
                    result = self.client.fetch_all(sql, params)
                    if result:
                        results.extend(result)
                        break  # Short-circuit on first match
                except QueryExecutionError as e:
                    logger.error(f"Query failed: {str(e)}")
                    continue

        return results

    # Selected object to a pandas dataframe
    def to_pandas(self, selected_obj: Dict[str, Any]):
        return pd.DataFrame(selected_obj)
    
    def __repr__(self) -> str:
        return f"SQLiteParser(defaultstr_table={self.default_table}, client={self.client})"

# Usage Example
if __name__ == '__main__ dude':
    # Initialize client and parser
    client = SQLiteClient('./__database__/another_example.db')
    parser = SQLiteParser(client, 'users')
    
    # Select only
    results = parser.select(
        r"\select 1 | 3, 7 | 2, 4 | 5 \columns name, age, rating \from users \select"
    )
    
    # Also use .to_markdown() to convert to markdown
    print("Query results:\n", parser.to_pandas(results))
    
# User Database example
if __name__ == "__main__ pro (user database)":
    
    # Initialize client and parser
    client = SQLiteClient('./__database__/user_database.db')
    parser = SQLiteParser(client, 'user_primary')
    
    # Fetch all
    client.fetch_all("SELECT * FROM user_primary")
    
    # Fetch Something
    # client.fetch_all("SELECT * FROM NathMath_Test WHERE key LIKE '五彩斑斓%' ")
    
    # Query using DSL
    results = parser.select(
        r"\select ?曙光 \select"
    )
    
    
# Complete Examples
if __name__ == "__main__ pro (well dude, it wouldn't happen)":
    
    # Initialize client and parser
    client = SQLiteClient('./__database__/another_example.db')
    parser = SQLiteParser(client, 'users')
    
    # Create table
    parser.create_table('users', [
        {"name": "id", "type": int, "primary": True},
        {"name": "name", "type": str},
        {"name": "age", "type": int},
        {"name": "rating", "type": float}
    ],
        safemode=False)
    
    # Fetch all
    client.fetch_all("SELECT * FROM users")
    
    # Insert data
    parser.insert([
        {"id": 0, "name": "Alice", "age": 30, "rating": 4.5},
        {"id": 1, "name": "Bob", "age": 25, "rating": 3.8},
        {"id": 2, "name": "Tesla", "age": 16, "rating": 7.9},
        [3, "Charlie", 35, 4.2],
        [4, "NathMath", 25, 9.9],
        [5, "DOF-Studio the author", 9, 9.8]
    ])
    
    # Update data
    parser.update([
        {"id": 11, "name": "Bob-Game", "age": 14, "rating": 9.5},
        ])
    
    # Query using DSL
    results = parser.select(
        r"\select 1 | 3, 7 | 2, 4 | 5 \from users \select"
    )
    
    # Also use .to_markdown() to convert to markdown
    print("Query results:\n", parser.to_pandas(results))
    