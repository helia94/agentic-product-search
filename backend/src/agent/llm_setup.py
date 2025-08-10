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

llm_llama3 = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
    rate_limiter=rate_limiter,
)