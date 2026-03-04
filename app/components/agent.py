from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
import re
import os

from app.components.vector_store import load_vector_store
from app.common.logger import get_logger
from app.common.custom_exception import CustomException
from app.config.config import GROQ_QWEN_MODEL

logger = get_logger(__name__)

# Source book name for citations
SOURCE_BOOK = "The GALE Encyclopedia of Medicine, 2nd Edition"

SYSTEM_PROMPT = f"""You are a medical assistant. Answer ONLY using text from the 'get_medical_context' tool. Never use your own knowledge.

RULES:
- If the retrieved chunks are NOT about the question's topic, refuse to answer.
- If you can answer, keep it to 3-4 sentences. Add a reminder to consult a doctor for serious topics.
- Use EXACT page numbers from the context (format: [Page XXX | Confidence: YY%]). Pages are 625+.

End every response with:
📖 Sources:
- {SOURCE_BOOK}, Page X
🎯 Confidence: XX% (average of cited pages only)
"""


# Initialize core components
try:
    _db = load_vector_store()
except Exception as e:
    logger.error(f"Failed to load vector store: {str(e)}")
    _db = None

_checkpointer = InMemorySaver()

@tool
def get_medical_context(question: str) -> str:
    """Retrieve relevant medical information from the knowledge base for a specific question. 
    Use this tool whenever a medical question is asked to find factual ground truth.
    The returned context includes page numbers and confidence scores for citation purposes.
    """
    try:
        if _db:
            # Use similarity_search_with_score to get L2 distances
            results = _db.similarity_search_with_score(question, k=3)
            if not results:
                return "No relevant medical context found in the database."
            
            # Build context with page citations and confidence scores
            chunks = []
            for doc, l2_distance in results:
                # page metadata is now the real printed page label (e.g. "625")
                page_num = doc.metadata.get("page", "unknown")
                # Convert L2 distance to confidence percentage
                # Lower L2 distance = higher confidence
                confidence = round((1 / (1 + l2_distance)) * 100)
                logger.info(f"Retrieved chunk: Page {page_num}, L2 distance: {l2_distance:.4f}, Confidence: {confidence}%")
                chunk_text = f"[Page {page_num} | Confidence: {confidence}%]\n{doc.page_content}"
                chunks.append(chunk_text)
            
            return "\n\n---\n\n".join(chunks)
        return "The medical knowledge base is currently unavailable."
    except Exception as e:
        logger.error(f"Error in context retrieval tool: {str(e)}")
        return f"Error retrieving medical context: {str(e)}"

# Initialize the model using the new init_chat_model API
_model = init_chat_model(
    model=GROQ_QWEN_MODEL,
    model_provider="groq",
    temperature=0
)

# Create the agent using the modern create_agent factory
_agent = create_agent(
    model=_model,
    tools=[get_medical_context],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer
)

def get_agent_response(user_message: str) -> str:
    """Invoke the agent and return the assistant response."""
    try:
        # Use a consistent thread_id for conversation memory
        # In a multi-user app, this would ideally come from the session ID
        config = {"configurable": {"thread_id": "medical_rag_session"}}
        
        # Invoke the agent with the user message
        result = _agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config
        )
        
        # Extract content from the last message in the response
        content = ""
        if isinstance(result, dict) and "messages" in result:
            content = result["messages"][-1].content
        elif hasattr(result, "content"):
            content = result.content
        else:
            content = str(result)
            
        # Manually strip <thought>...</thought> tags if they appear in the model output
        content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL).strip()
        
        # Strip inline [Page X] and [Page X | Confidence: Y%] markers from the answer body
        # Only remove them from the text BEFORE the "📖 Sources:" block
        parts = content.split('📖 Sources:')
        if len(parts) == 2:
            cleaned_body = re.sub(r'\s*\[Page \d+(?:\s*\|\s*Confidence:\s*\d+%)?\]', '', parts[0]).strip()
            content = cleaned_body + '\n\n📖 Sources:' + parts[1]
        else:
            content = re.sub(r'\s*\[Page \d+(?:\s*\|\s*Confidence:\s*\d+%)?\]', '', content).strip()
        
        return content
        
    except Exception as e:
        error = CustomException("Agent processing failed", e)
        logger.error(str(error))
        return f"I'm sorry, I'm having trouble processing that request. (Error: {str(e)})"
