"""
AGENT 1: Context Rewriter Agent

Purpose: Convert follow-up questions into standalone queries using session context.
Model: Groq LLaMA-3.3-70B Versatile
"""

import json
import logging
from typing import Dict, List, Optional
from groq import AsyncGroq
import os

logger = logging.getLogger(__name__)


class ContextRewriterAgent:
    """
    Rewrites follow-up questions into standalone questions using conversation history.
    
    Examples:
        - "What about last year?" → "Total sales for 2025"
        - "Only for West region" → "Total sales by region for West"
        - "Same but by category" → "Total sales by category"
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Context Rewriter Agent."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        logger.info(f"Context Rewriter initialized with model: {self.model}")
        
    def _build_context_string(self, history: List[Dict]) -> str:
        """Build a formatted context string from conversation history."""
        if not history:
            return "No previous context."
        
        context_lines = []
        for i, turn in enumerate(history[-5:], 1):  # Last 5 turns max
            context_lines.append(f"{i}. Q: {turn.get('question', '')}")
            if turn.get('rewritten'):
                context_lines.append(f"   Rewritten: {turn['rewritten']}")
            if turn.get('intent'):
                context_lines.append(f"   Intent: {turn['intent']}")
        
        return "\n".join(context_lines)
    
    def _build_prompt(self, question: str, history: List[Dict]) -> str:
        """Build the complete prompt for the LLM."""
        context = self._build_context_string(history)
        
        prompt = f"""You are a context rewriter for a business analytics system analyzing a Superstore dataset.

Database context:
- Table: superstore
- Contains: sales, profit, customers, products, regions, dates
- Time period: 2014-2017

Previous conversation:
{context}

Current follow-up question: "{question}"

Task: Rewrite this into a STANDALONE question that can be understood without previous context.

Rules:
1. Preserve ALL business terms (sales, profit, revenue, customers, products, regions, categories)
2. Infer missing details from conversation history
3. If the question is already standalone, return it as-is
4. If context is insufficient, ask for clarification
5. Keep the rewritten question concise and clear
6. Use proper business terminology

Output ONLY valid JSON in this exact format:
{{"rewritten_question": "your rewritten question here"}}

Examples:
- "What about last year?" → {{"rewritten_question": "Total sales for 2023"}}
- "Only for West" → {{"rewritten_question": "Total sales by region for West region"}}
- "Same by category" → {{"rewritten_question": "Total sales by product category"}}

Now rewrite the current question:"""
        
        return prompt
    
    async def rewrite(self, question: str, history: List[Dict] = None) -> Dict:
        """
        Rewrite a follow-up question into a standalone question.
        
        Args:
            question: The user's follow-up question
            history: List of previous conversation turns
            
        Returns:
            Dict with 'rewritten_question' and 'confidence'
        """
        history = history or []
        
        # If no history or question is already detailed, return as-is
        if not history or len(question.split()) > 8:
            logger.info(f"Question appears standalone: {question}")
            return {
                "rewritten_question": question,
                "confidence": "high",
                "used_context": False
            }
        
        try:
            prompt = self._build_prompt(question, history)
            
            logger.info(f"Rewriting question with context from {len(history)} previous turns")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise context rewriter. Output ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            rewritten = result.get("rewritten_question", question)
            
            logger.info(f"Rewritten: '{question}' → '{rewritten}'")
            
            # Determine confidence based on history usage
            confidence = "high" if len(history) > 0 else "medium"
            
            return {
                "rewritten_question": rewritten,
                "confidence": confidence,
                "used_context": True,
                "context_turns": len(history)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {
                "rewritten_question": question,
                "confidence": "low",
                "used_context": False,
                "error": "json_parse_error"
            }
        except Exception as e:
            logger.error(f"Context rewriting failed: {e}")
            return {
                "rewritten_question": question,
                "confidence": "low",
                "used_context": False,
                "error": str(e)
            }
    
    async def should_use_context(self, question: str) -> bool:
        """
        Determine if a question is a follow-up that needs context.
        
        Follow-up indicators:
        - Short questions (< 4 words)
        - Starts with: "what about", "only", "same", "and", "also"
        - Contains pronouns: "it", "that", "this", "there"
        """
        question_lower = question.lower().strip()
        words = question_lower.split()
        
        # Short questions likely need context
        if len(words) <= 3:
            return True
        
        # Follow-up phrase indicators
        follow_up_starters = [
            "what about", "only", "same", "and ", "also", "how about",
            "for ", "in ", "by ", "with ", "without "
        ]
        
        if any(question_lower.startswith(starter) for starter in follow_up_starters):
            return True
        
        # Pronoun indicators
        pronouns = ["it", "that", "this", "there", "them", "those", "these"]
        if any(pronoun in words for pronoun in pronouns):
            return True
        
        return False


# Example usage and testing
async def test_context_rewriter():
    """Test the Context Rewriter Agent"""
    agent = ContextRewriterAgent()
    
    # Test 1: No context
    result = await agent.rewrite("Total sales by region")
    print(f"Test 1 (no context): {result}")
    
    # Test 2: With context
    history = [
        {
            "question": "Total sales by region",
            "rewritten": "Total sales by region",
            "intent": "sales"
        }
    ]
    result = await agent.rewrite("What about last year?", history)
    print(f"Test 2 (with context): {result}")
    
    # Test 3: Complex follow-up
    history.append({
        "question": "What about last year?",
        "rewritten": "Total sales by region for 2023",
        "intent": "sales"
    })
    result = await agent.rewrite("Only for West", history)
    print(f"Test 3 (follow-up): {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_context_rewriter())
