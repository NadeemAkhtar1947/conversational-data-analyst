"""
Database connection and query execution utilities.
"""

import logging
from typing import Dict, List, Optional
import asyncpg
import os
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections and query execution.
    Uses asyncpg for async operations.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize Database Manager.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.warning("DATABASE_URL not set - database functionality will be limited")
            self.database_url = None
        
        self.pool = None
        self._schema_cache = None
    
    async def initialize(self):
        """Initialize connection pool."""
        if not self.database_url:
            logger.warning("Skipping database initialization - no DATABASE_URL provided")
            return
            
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
                server_settings={
                    'application_name': 'conversational_analyst'
                }
            )
            logger.info("Database connection pool initialized")
            
            # Cache schema information
            await self._cache_schema()
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute_query(self, sql: str, timeout: int = 30) -> List[Dict]:
        """
        Execute a SELECT query and return results as list of dictionaries.
        
        Args:
            sql: SQL query (must be validated first)
            timeout: Query timeout in seconds
            
        Returns:
            List of dictionaries with query results
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        
        try:
            async with self.pool.acquire() as conn:
                # Set query timeout
                await conn.execute(f'SET statement_timeout = {timeout * 1000}')
                
                # Execute query
                logger.info(f"Executing query: {sql[:200]}...")
                rows = await conn.fetch(sql)
                
                # Convert to list of dicts
                results = [dict(row) for row in rows]
                
                logger.info(f"Query returned {len(results)} rows")
                return results
                
        except asyncpg.PostgresError as e:
            logger.error(f"Database query error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            raise
    
    async def _cache_schema(self):
        """Cache database schema information for all tables."""
        try:
            async with self.pool.acquire() as conn:
                # Get all tables in public schema
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                
                self._schema_cache = {"tables": {}}
                
                for table_row in tables:
                    table_name = table_row['table_name']
                    
                    # Get column information for this table
                    columns = await conn.fetch(f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        ORDER BY ordinal_position
                    """)
                    
                    # Get sample data
                    sample = await conn.fetch(f"SELECT * FROM {table_name} LIMIT 3")
                    
                    self._schema_cache["tables"][table_name] = {
                        "columns": [dict(col) for col in columns],
                        "sample_data": [dict(row) for row in sample]
                    }
                
                logger.info(f"Cached schema for {len(tables)} tables: {', '.join([t['table_name'] for t in tables])}")
                
        except Exception as e:
            logger.error(f"Failed to cache schema: {e}")
            self._schema_cache = {"tables": {}}
    
    def get_schema_info(self, table_name: str = None) -> Dict:
        """Get cached schema information for a specific table or all tables."""
        if not self._schema_cache:
            return {"tables": {}}
        
        if table_name:
            # Return specific table schema
            return self._schema_cache.get("tables", {}).get(table_name, {"columns": [], "sample_data": []})
        
        return self._schema_cache
    
    def get_table_list(self) -> list:
        """Get list of all available tables."""
        if not self._schema_cache:
            return []
        return list(self._schema_cache.get("tables", {}).keys())
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions (not used for read-only, but available)."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Example usage and testing
async def test_database():
    """Test Database Manager"""
    db = DatabaseManager()
    
    try:
        await db.initialize()
        
        # Test connection
        connected = await db.test_connection()
        print(f"Connection test: {connected}")
        
        # Get schema info
        schema = db.get_schema_info()
        print(f"Schema columns: {len(schema['columns'])}")
        print(f"Sample data rows: {len(schema['sample_data'])}")
        
        # Execute test query
        results = await db.execute_query("SELECT region, SUM(sales) as total FROM superstore GROUP BY region LIMIT 5")
        print(f"Query results: {results}")
        
    finally:
        await db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_database())
