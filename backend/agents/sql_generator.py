"""
AGENT 2: SQL Generator Agent

Purpose: Generate safe SELECT queries from natural language questions.
Primary Model: SQLCoder-7B via HuggingFace Inference API
Fallback Model 1: OpenAI GPT-OSS-120B via Groq
Fallback Model 2: LLaMA-3.3-70B via Groq
"""

import json
import logging
import re
from typing import Dict, Optional
import httpx
from groq import AsyncGroq
import os

logger = logging.getLogger(__name__)


class SQLGeneratorAgent:
    """
    Generates safe SQL queries from natural language questions.
    Uses SQLCoder-7B as primary model with Groq LLaMA-3 as fallback.
    """
    
    SCHEMA_INFO = """
Table: superstore

Columns (21):
  - row_id (INTEGER): Unique row identifier
  - order_id (TEXT): Order ID
  - order_date (DATE): Order date
  - ship_date (DATE): Ship date
  - ship_mode (TEXT): Shipping mode
  - customer_id (TEXT): Customer ID
  - customer_name (TEXT): Customer name
  - segment (TEXT): Customer segment (Consumer, Corporate, Home Office)
  - country (TEXT): Country
  - city (TEXT): City
  - state (TEXT): State
  - postal_code (TEXT): Postal code
  - region (TEXT): Region (West, East, Central, South)
  - product_id (TEXT): Product ID
  - category (TEXT): Product category (Furniture, Office Supplies, Technology)
  - sub_category (TEXT): Product sub-category
  - product_name (TEXT): Product name
  - sales (NUMERIC): Sales amount in USD
  - quantity (INTEGER): Quantity sold
  - discount (NUMERIC): Discount percentage (0-1)
  - profit (NUMERIC): Profit amount in USD

Sample queries:
  - Total sales: SELECT SUM(sales) FROM superstore
  - By region: SELECT region, SUM(sales) FROM superstore GROUP BY region
  - Time series: SELECT DATE_TRUNC('month', order_date) as month, SUM(sales) FROM superstore GROUP BY month
"""
    
    def __init__(self, hf_token: Optional[str] = None, groq_key: Optional[str] = None):
        """Initialize SQL Generator with HuggingFace and Groq credentials."""
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.groq_key = groq_key or os.getenv("GROQ_API_KEY")
        
        if not self.hf_token:
            logger.warning("HF_TOKEN not found, will use Groq fallback only")
        
        if not self.groq_key:
            raise ValueError("GROQ_API_KEY is required for fallback")
        
        self.groq_client = AsyncGroq(api_key=self.groq_key)
        self.groq_model_primary = "openai/gpt-oss-120b"
        self.groq_model_fallback = "llama-3.3-70b-versatile"
        self._current_schema = None  # Will be set when schema_override is provided
        
        logger.info(f"SQL Generator initialized with cascade: SQLCoder-7B → {self.groq_model_primary} → {self.groq_model_fallback}")
    
    def _get_schema_text(self) -> str:
        """Get schema text (either custom or default superstore schema)."""
        if self._current_schema:
            return self._current_schema.get("schema_text", self.SCHEMA_INFO)
        return self.SCHEMA_INFO
        
    async def generate_sql_hf(self, question: str) -> Optional[str]:
        """
        Generate SQL using SQLCoder-7B via HuggingFace Inference API.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string or None if failed
        """
        if not self.hf_token:
            return None
        
        # SQLCoder prompt format
        prompt = f"""### Task
Generate a SQL query to answer the following question: `{question}`

### Database Schema
{self._get_schema_text()}

### SQL Query
Return only the SQL query without explanation. Use PostgreSQL syntax.
"""
        
        try:
            # Use httpx to call HuggingFace API directly (async-native)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://router.huggingface.co/models/defog/sqlcoder-7b-2",
                    headers={"Authorization": f"Bearer {self.hf_token}"},
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "max_new_tokens": 300,
                            "temperature": 0.1,
                            "return_full_text": False
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # HF returns [{"generated_text": "..."}]
                    if isinstance(result, list) and len(result) > 0:
                        sql = result[0].get("generated_text", "").strip()
                    elif isinstance(result, dict):
                        sql = result.get("generated_text", "").strip()
                    else:
                        sql = None
                    
                    if sql:
                        # Clean up the SQL
                        sql = self._clean_sql(sql)
                        logger.info(f"✓ SQLCoder-7B generated: {sql}")
                        return sql
                else:
                    logger.warning(f"SQLCoder-7B HTTP error: {response.status_code} - {response.text}")
                    
            return None
                    
        except Exception as e:
            logger.warning(f"SQLCoder-7B request failed: {e}")
            return None
    
    async def generate_sql_groq(self, question: str, use_fallback_model: bool = False) -> str:
        """
        Generate SQL using Groq models.
        
        Args:
            question: Natural language question
            use_fallback_model: If True, use llama-3.3-70b instead of gpt-oss-120b
            
        Returns:
            SQL query string
        """
        model = self.groq_model_fallback if use_fallback_model else self.groq_model_primary
        
        prompt = f"""You are an expert PostgreSQL SQL generator for business analytics.

Database Schema:
{self._get_schema_text()}

User Question: "{question}"

Generate a SELECT query that answers this question.

STRICT RULES:
1. ONLY SELECT statements (no INSERT, UPDATE, DELETE, DROP)
2. ONLY use the 'superstore' table
3. Use proper aggregation (SUM, AVG, COUNT, MAX, MIN)
4. Add LIMIT 100 for queries that might return many rows
5. Use DATE_TRUNC for date grouping
6. Use proper WHERE clauses for filtering
7. Use ORDER BY for ranked results

Output ONLY valid JSON:
{{"sql": "SELECT ..."}}

Do NOT include any explanation, just the JSON.
"""
        
        try:
            response = await self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a SQL expert. Output ONLY valid JSON with SQL query."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            sql = result.get("sql", "").strip()
            
            logger.info(f"Groq {model} generated: {sql}")
            return sql
            
        except Exception as e:
            logger.error(f"Groq SQL generation failed ({model}): {e}")
            raise
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up generated SQL query."""
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Remove trailing semicolon if present
        sql = sql.rstrip(';')
        
        return sql.strip()
    
    async def generate(self, question: str, use_fallback_first: bool = False, schema_override: Optional[Dict] = None) -> Dict:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            use_fallback_first: If True, skip HF and use Groq directly
            schema_override: Optional custom schema info for uploaded CSV
            
        Returns:
            Dict with 'sql', 'source', and 'confidence'
        """
        sql = None
        source = None
        
        # Store schema for use in generation methods
        self._current_schema = schema_override
        
        # Level 1: Try SQLCoder-7B first (unless fallback requested)
        if not use_fallback_first:
            sql = await self.generate_sql_hf(question)
            if sql:
                source = "sqlcoder-7b"
                logger.info("✓ SQLCoder-7B succeeded")
        
        # Level 2: Fallback to Groq GPT-OSS-120B
        if not sql:
            try:
                sql = await self.generate_sql_groq(question, use_fallback_model=False)
                source = "gpt-oss-120b"
                logger.info("✓ GPT-OSS-120B fallback succeeded")
            except Exception as e:
                logger.warning(f"GPT-OSS-120B failed: {e}")
        
        # Level 3: Final fallback to LLaMA-3.3-70B
        if not sql:
            try:
                sql = await self.generate_sql_groq(question, use_fallback_model=True)
                source = "llama-3.3-70b"
                logger.info("✓ LLaMA-3.3-70B final fallback succeeded")
            except Exception as e:
                logger.error(f"All SQL generation methods failed: {e}")
                raise
        
        # Determine confidence
        confidence = "high" if source == "sqlcoder-7b" else "medium" if source == "gpt-oss-120b" else "low"
        
        return {
            "sql": sql,
            "source": source,
            "confidence": confidence
        }
    
    def add_safety_limit(self, sql: str, default_limit: int = 100) -> str:
        """
        Add LIMIT clause to SQL if not present and query might return many rows.
        
        Args:
            sql: SQL query
            default_limit: Default limit to add
            
        Returns:
            SQL with LIMIT clause
        """
        sql_upper = sql.upper()
        
        # Don't add limit if already present
        if 'LIMIT' in sql_upper:
            return sql
        
        # Add limit if query uses GROUP BY or might return many rows
        if 'GROUP BY' not in sql_upper and 'COUNT' not in sql_upper:
            sql = f"{sql} LIMIT {default_limit}"
        
        return sql


# Example usage and testing
async def test_sql_generator():
    """Test the SQL Generator Agent"""
    agent = SQLGeneratorAgent()
    
    questions = [
        "Total sales by region",
        "Top 10 most profitable products",
        "Monthly sales trend for 2023",
        "Average discount by product category"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        result = await agent.generate(question)
        print(f"SQL: {result['sql']}")
        print(f"Source: {result['source']}")
        print(f"Confidence: {result['confidence']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sql_generator())
