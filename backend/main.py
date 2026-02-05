"""
FastAPI Backend for Conversational Analytics System
"""

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
import pandas as pd
import duckdb
from io import StringIO
import uuid

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agents and utilities
from backend.agents.context_rewriter import ContextRewriterAgent
from backend.agents.sql_generator import SQLGeneratorAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.visualization_agent import VisualizationAgent
from backend.utils.sql_validator import SQLValidator
from backend.utils.database import DatabaseManager
from backend.utils.session import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Conversational Analytics API",
    description="multi-agent AI analytics system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_manager: Optional[DatabaseManager] = None
session_manager = SessionManager(ttl_minutes=60, max_history=5)
sql_validator = SQLValidator()

# In-memory dataset storage (session-based)
uploaded_datasets: Dict[str, pd.DataFrame] = {}

# Agents
context_agent: Optional[ContextRewriterAgent] = None
sql_agent: Optional[SQLGeneratorAgent] = None
analysis_agent: Optional[AnalysisAgent] = None
viz_agent: Optional[VisualizationAgent] = None


# Pydantic models
class QueryRequest(BaseModel):
    """Request model for /query endpoint"""
    question: str = Field(..., min_length=3, max_length=500, description="Natural language question")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    use_uploaded_data: bool = Field(False, description="Whether to use uploaded CSV data")
    dataset: str = Field("superstore", description="Dataset/table name to query")

class UploadResponse(BaseModel):
    """Response model for /upload-csv endpoint"""
    success: bool
    session_id: str
    filename: str
    rows: int
    columns: List[str]
    message: str


class QueryResponse(BaseModel):
    """Response model for /query endpoint"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[Dict] = None


class HealthResponse(BaseModel):
    """Response model for /health endpoint"""
    status: str
    timestamp: str
    database: bool
    agents: Dict[str, bool]


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager, context_agent, sql_agent, analysis_agent, viz_agent
    
    logger.info("Starting Conversational Analytics System...")
    
    try:
        # Initialize database (optional for UI preview)
        try:
            db_manager = DatabaseManager()
            await db_manager.initialize()
            logger.info("Database connected")
        except Exception as db_error:
            logger.warning(f"Database initialization failed (UI will still work): {db_error}")
            db_manager = None
        
        # Initialize agents
        context_agent = ContextRewriterAgent()
        logger.info("Context Rewriter Agent initialized")
        
        sql_agent = SQLGeneratorAgent()
        logger.info("SQL Generator Agent initialized")
        
        analysis_agent = AnalysisAgent()
        logger.info("Analysis Agent initialized")
        
        viz_agent = VisualizationAgent()
        logger.info("Visualization Agent initialized")
        
        logger.info("System ready!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_manager
    
    logger.info("Shutting down...")
    
    if db_manager:
        await db_manager.close()
    
    logger.info("Shutdown complete")


# API Endpoints
@app.get("/", response_class=FileResponse)
async def root():
    """Serve the frontend HTML (ChatGPT-style interface)"""
    return FileResponse("static/chat.html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_healthy = False
    if db_manager:
        try:
            db_healthy = await db_manager.test_connection()
        except:
            pass
    
    return HealthResponse(
        status="healthy" if db_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        database=db_healthy,
        agents={
            "context_rewriter": context_agent is not None,
            "sql_generator": sql_agent is not None,
            "analysis": analysis_agent is not None,
            "visualization": viz_agent is not None
        }
    )


@app.post("/upload-csv", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload CSV file for analysis.
    Stores data in memory with DuckDB for SQL querying.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read CSV content
        content = await file.read()
        csv_string = StringIO(content.decode('utf-8'))
        
        # Load into pandas DataFrame
        df = pd.read_csv(csv_string)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Generate session ID for this dataset
        session_id = str(uuid.uuid4())
        
        # Store in memory
        uploaded_datasets[session_id] = df
        
        logger.info(f"CSV uploaded: {file.filename} ({len(df)} rows, {len(df.columns)} columns) - Session: {session_id}")
        
        return UploadResponse(
            success=True,
            session_id=session_id,
            filename=file.filename,
            rows=len(df),
            columns=df.columns.tolist(),
            message=f"Successfully uploaded {file.filename} with {len(df)} rows"
        )
        
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Main query endpoint - orchestrates all agents.
    
    Pipeline:
    1. Context Rewriter Agent
    2. SQL Generator Agent
    3. SQL Validator
    4. Database Execution
    5. Analysis Agent (parallel)
    6. Visualization Agent (parallel)
    """
    try:
        question = request.question.strip()
        session_id = request.session_id
        
        # Create or retrieve session
        if not session_id:
            session_id = session_manager.create_session()
        
        session = session_manager.get_session(session_id)
        if not session:
            session_id = session_manager.create_session()
            session = session_manager.get_session(session_id)
        
        history = session_manager.get_history(session_id)
        
        logger.info(f"Processing query: {question} (session: {session_id})")
        logger.info(f"use_uploaded_data: {request.use_uploaded_data}, session in datasets: {request.session_id in uploaded_datasets}")
        
        # Step 1: Context Rewriter
        context_result = await context_agent.rewrite(question, history)
        rewritten_question = context_result["rewritten_question"]
        used_context = context_result.get("used_context", False)
        
        logger.info(f"Rewritten: {rewritten_question} (used_context={used_context})")
        
        # Check if question is too vague (single word or short phrase without clear intent)
        question_words = rewritten_question.strip().split()
        has_question_word = any(word.lower() in rewritten_question.lower() for word in ['how', 'what', 'when', 'where', 'who', 'which', 'show', 'list', 'get', 'find', 'count', 'total', 'average', 'sum', 'top', 'bottom', 'highest', 'lowest'])
        
        if len(question_words) <= 3 and not has_question_word:
            # Generate helpful suggestions
            suggestions = []
            entity = rewritten_question.strip()
            
            if request.use_uploaded_data and request.session_id in uploaded_datasets:
                # Context-aware suggestions based on entity mentioned
                suggestions = [
                    f"How many wins does {entity} have?",
                    f"Show me statistics about {entity}",
                    f"What is the performance of {entity}?",
                    f"List all matches involving {entity}"
                ]
            else:
                suggestions = [
                    f"What information would you like about {entity}?",
                    "Try asking 'How many...', 'What is...', or 'Show me...'"
                ]
            
            return QueryResponse(
                success=False,
                error={
                    "message": f"I understand you're asking about '{entity}', but I need more details. What would you like to know?",
                    "code": "VAGUE_QUESTION",
                    "suggestions": suggestions
                }
            )
        
        # Get schema info (either from DB or uploaded CSV)
        schema_context = None
        active_table = request.dataset
        
        if request.use_uploaded_data and request.session_id in uploaded_datasets:
            df = uploaded_datasets[request.session_id]
            # Build schema context from DataFrame
            columns_info = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                sample_val = df[col].iloc[0] if len(df) > 0 else None
                columns_info.append(f"  - {col} ({dtype})")
            schema_context = {
                "table_name": "dataset",
                "columns": list(df.columns),
                "schema_text": f"Table: dataset\nColumns:\n" + "\n".join(columns_info),
                "row_count": len(df)
            }
            active_table = "dataset"
            logger.info(f"Using uploaded CSV schema: {len(df.columns)} columns, {len(df)} rows")
        elif db_manager:
            # Use database schema for selected dataset
            table_schema = db_manager.get_schema_info(request.dataset)
            if table_schema and table_schema.get("columns"):
                columns_info = []
                for col in table_schema["columns"]:
                    columns_info.append(f"  - {col['column_name']} ({col['data_type']})")
                schema_context = {
                    "table_name": request.dataset,
                    "columns": [col["column_name"] for col in table_schema["columns"]],
                    "schema_text": f"Table: {request.dataset}\nColumns:\n" + "\n".join(columns_info),
                    "row_count": len(table_schema.get("sample_data", []))
                }
                logger.info(f"Using database schema ({request.dataset} table)")
            else:
                schema_context = db_manager.get_schema_info()
                logger.info(f"Using database schema (default table)")
        else:
            logger.error("No data source available - neither CSV uploaded nor database connected")
            return QueryResponse(
                success=False,
                error={
                    "message": "No data source available. Please upload a CSV file to analyze.",
                    "code": "NO_DATA_SOURCE",
                    "suggestions": ["Click the + button to upload a CSV file"]
                }
            )
        
        # Step 2: Generate SQL
        sql_result = await sql_agent.generate(rewritten_question, schema_override=schema_context)
        sql_query = sql_result["sql"]
        sql_source = sql_result["source"]
        
        logger.info(f"Generated SQL from {sql_source}: {sql_query[:100]}...")
        
        # Step 3: Validate SQL
        # Set allowed tables based on data source
        if request.use_uploaded_data:
            sql_validator.ALLOWED_TABLES = {'dataset'}
        else:
            # Allow all database tables
            sql_validator.ALLOWED_TABLES = set(db_manager.get_table_list()) if db_manager else {active_table}
        
        validation = sql_validator.validate(sql_query)
        
        if not validation["valid"]:
            logger.warning(f"SQL validation failed: {validation['error']}")
            return QueryResponse(
                success=False,
                error={
                    "message": "I couldn't generate a safe query for that question. Please try rephrasing.",
                    "code": "SQL_VALIDATION_FAILED",
                    "details": validation["error"],
                    "suggestions": get_suggestions()
                }
            )
        
        validated_sql = validation["modified_sql"]
        
        # Step 4: Execute query (DB or CSV)
        try:
            if request.use_uploaded_data and request.session_id in uploaded_datasets:
                # Query uploaded CSV data with DuckDB
                logger.info(f"Executing query on uploaded CSV (session: {request.session_id})")
                df = uploaded_datasets[request.session_id]
                conn = duckdb.connect(":memory:")
                conn.register('dataset', df)
                
                # Replace any table name in SQL with 'dataset'
                csv_sql = validated_sql
                for table in db_manager.get_table_list() if db_manager else []:
                    csv_sql = csv_sql.replace(table, 'dataset')
                logger.info(f"CSV SQL: {csv_sql}")
                
                result = conn.execute(csv_sql).fetchdf()
                
                # Replace NaN/Inf values with None for JSON compatibility
                result = result.replace({float('nan'): None, float('inf'): None, float('-inf'): None})
                
                data = result.to_dict('records')
                conn.close()
                
                logger.info(f"CSV query returned {len(data)} rows")
            else:
                # Query Neon database
                logger.info(f"Executing query on database (superstore table)")
                if not db_manager:
                    raise HTTPException(status_code=500, detail="Database not available. Please upload a CSV file.")
                data = await db_manager.execute_query(validated_sql, timeout=30)
                logger.info(f"Database query returned {len(data)} rows")
                
        except Exception as e:
            error_msg = sql_validator.sanitize_error(e)
            logger.error(f"Query execution failed: {e}")
            return QueryResponse(
                success=False,
                error={
                    "message": error_msg,
                    "code": "QUERY_EXECUTION_FAILED",
                    "suggestions": get_suggestions()
                }
            )
        
        logger.info(f"Query returned {len(data)} rows")
        
        # Step 5 & 6: Run analysis and visualization in parallel
        analysis_task = analysis_agent.analyze(rewritten_question, validated_sql, data)
        viz_task = viz_agent.suggest_chart(rewritten_question, data)
        
        analysis_result, viz_result = await asyncio.gather(analysis_task, viz_task)
        
        # Determine overall confidence
        confidence = "high" if sql_source == "sqlcoder-7b" and len(data) > 0 else "medium"
        if len(data) == 0:
            confidence = "low"
        
        # Build response
        response_data = {
            "session_id": session_id,
            "rewritten_question": rewritten_question,
            "used_context": used_context,
            "sql": validated_sql,
            "sql_source": sql_source,
            "data": data[:1000],  # Limit data sent to frontend
            "summary": analysis_result["summary"],
            "insights": analysis_result["insights"],
            "chart": viz_result,
            "confidence": confidence,
            "metadata": {
                "execution_time": 0.0,  # TODO: Add timing
                "row_count": len(data),
                "row_count_limited": len(data) > 1000
            }
        }
        
        # Save to session history
        session_manager.add_to_history(session_id, {
            "question": question,
            "rewritten": rewritten_question,
            "sql": validated_sql,
            "intent": "analytics"  # TODO: Add intent classification
        })
        
        return QueryResponse(success=True, data=response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return QueryResponse(
            success=False,
            error={
                "message": "An unexpected error occurred. Please try again.",
                "code": "INTERNAL_ERROR",
                "suggestions": get_suggestions()
            }
        )


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session"""
    history = session_manager.get_history(session_id, limit=10)
    return {
        "session_id": session_id,
        "history": history
    }


@app.get("/session/{session_id}/recent")
async def get_recent_questions(session_id: str):
    """Get recently asked questions for quick access"""
    questions = session_manager.get_recent_questions(session_id, limit=5)
    return {
        "session_id": session_id,
        "recent_questions": questions
    }


@app.get("/datasets")
async def get_datasets():
    """Get list of available datasets"""
    if not db_manager:
        return {"datasets": []}
    
    tables = db_manager.get_table_list()
    
    # Define dataset metadata
    dataset_info = {
        "superstore": {
            "name": "Superstore Sales",
            "description": "Retail sales data with orders, customers, and products",
            "icon": "🛒",
            "color": "blue",
            "row_count": 9994
        },
        "sales_data": {
            "name": "E-Commerce Sales",
            "description": "Online sales data with customer segments and regions",
            "icon": "📦",
            "color": "green",
            "row_count": 9994
        },
        "ipl_matches": {
            "name": "IPL Cricket",
            "description": "Indian Premier League match data and statistics",
            "icon": "🏏",
            "color": "orange",
            "row_count": 1169
        },
        "netflix_titles": {
            "name": "Netflix Titles",
            "description": "Movies and TV shows available on Netflix",
            "icon": "🎬",
            "color": "red",
            "row_count": 8807
        },
        "world_population": {
            "name": "World Population",
            "description": "Population data by country from 1970 to 2022",
            "icon": "🌍",
            "color": "purple",
            "row_count": 234
        }
    }
    
    datasets = []
    for table in tables:
        info = dataset_info.get(table, {
            "name": table.replace('_', ' ').title(),
            "description": f"Data from {table}",
            "icon": "📊",
            "color": "gray",
            "row_count": 0
        })
        datasets.append({
            "table_name": table,
            **info
        })
    
    return {"datasets": datasets}


@app.get("/suggestions")
async def get_suggestion_questions(dataset: str = "superstore"):
    """Get suggested sample questions based on selected dataset"""
    
    suggestions_map = {
        "superstore": {
            "trending": [
                "Which region has the highest total sales?",
                "Top 10 most profitable products",
                "Show monthly sales trend from 2014 to 2017",
                "How does discount affect profit margins?",
                "What is the average order value by customer segment?",
                "Which shipping mode is most commonly used?"
            ],
            "suggested": [
                "Compare sales across all product categories",
                "Which sub-categories are loss-making?",
                "Top 5 states by revenue",
                "Best-selling products in Technology category",
                "Average profit margin by region"
            ]
        },
        "sales_data": {
            "trending": [
                "What is the total sales revenue?",
                "Which country has the highest sales?",
                "Top 10 customers by order value",
                "Compare sales across different segments",
                "Which products have the highest profit margins?"
            ],
            "suggested": [
                "Show sales by region",
                "Average discount per category",
                "Which shipping method is most used?",
                "Monthly sales trends",
                "Top 5 cities by revenue"
            ]
        },
        "ipl_matches": {
            "trending": [
                "Which team won the most matches?",
                "How many total matches are there?",
                "Show match winners by season",
                "Which player won the most 'Player of Match' awards?",
                "What is the toss decision trend?",
                "Which venue hosted the most matches?"
            ],
            "suggested": [
                "Count matches by team",
                "Show all team names",
                "Which team wins most after winning toss?",
                "List all venues",
                "Matches per city"
            ]
        },
        "netflix_titles": {
            "trending": [
                "How many movies vs TV shows?",
                "Which country produces the most content?",
                "Top 10 directors by number of titles",
                "What are the most common ratings?",
                "Show content added by year",
                "Which genres are most popular?"
            ],
            "suggested": [
                "List all movie ratings",
                "Count titles by type",
                "Show recent additions",
                "Top actors/cast members",
                "Content by country"
            ]
        },
        "world_population": {
            "trending": [
                "Which country has the highest population in 2022?",
                "Top 10 most populated countries",
                "Compare population growth rates",
                "Show population by continent",
                "Which countries have declining populations?",
                "Population density rankings"
            ],
            "suggested": [
                "List all continents",
                "Show Asian countries population",
                "Compare 2022 vs 2000 population",
                "Countries with largest growth",
                "Population per capita trends"
            ]
        }
    }
    
    return suggestions_map.get(dataset, suggestions_map["superstore"])


@app.get("/dataset/{table_name}/preview")
async def get_dataset_preview(table_name: str, limit: int = 100):
    """Get preview of dataset"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        # Validate table name to prevent SQL injection
        valid_tables = db_manager.get_table_list()
        if table_name not in valid_tables:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        # Get total row count
        count_result = await db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        total_rows = count_result[0]["count"] if count_result else 0
        
        # Get data preview
        data = await db_manager.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
        schema = db_manager.get_schema_info(table_name)
        columns = [col["column_name"] for col in schema.get("columns", [])]
        
        # Convert data to rows format (list of lists)
        rows = [[row.get(col, '') for col in columns] for row in data]
        
        return {
            "table_name": table_name,
            "rows": rows,
            "columns": columns,
            "total_rows": total_rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session"""
    session_manager.clear_session(session_id)
    return {"message": "Session cleared"}


def get_suggestions() -> List[str]:
    """Get helpful question suggestions for error messages"""
    return [
        "Which region has the highest sales?",
        "Top 10 most profitable products",
        "Show sales trend over time",
        "Compare performance by customer segment",
        "What are the loss-making products?"
    ]


# Mount static files (frontend)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}"
            }
        }
    )


@app.get("/api/chatbot-config")
async def get_chatbot_config():
    """Get chatbot configuration (API key from environment)"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="Groq API key not configured")
    
    return {
        "groqApiKey": groq_api_key,
        "groqModel": "llama-3.3-70b-versatile"
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "An internal error occurred. Please try again later.",
                "code": "INTERNAL_SERVER_ERROR"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        reload=False
    )
