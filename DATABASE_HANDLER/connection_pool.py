import asyncpg
from typing import Optional
from config import config

DATABASE_URL = config.DATABASE_URL


class DatabasePool:
    """
    Singleton database connection pool manager for PostgreSQL
    """
    _instance: Optional['DatabasePool'] = None
    _pool: Optional[asyncpg.Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, min_size: int = 5, max_size: int = 20):
        """
        Initialize the connection pool
        
        Args:
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
        """
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60
            )
    
    async def close(self):
        """
        Close all connections in the pool
        """
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    def get_pool(self) -> asyncpg.Pool:
        """
        Get the connection pool instance
        
        Returns:
            The asyncpg connection pool
        
        Raises:
            RuntimeError: If pool is not initialized
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        return self._pool
    
    async def acquire(self):
        """
        Acquire a connection from the pool
        
        Returns:
            Database connection context manager
        """
        pool = self.get_pool()
        return pool.acquire()
    
    async def execute(self, query: str, *args):
        """
        Execute a query using a connection from the pool
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Query result
        """
        pool = self.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """
        Fetch multiple rows using a connection from the pool
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            List of records
        """
        pool = self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """
        Fetch a single row using a connection from the pool
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Single record or None
        """
        pool = self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """
        Fetch a single value using a connection from the pool
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Single value or None
        """
        pool = self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)


db_pool = DatabasePool()