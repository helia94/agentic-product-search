"""
FastAPI backend for unified search across multiple services.

This module exposes a single `/search` endpoint that accepts a plain
`query` string and a list of `models` indicating which search providers
should be queried. Each provider is implemented as its own asynchronous
function to keep network I/O non‑blocking. Supported models include:

* `exa_search` – Use Exa's search API to retrieve links and summaries.
* `exa_answer` – Use Exa's answer API to ask for a synthesized answer with citations.
* `google_custom` – Use Google’s Custom Search JSON API for classic keyword search.
* `gemini_search` – Call Google Generative AI’s `generateContent` with the
  `google_search` tool enabled to ground the response in live web results.
* `openai_search` – Use OpenAI’s Responses API with the `web_search_preview` tool.
* `browser` – Perform a rudimentary scrape of Google’s public search
  results. This is provided for completeness but should be used sparingly as it
  does not respect Google’s terms of service. In production you should
  integrate a proper scraping API instead of hitting google.com directly.

Each provider reads its API key and other configuration from environment
variables. See the accompanying `.env` file for names of variables that need
to be populated before running the service.

The `/search` endpoint returns a JSON object keyed by the provider name. Each
value contains whatever raw data was returned by the underlying API. Errors
are captured and reported rather than raised.

"""

import os
from typing import List, Dict, Any
import json

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from bs4 import BeautifulSoup


# Load environment variables from a .env file if present. Developers
# can create a `.env` file based on the provided template (see
# `.env` in this repository) and populate the API keys. The `dotenv`
# package will quietly ignore missing files.
load_dotenv()

app = FastAPI(title="Unified Search API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://127.0.0.1:5500"] if hosted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    """Incoming request schema for the search endpoint."""
    query: str = Field(..., description="Search string to run across providers")
    models: List[str] = Field(..., description="List of provider names to query")


async def exa_search(query: str, num_results: int = 5, search_type: str = "neural") -> Any:
    """Call Exa's search endpoint.

    According to Exa’s API documentation, the `/search` endpoint accepts
    a JSON payload with at least a `query` field and optional fields
    such as `type` (neural/keyword/auto), `category`, `numResults`, and
    `text` to include full page text【645406731712684†L150-L173】. We include
    `text: True` so that the returned objects contain excerpts. The API
    key is passed via the `x-api-key` header【985342716872†L77-L84】.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY is not set in the environment")
    headers = {"x-api-key": api_key}
    payload = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
        "text": True,
    }
    url = "https://api.exa.ai/search"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"error": str(exc)}
    return data


async def exa_answer(query: str) -> Any:
    """Call Exa's answer endpoint to obtain a concise answer with citations.

    The `/answer` endpoint expects a JSON body with a `query` and
    optional `text` and `stream` parameters and returns an object
    containing `answer` and `citations`【535166016557528†L77-L83】.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY is not set in the environment")
    headers = {"x-api-key": api_key}
    payload = {
        "query": query,
        "text": True,
        "stream": False,
    }
    url = "https://api.exa.ai/answer"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            return {"error": str(exc)}
    return data


async def google_custom_search(query: str, num_results: int = 5) -> Any:
    """Perform a Google Custom Search using the JSON API.

    Google’s Custom Search JSON API requires an API key and a search
    engine ID (CX). The documentation states that the API provides
    100 free queries per day and charges $5 per 1,000 queries thereafter【346974713598932†L124-L134】.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")
    if not (api_key and cx):
        raise ValueError("GOOGLE_API_KEY or GOOGLE_CX is not set in the environment")
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": num_results,
    }
    url = "https://www.googleapis.com/customsearch/v1"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"error": str(exc)}
    return data


async def gemini_search(query: str, model: str = "models/gemini-2.5-flash") -> Any:
    """Use Google Generative AI to call Gemini with the google_search tool.

    The `generateContent` method with the `google_search` tool attaches
    live web results to the model response【841774432896565†L256-L371】. Billing
    is per API call with a free tier of 500 requests/day and $35 per
    1k calls afterwards for many models【671167997998555†L286-L306】.
    The API key is supplied via the query parameter `key` rather than
    using an authorization header.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in the environment")
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": query}],
            }
        ],
        "tools": [{"google_search": {}}],
    }
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"error": str(exc)}
    return data


async def openai_search(query: str, model: str = "gpt-4o") -> Any:
    """Call OpenAI’s Responses API with the `web_search_preview` tool.

    See the Medium article for an example that passes `model`, `input`
    and a `tools` array containing `{"type": "web_search_preview"}`【241281194709960†L68-L80】.
    Additional options like `search_context_size` or `user_location`
    can be supplied; here we leave them empty to use defaults.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment")
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": query,
        "tools": [
            {
                "type": "web_search_preview",
            }
        ],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"error": str(exc)}
    return data

async def openai_gpt41_mini(query: str, model: str = "gpt-4.1-mini") -> Any:
    """Plain chat completion with OpenAI GPT-4.1-mini (no search)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    url = "https://api.openai.com/v1/chat/completions"          # :contentReference[oaicite:0]{index=0}
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    payload = {"model": model,
               "messages": [{"role": "user", "content": query}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        return r.json()

async def deepseek_llama_groq(query: str,
                              model: str = "deepseek-r1-distill-llama-70b") -> Any:
    """DeepSeek R1-Distill-Llama-70B-128k served by Groq (chat-only)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")
    url = "https://api.groq.com/openai/v1/chat/completions"      # :contentReference[oaicite:1]{index=1}
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    payload = {"model": model,
               "messages": [{"role": "user", "content": query}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        return r.json()

async def grok3_mini(query: str, model: str = "grok-3-mini") -> Any:
    """xAI Grok-3-mini completion (no search)."""
    api_key = os.getenv("XAI_API_KEY")           # name it whatever you like
    if not api_key:
        raise ValueError("XAI_API_KEY is not set")
    url = "https://api.x.ai/v1/chat/completions"                    # :contentReference[oaicite:2]{index=2}
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    payload = {"model": model,
               "messages": [{"role": "user", "content": query}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        return r.json()
    


async def browser_scrape(query: str, num_results: int = 5) -> Any:
    """Perform a simple scrape of Google’s public search results page.

    This function fetches the HTML of a Google search results page and
    parses it using BeautifulSoup to extract titles and URLs. It uses
    a custom User‑Agent header to mimic a browser. Note that scraping
    Google results directly may violate Google’s terms of service and is
    provided here for demonstration only. You should use an official API
    like Google Custom Search in production.
    """
    params = {"q": query, "num": num_results}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    }
    url = "https://www.google.com/search"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            html = response.text
        except Exception as exc:
            return {"error": str(exc)}
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select("div.g"):
        link = item.find("a")
        title = item.find("h3")
        if link and title:
            results.append({"title": title.get_text(), "url": link.get("href")})
        if len(results) >= num_results:
            break
    return {"results": results}

@app.get("/")
def index():
    return {"msg": "Backend is running"}


@app.post("/search")
async def unified_search(request: SearchRequest) -> Dict[str, Any]:
    """Unified search endpoint.

    Loops through the requested models, dispatches the appropriate
    asynchronous function for each provider, and collates responses
    into a dictionary keyed by provider name. Unknown model names are
    returned with an error entry.
    """
    responses: Dict[str, Any] = {}
    providers = {
        "exa_search": exa_search,
        "exa_answer": exa_answer,
        "google_custom": google_custom_search,
        "gemini_search": gemini_search,
        "openai_search": openai_search,
        "browser": browser_scrape,
        "openai_gpt41_mini": openai_gpt41_mini,
        "deepseek_llama_groq": deepseek_llama_groq,
        "grok3_mini": grok3_mini,
    }
    for model in request.models:
        func = providers.get(model)
        if func is None:
            responses[model] = {"error": f"Unknown model '{model}'"}
            continue
        try:
            result = await func(request.query)
            responses[model] = result
        except Exception as exc:
            responses[model] = {"error": str(exc)}
    return responses