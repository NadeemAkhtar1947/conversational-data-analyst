"""
Session management for conversation context.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions and conversation history.
    In-memory storage with TTL (can be extended to Redis for production scale).
    """
    
    def __init__(self, ttl_minutes: int = 60, max_history: int = 5):
        """
        Initialize Session Manager.
        
        Args:
            ttl_minutes: Session time-to-live in minutes
            max_history: Maximum number of queries to keep in history
        """
        self.sessions = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_history = max_history
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow(),
            "history": []
        }
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data by ID."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if expired
        if datetime.utcnow() - session["last_accessed"] > self.ttl:
            logger.info(f"Session expired: {session_id}")
            del self.sessions[session_id]
            return None
        
        # Update last accessed
        session["last_accessed"] = datetime.utcnow()
        return session
    
    def add_to_history(self, session_id: str, query_data: Dict):
        """
        Add a query to session history.
        
        Args:
            session_id: Session ID
            query_data: Dict containing question, rewritten, sql, intent, etc.
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot add to history: session {session_id} not found")
            return
        
        # Add timestamp
        query_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Add to history (keep only last N)
        session["history"].append(query_data)
        if len(session["history"]) > self.max_history:
            session["history"] = session["history"][-self.max_history:]
        
        logger.info(f"Added to history (session {session_id}): {query_data.get('question', '')[:50]}")
    
    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of history items to return
            
        Returns:
            List of query data dictionaries
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        history = session["history"]
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_recent_questions(self, session_id: str, limit: int = 5) -> List[str]:
        """
        Get list of recent questions for quick access.
        
        Args:
            session_id: Session ID
            limit: Number of questions to return
            
        Returns:
            List of question strings
        """
        history = self.get_history(session_id, limit)
        return [item.get("question", "") for item in history if "question" in item]
    
    def clear_session(self, session_id: str):
        """Clear a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
    
    def cleanup_expired(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session["last_accessed"] > self.ttl
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_stats(self) -> Dict:
        """Get session statistics."""
        return {
            "active_sessions": len(self.sessions),
            "total_queries": sum(len(s["history"]) for s in self.sessions.values())
        }


# Testing
def test_session_manager():
    """Test Session Manager"""
    manager = SessionManager(ttl_minutes=1, max_history=3)
    
    # Create session
    session_id = manager.create_session()
    print(f"Created session: {session_id}")
    
    # Add queries
    for i in range(5):
        manager.add_to_history(session_id, {
            "question": f"Question {i}",
            "rewritten": f"Rewritten {i}",
            "intent": "sales"
        })
    
    # Get history (should only have last 3 due to max_history=3)
    history = manager.get_history(session_id)
    print(f"History count: {len(history)} (should be 3)")
    
    # Get recent questions
    questions = manager.get_recent_questions(session_id)
    print(f"Recent questions: {questions}")
    
    # Stats
    stats = manager.get_stats()
    print(f"Stats: {stats}")


if __name__ == "__main__":
    test_session_manager()
