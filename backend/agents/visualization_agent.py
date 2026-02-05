"""
AGENT 4: Visualization Agent

Purpose: Determine the best chart type and axes for visualizing query results.
Model: Groq LLaMA-3.1-70B Versatile
"""

import json
import logging
from typing import Dict, List, Any
from groq import AsyncGroq
import os

logger = logging.getLogger(__name__)


class VisualizationAgent:
    """
    Determines optimal visualization type for query results.
    Chooses between bar charts, line charts, pie charts, and tables.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the Visualization Agent."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        logger.info(f"Visualization Agent initialized with model: {self.model}")
    
    def _analyze_data_structure(self, data: List[Dict]) -> Dict:
        """Analyze the structure of query results."""
        if not data:
            return {"row_count": 0, "columns": [], "column_types": {}}
        
        first_row = data[0]
        columns = list(first_row.keys())
        
        # Determine column types
        column_types = {}
        for col in columns:
            sample_values = [row.get(col) for row in data[:10] if col in row and row.get(col) is not None]
            if not sample_values:
                column_types[col] = "unknown"
            elif all(isinstance(v, (int, float)) for v in sample_values):
                column_types[col] = "numeric"
            elif all(isinstance(v, str) for v in sample_values):
                # Check if it looks like a date
                if any(keyword in col.lower() for keyword in ['date', 'time', 'month', 'year']):
                    column_types[col] = "temporal"
                else:
                    column_types[col] = "categorical"
            else:
                column_types[col] = "mixed"
        
        return {
            "row_count": len(data),
            "columns": columns,
            "column_types": column_types
        }
    
    def _build_prompt(self, question: str, data_structure: Dict, sample_data: List[Dict]) -> str:
        """Build prompt for chart type selection."""
        columns_info = "\n".join([
            f"  - {col} ({dtype})"
            for col, dtype in data_structure["column_types"].items()
        ])
        
        sample_preview = json.dumps(sample_data[:3], indent=2, default=str)
        
        prompt = f"""You are a data visualization expert. Choose the best chart type for this data.

User Question: "{question}"

Data Structure:
- Row count: {data_structure['row_count']}
- Columns:
{columns_info}

Sample Data:
{sample_preview}

Task: Choose the optimal visualization.

Chart Type Guidelines:
1. BAR CHART: Use for comparing categories (regions, products, segments)
   - Best for: Top N, rankings, comparisons across categories
   - Requires: 1 categorical column + 1 numeric column

2. LINE CHART: Use for time series or trends
   - Best for: Temporal data, trends over time
   - Requires: 1 temporal/date column + 1 numeric column

3. PIE CHART: Use for showing parts of a whole (limited to ≤6 categories)
   - Best for: Market share, composition, proportions
   - Requires: 1 categorical column + 1 numeric column
   - Only if row_count ≤ 6

4. TABLE: Use when:
   - More than 2 columns to display
   - Data doesn't fit other chart types
   - Detailed numeric comparison needed
   - Row count is small (< 20)

Output ONLY valid JSON in this exact format:
{{
  "chart_type": "bar" | "line" | "pie" | "table",
  "x_axis": "column_name",
  "y_axis": "column_name",
  "reasoning": "Brief explanation"
}}

Rules:
- x_axis should be categorical or temporal
- y_axis should be numeric
- If chart_type is "table", x_axis and y_axis can be null
- Choose the chart type that best answers the user's question
"""
        
        return prompt
    
    async def suggest_chart(self, question: str, data: List[Dict]) -> Dict:
        """
        Suggest the best visualization for query results.
        
        Args:
            question: Original user question
            data: Query results as list of dictionaries
            
        Returns:
            Dict with chart_type, x_axis, y_axis, and reasoning
        """
        # Handle empty data
        if not data:
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "reasoning": "No data to visualize"
            }
        
        # Analyze data structure
        data_structure = self._analyze_data_structure(data)
        
        # Use heuristics for simple cases
        if data_structure["row_count"] == 1:
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "reasoning": "Single row result best displayed as table"
            }
        
        # If many columns, default to table
        if len(data_structure["columns"]) > 3:
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "reasoning": "Multiple columns best displayed in table format"
            }
        
        # Try LLM-based selection for 2-3 column data
        try:
            prompt = self._build_prompt(question, data_structure, data)
            
            logger.info(f"Determining chart type for {data_structure['row_count']} rows")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data visualization expert. Output ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            chart_type = result.get("chart_type", "table")
            x_axis = result.get("x_axis")
            y_axis = result.get("y_axis")
            reasoning = result.get("reasoning", "")
            
            # Validate chart type
            valid_types = ["bar", "line", "pie", "table"]
            if chart_type not in valid_types:
                chart_type = "table"
            
            # Validate axes exist in data
            if x_axis and x_axis not in data_structure["columns"]:
                x_axis = data_structure["columns"][0]
            
            if y_axis and y_axis not in data_structure["columns"]:
                numeric_cols = [c for c, t in data_structure["column_types"].items() if t == "numeric"]
                y_axis = numeric_cols[0] if numeric_cols else data_structure["columns"][-1]
            
            logger.info(f"Selected chart: {chart_type} ({x_axis} vs {y_axis})")
            
            return {
                "chart_type": chart_type,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.error(f"Chart selection failed: {e}")
            return self._fallback_chart_selection(data_structure)
    
    def _fallback_chart_selection(self, data_structure: Dict) -> Dict:
        """Fallback heuristic-based chart selection."""
        columns = data_structure["columns"]
        types = data_structure["column_types"]
        
        # Find categorical and numeric columns
        categorical = [c for c, t in types.items() if t in ["categorical", "temporal"]]
        numeric = [c for c, t in types.items() if t == "numeric"]
        
        # Default to table
        if not categorical or not numeric:
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "reasoning": "Data structure doesn't fit standard chart types"
            }
        
        # Check for temporal data (line chart)
        temporal = [c for c, t in types.items() if t == "temporal"]
        if temporal:
            return {
                "chart_type": "line",
                "x_axis": temporal[0],
                "y_axis": numeric[0],
                "reasoning": "Time series data best shown as line chart"
            }
        
        # Check row count for pie chart
        if data_structure["row_count"] <= 6:
            return {
                "chart_type": "pie",
                "x_axis": categorical[0],
                "y_axis": numeric[0],
                "reasoning": "Small number of categories suitable for pie chart"
            }
        
        # Default to bar chart
        return {
            "chart_type": "bar",
            "x_axis": categorical[0],
            "y_axis": numeric[0],
            "reasoning": "Categorical comparison best shown as bar chart"
        }


# Example usage and testing
async def test_visualization_agent():
    """Test the Visualization Agent"""
    agent = VisualizationAgent()
    
    # Test 1: Regional sales (bar chart)
    question = "Total sales by region"
    data = [
        {"region": "West", "total_sales": 725458.0},
        {"region": "East", "total_sales": 678781.2},
        {"region": "Central", "total_sales": 501240.0},
        {"region": "South", "total_sales": 391721.9}
    ]
    result = await agent.suggest_chart(question, data)
    print(f"Test 1: {result}\n")
    
    # Test 2: Time series (line chart)
    question = "Monthly sales trend"
    data = [
        {"month": "2024-01", "sales": 50000},
        {"month": "2024-02", "sales": 55000},
        {"month": "2024-03", "sales": 52000}
    ]
    result = await agent.suggest_chart(question, data)
    print(f"Test 2: {result}\n")
    
    # Test 3: Multiple columns (table)
    question = "Product details"
    data = [
        {"product": "Desk", "sales": 1000, "profit": 200, "quantity": 5},
        {"product": "Chair", "sales": 500, "profit": 100, "quantity": 10}
    ]
    result = await agent.suggest_chart(question, data)
    print(f"Test 3: {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_visualization_agent())
