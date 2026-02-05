"""
SQL Validation and Safety Layer

Purpose: Ensure only safe SELECT queries are executed.
Non-LLM based validation using regex and SQL parsing.
"""

import re
import logging
from typing import Dict, Optional, List
from sqlparse import parse, tokens
import sqlparse

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    Validates SQL queries for safety before execution.
    Blocks DML/DDL operations and enforces read-only access.
    """
    
    # Dangerous SQL keywords that should never appear
    BLOCKED_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
        'EXEC', 'EXECUTE', 'CALL', 'PROCEDURE'
    ]
    
    # Allowed table names (whitelist)
    ALLOWED_TABLES = ['superstore']
    
    # Maximum query length
    MAX_QUERY_LENGTH = 2000
    
    # Default row limit for safety
    DEFAULT_LIMIT = 1000
    
    def __init__(self):
        """Initialize SQL Validator."""
        # Compile regex patterns for efficiency
        self.blocked_pattern = re.compile(
            r'\b(' + '|'.join(self.BLOCKED_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        
        # Pattern for detecting SQL injection attempts
        self.injection_patterns = [
            r"--",  # SQL comments
            r"/\*",  # Multi-line comments
            r";\s*\w+",  # Multiple statements
            r"'\s*OR\s+'",  # Classic injection
            r"'\s*=\s*'",  # Tautology
            r"xp_",  # Extended stored procedures
            r"sp_",  # System stored procedures
        ]
        
        self.injection_regex = re.compile(
            '|'.join(self.injection_patterns),
            re.IGNORECASE
        )
    
    def validate(self, sql: str) -> Dict:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query string
            
        Returns:
            Dict with 'valid', 'error', 'modified_sql'
        """
        if not sql or not sql.strip():
            return {
                "valid": False,
                "error": "Empty query",
                "modified_sql": None
            }
        
        sql = sql.strip()
        
        # Check 1: Query length
        if len(sql) > self.MAX_QUERY_LENGTH:
            return {
                "valid": False,
                "error": f"Query too long (max {self.MAX_QUERY_LENGTH} characters)",
                "modified_sql": None
            }
        
        # Check 2: Must start with SELECT
        if not re.match(r'^\s*SELECT\s+', sql, re.IGNORECASE):
            return {
                "valid": False,
                "error": "Only SELECT queries are allowed",
                "modified_sql": None
            }
        
        # Check 3: Block dangerous keywords
        blocked_match = self.blocked_pattern.search(sql)
        if blocked_match:
            return {
                "valid": False,
                "error": f"Blocked keyword detected: {blocked_match.group(1)}",
                "modified_sql": None
            }
        
        # Check 4: SQL injection patterns
        injection_match = self.injection_regex.search(sql)
        if injection_match:
            logger.warning(f"Potential SQL injection detected: {injection_match.group()}")
            return {
                "valid": False,
                "error": "Invalid SQL syntax detected",
                "modified_sql": None
            }
        
        # Check 5: Table whitelist
        if not self._validate_tables(sql):
            return {
                "valid": False,
                "error": f"Query must only use allowed tables: {', '.join(self.ALLOWED_TABLES)}",
                "modified_sql": None
            }
        
        # Check 6: Ensure LIMIT clause exists (add if missing)
        modified_sql = self._ensure_limit(sql)
        
        # Check 7: Parse with sqlparse for syntax validation
        try:
            parsed = sqlparse.parse(modified_sql)
            if not parsed:
                return {
                    "valid": False,
                    "error": "Invalid SQL syntax",
                    "modified_sql": None
                }
        except Exception as e:
            logger.error(f"SQL parsing failed: {e}")
            return {
                "valid": False,
                "error": "Invalid SQL syntax",
                "modified_sql": None
            }
        
        logger.info(f"SQL validation passed: {modified_sql[:100]}...")
        
        return {
            "valid": True,
            "error": None,
            "modified_sql": modified_sql
        }
    
    def _validate_tables(self, sql: str) -> bool:
        """
        Check if query only uses whitelisted tables.
        
        Args:
            sql: SQL query
            
        Returns:
            True if all tables are whitelisted
        """
        # Extract table names using regex pattern matching
        # Match FROM/JOIN followed by table name (before WHERE, GROUP BY, etc.)
        try:
            # Pattern to find table names after FROM or JOIN
            table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(table_pattern, sql, re.IGNORECASE)
            
            if not matches:
                # No tables found - likely invalid query
                logger.warning("No tables found in query")
                return False
            
            # Check all found tables against whitelist
            for table_name in matches:
                table_name = table_name.lower().strip()
                if table_name not in self.ALLOWED_TABLES:
                    logger.warning(f"Unauthorized table access: {table_name}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Table validation failed: {e}")
            # If parsing fails, be conservative and reject
            return False
    
    def _ensure_limit(self, sql: str) -> str:
        """
        Ensure query has a LIMIT clause. Add one if missing.
        
        Args:
            sql: SQL query
            
        Returns:
            SQL query with LIMIT clause
        """
        sql_upper = sql.upper()
        
        # Already has LIMIT
        if 'LIMIT' in sql_upper:
            # Check if limit is reasonable
            limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
            if limit_match:
                limit_value = int(limit_match.group(1))
                if limit_value > self.DEFAULT_LIMIT:
                    logger.warning(f"Reducing LIMIT from {limit_value} to {self.DEFAULT_LIMIT}")
                    sql = re.sub(
                        r'LIMIT\s+\d+',
                        f'LIMIT {self.DEFAULT_LIMIT}',
                        sql,
                        flags=re.IGNORECASE
                    )
            return sql
        
        # Don't add LIMIT if query has aggregation without GROUP BY
        # (these typically return single rows)
        has_aggregation = any(keyword in sql_upper for keyword in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN('])
        has_group_by = 'GROUP BY' in sql_upper
        
        if has_aggregation and not has_group_by:
            return sql
        
        # Add LIMIT at the end
        return f"{sql} LIMIT {self.DEFAULT_LIMIT}"
    
    def sanitize_error(self, error: Exception) -> str:
        """
        Sanitize database error messages for user display.
        Remove sensitive information.
        
        Args:
            error: Exception from database
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        # Map technical errors to user-friendly messages
        if 'syntax' in error_str:
            return "There was an error in the generated query. Please try rephrasing your question."
        elif 'column' in error_str and 'does not exist' in error_str:
            return "The query referenced a column that doesn't exist. Please try a different question."
        elif 'relation' in error_str and 'does not exist' in error_str:
            return "The query referenced a table that doesn't exist. Please try again."
        elif 'timeout' in error_str or 'timed out' in error_str:
            return "The query took too long to execute. Please try a simpler question or add more filters."
        elif 'permission' in error_str or 'denied' in error_str:
            return "Database permission error. Please contact support."
        else:
            return "An error occurred while executing the query. Please try rephrasing your question."


# Testing
def test_validator():
    """Test SQL Validator"""
    validator = SQLValidator()
    
    # Test 1: Valid SELECT
    result = validator.validate("SELECT * FROM superstore WHERE region = 'West'")
    print(f"Test 1 (Valid SELECT): {result['valid']} - {result.get('error')}")
    
    # Test 2: Invalid UPDATE
    result = validator.validate("UPDATE superstore SET sales = 0")
    print(f"Test 2 (Invalid UPDATE): {result['valid']} - {result['error']}")
    
    # Test 3: Invalid DROP
    result = validator.validate("DROP TABLE superstore")
    print(f"Test 3 (Invalid DROP): {result['valid']} - {result['error']}")
    
    # Test 4: SQL Injection attempt
    result = validator.validate("SELECT * FROM superstore WHERE id = 1; DROP TABLE users; --")
    print(f"Test 4 (SQL Injection): {result['valid']} - {result['error']}")
    
    # Test 5: Invalid table
    result = validator.validate("SELECT * FROM users")
    print(f"Test 5 (Invalid table): {result['valid']} - {result['error']}")
    
    # Test 6: Query without LIMIT
    result = validator.validate("SELECT * FROM superstore")
    print(f"Test 6 (Auto-LIMIT): {result['valid']} - Modified: {result['modified_sql']}")
    
    # Test 7: Aggregation (should not add LIMIT)
    result = validator.validate("SELECT COUNT(*) FROM superstore")
    print(f"Test 7 (Aggregation): {result['valid']} - Modified: {result['modified_sql']}")


if __name__ == "__main__":
    test_validator()
