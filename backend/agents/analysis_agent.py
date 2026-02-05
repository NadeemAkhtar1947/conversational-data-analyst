"""
AGENT 3: Analysis Agent

Purpose: Convert raw SQL results into business insights and plain English summaries.
Model: Groq LLaMA-3.1-70B Versatile
"""

import json
import logging
from typing import Dict, List, Any
from groq import AsyncGroq
import os

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    Analyzes SQL query results and generates business insights.
    Converts technical data into actionable business intelligence.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the Analysis Agent."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        logger.info(f"Analysis Agent initialized with model: {self.model}")
    
    def _format_data_preview(self, data: List[Dict], max_rows: int = 10) -> str:
        """Format query results for LLM consumption."""
        if not data:
            return "No data returned"
        
        # Show first few rows
        preview = data[:max_rows]
        
        # Calculate summary stats if numeric columns present
        summary_lines = [f"Query returned {len(data)} rows"]
        
        # Format preview
        formatted = json.dumps(preview, indent=2, default=str)
        
        return f"{formatted}\n\nTotal rows: {len(data)}"
    
    def _build_prompt(self, question: str, sql: str, data: List[Dict]) -> str:
        """Build analysis prompt for the LLM."""
        data_preview = self._format_data_preview(data)
        
        prompt = f"""You are a business analyst explaining data insights to business stakeholders.

User Question: "{question}"

SQL Query Executed:
{sql}

Query Results:
{data_preview}

Task: Provide a business analysis of these results.

Your response should include:
1. A clear 2-3 sentence summary in plain English
2. 2-4 key insights or findings
3. Use business terminology (avoid technical jargon)
4. Include specific numbers and percentages when relevant
5. Highlight trends, patterns, or notable findings

Output ONLY valid JSON in this exact format:
{{
  "summary": "Plain English explanation of what the data shows",
  "insights": [
    "First key insight with specific numbers",
    "Second key insight with context",
    "Third key insight if applicable"
  ]
}}

Rules:
- Keep summary concise but informative
- Make insights actionable
- Use dollar signs for currency ($)
- Round large numbers (e.g., "$1.2M" not "$1,234,567.89")
- Avoid phrases like "the data shows" - just state the findings directly
"""
        
        return prompt
    
    async def analyze(self, question: str, sql: str, data: List[Dict]) -> Dict:
        """
        Analyze query results and generate business insights.
        
        Args:
            question: Original user question
            sql: SQL query that was executed
            data: Query results as list of dictionaries
            
        Returns:
            Dict with 'summary' and 'insights'
        """
        # Handle empty results
        if not data:
            return {
                "summary": "No data found matching your criteria. Try adjusting your filters or time range.",
                "insights": [
                    "Consider expanding your search criteria",
                    "Check if the specified filters are too restrictive"
                ]
            }
        
        # Handle single aggregate result (e.g., COUNT, SUM)
        if len(data) == 1 and len(data[0]) == 1:
            value = list(data[0].values())[0]
            return {
                "summary": f"The query returned a single value: {self._format_value(value)}",
                "insights": [
                    f"This represents the {list(data[0].keys())[0]} for your query"
                ]
            }
        
        try:
            prompt = self._build_prompt(question, sql, data)
            
            logger.info(f"Analyzing {len(data)} rows of data")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst. Output ONLY valid JSON with summary and insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Slightly higher for creative insights
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            summary = result.get("summary", "Analysis completed successfully")
            insights = result.get("insights", [])
            
            # Ensure insights is a list
            if not isinstance(insights, list):
                insights = [str(insights)]
            
            logger.info(f"Generated {len(insights)} insights")
            
            return {
                "summary": summary,
                "insights": insights[:4]  # Limit to 4 insights
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            return self._generate_fallback_analysis(question, data)
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._generate_fallback_analysis(question, data)
    
    def _generate_fallback_analysis(self, question: str, data: List[Dict]) -> Dict:
        """Generate basic analysis when LLM fails."""
        row_count = len(data)
        
        # Try to extract some basic insights
        insights = []
        
        if row_count > 0:
            insights.append(f"Query returned {row_count} records")
            
            # Check for numeric columns
            first_row = data[0]
            numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
            
            if numeric_cols:
                col = numeric_cols[0]
                values = [row[col] for row in data if col in row and row[col] is not None]
                if values:
                    insights.append(f"Values range from {min(values):.2f} to {max(values):.2f}")
        
        return {
            "summary": f"Query executed successfully and returned {row_count} rows.",
            "insights": insights if insights else ["Data retrieved successfully"]
        }
    
    def _format_value(self, value: Any) -> str:
        """Format a single value for display."""
        if isinstance(value, float):
            # Assume it's currency if > 100
            if value > 100:
                return f"${value:,.2f}"
            return f"{value:.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        return str(value)


# Example usage and testing
async def test_analysis_agent():
    """Test the Analysis Agent"""
    agent = AnalysisAgent()
    
    # Test 1: Sales by region
    question = "Total sales by region"
    sql = "SELECT region, SUM(sales) as total_sales FROM superstore GROUP BY region"
    data = [
        {"region": "West", "total_sales": 725458.0},
        {"region": "East", "total_sales": 678781.2},
        {"region": "Central", "total_sales": 501240.0},
        {"region": "South", "total_sales": 391721.9}
    ]
    
    result = await agent.analyze(question, sql, data)
    print(f"Test 1 - Summary: {result['summary']}")
    print(f"Insights: {result['insights']}\n")
    
    # Test 2: Empty results
    result = await agent.analyze("Sales for invalid region", sql, [])
    print(f"Test 2 - Summary: {result['summary']}")
    print(f"Insights: {result['insights']}\n")
    
    # Test 3: Single value
    data = [{"total": 2297201.0}]
    result = await agent.analyze("Total sales", "SELECT SUM(sales) as total FROM superstore", data)
    print(f"Test 3 - Summary: {result['summary']}")
    print(f"Insights: {result['insights']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analysis_agent())
