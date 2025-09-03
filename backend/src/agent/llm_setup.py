import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain.globals import set_debug

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")

set_debug(True)

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.2,  # 1 request every 5 seconds
    check_every_n_seconds=0.1,
    max_bucket_size=1  # No burst requests
)

# Model class definitions
FAST_MODEL = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=None,
    max_retries=10,
)

BALANCED_MODEL = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
#    rate_limiter=rate_limiter,
)


SMART_MODEL = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    max_retries=10,
#    rate_limiter=rate_limiter,
)

CREATIVE_MODEL =  ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=0.3,
    max_tokens=None,
    timeout=None,
    max_retries=10,
)

#BALANCED_MODEL = FAST_MODEL
#CREATIVE_MODEL = FAST_MODEL



# LLM invocation mapping dictionary
LLM_MAPPING = {
    # Query processing - need balanced performance
    "query_breakdown": BALANCED_MODEL,
    "query_tips": SMART_MODEL,
    "use_case_selection": SMART_MODEL,
    "buying_criteria": SMART_MODEL,
    
    # Query generation - creative task
    "query_generation": CREATIVE_MODEL,
    
    # Search and exploration - need smart reasoning
    "product_exploration": FAST_MODEL,
    "tool_call_analysis": FAST_MODEL,
    "search_query_generation": SMART_MODEL,
    "search_result_analysis": FAST_MODEL,
    
    # Result processing - need accuracy
    "product_selection": SMART_MODEL,
    "final_product_info": FAST_MODEL,
    "json_fixing": FAST_MODEL,
    
    # HTML generation - creative formatting
    "html_generation": FAST_MODEL,
    
    # Pattern-based search
    "search_pattern": FAST_MODEL,
    "pattern_tool_calls": SMART_MODEL,
    "pattern_final_result": FAST_MODEL,
}

def get_llm(key: str):
    """Get LLM instance for a specific use case."""
    return LLM_MAPPING.get(key, BALANCED_MODEL)  # Default to balanced model

# Backward compatibility
llm_llama3 = FAST_MODEL
llm_gemini = BALANCED_MODEL