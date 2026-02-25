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

SYSTEM_PROMPT = f"""You are a helpful and concise medical question-answering assistant.
Your goal is to provide accurate information based on the medical context you retrieve using your tools.

Guidelines:
- Use only the provided context from the 'get_medical_context' tool to answer. 
- If the tool doesn't return relevant information, clearly state that you don't know based on the available information.
- Provide answers that are at most 3-4 sentences.
- Use clear, simple, and professional language.
- If the query is serious, include a reminder to consult a healthcare professional WITHIN your answer text, NOT after the sources.

IMPORTANT - Citation Rules:
- The context returned by the tool includes page numbers in the format [Page X].
- You MUST always include citations at the VERY END of your response, as the absolute last thing. Nothing should come after the citations.
- Use this EXACT format:

📖 Sources:
- {SOURCE_BOOK}, Page X
- {SOURCE_BOOK}, Page Y

- List every unique page number that contributed to your answer.
- The citation block MUST be the last thing in your response. Do NOT write anything after it.
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
    The returned context includes page numbers for citation purposes.
    """
    try:
        if _db:
            retriever = _db.as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(question)
            if not docs:
                return "No relevant medical context found in the database."
            
            # Build context with page citations
            chunks = []
            for doc in docs:
                page_num = doc.metadata.get("page", "unknown")
                # page is 0-indexed from PyPDF, so add 1 for human-readable
                if isinstance(page_num, int):
                    page_num = page_num + 1
                source = doc.metadata.get("source", "unknown")
                chunk_text = f"[Page {page_num}]\n{doc.page_content}"
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
        
        # Strip inline [Page X] markers from the answer body (they're shown in the citation card)
        # Only remove them from the text BEFORE the "📖 Sources:" block
        parts = content.split('📖 Sources:')
        if len(parts) == 2:
            cleaned_body = re.sub(r'\s*\[Page \d+\]', '', parts[0]).strip()
            content = cleaned_body + '\n\n📖 Sources:' + parts[1]
        else:
            content = re.sub(r'\s*\[Page \d+\]', '', content).strip()
        
        return content
        
    except Exception as e:
        error = CustomException("Agent processing failed", e)
        logger.error(str(error))
        return f"I'm sorry, I'm having trouble processing that request. (Error: {str(e)})"
