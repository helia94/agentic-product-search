from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict


import operator
from dataclasses import dataclass, field
from pydantic import BaseModel, Field



class QueryBreakDown(BaseModel):
    """Breaks down a user query into components for structured search."""
    
    product: str = Field(description="The core product the user is interested in.")
    use_case: str = Field(description="The specific situation or purpose the product is meant to serve.")
    conditions: List[str] = Field(description="Constraints or filters like price, size, brand, etc.")
    other: str = Field(description="Anything else from the query not covered above.")

class QueryTips(BaseModel):
    """Provides metadata to guide the product search process based on the query context."""

    timeframe: str = Field(
        description="Relevant time period for search results. For fast-evolving products (e.g. AI tools), specify a recent timeframe like 'past year'; leave empty for stable products (e.g. dumbbells)."
    )
    sources: List[str] = Field(
        description="Recommended online sources where knowledgeable users discuss this product (e.g. Reddit, Amazon, Hacker News, price comparison sites)."
    )
    how_many: int = Field(
        description="Suggested number of products to show. Use higher numbers for undifferentiated or taste-driven products (e.g. shoes), lower for niche or clearly segmented ones (e.g. e-readers)."
    )
    potential_use_cases_to_clarify: List[str] = Field(
        description="Possible user segments or use cases not clearly specified in the query. Max 4 entries to clarify product intent (e.g. Travelers, Sleep Aid)."
    )

    reasoning: str = Field(
        description="Reasoning behind the tips provided, explaining how they are critical to the buying decision."
    )



class Criteria(TypedDict):
    buying_criteria: List[str] = Field(description ="List critical criteria to consider when buying a product.")

    reasoning: str = Field(
        description="Reasoning behind the tips provided, explaining how they are critical to the buying decision."
    )

class Queries(TypedDict):
    queries: List[str] = Field(
        description="List of queries to be used for searching products."
    )


class ProductSimple(TypedDict):
    id: str = Field(
        description="Unique identifier for the product, used for tracking and retrieval."
    )
    name: str = Field(
        description="Name of the product."
    )
    USP: str = Field(
        description="Unique Selling Proposition of the product."
    )
    use_case: str = Field(
        description="Primary use case for the product."
    )
    other_info: str = Field(
        description="Any other relevant information about the product."
    )


class ProductSimpleList(TypedDict):
    products: List[ProductSimple]
    reasoning: str = Field(
        description="Reasoning behind the selection of products, explaining how they meet the user's needs."
    )


class ProductFull(TypedDict):
    id: str = Field(
        description="Unique identifier for the product, used for tracking and retrieval."
    )
    name: str = Field(
        description="Fully unique name of the product including model, specifications, and other distinguishing features."
    )
    criteria: Dict[str, str] = Field(
        description="Dictionary of evaluation criteria for the product. Keys are criteria names, values are descriptions."
    )
    USP: str = Field(
        description="Unique Selling Proposition of the product."
    )
    use_case: str = Field(
        description="Primary use case for the product."
    )
    price: float = Field(
        description="Price of the product. Do not say it depends, price should be a specific number."
    )
    country: str = Field(
        description="Country where the product was design and produced. e.g. designed in Finland, produced in China."
    )
    year: int = Field(
        description="Year of the product release."
    )
    review_summary: str = Field(
        description="Summary of user reviews for the product. short keyword style, only informative words, no generic phrases like 'good product' or 'bad product'."
    )
    rating: str = Field(
        description="User rating for the product. combination of rating and platform name (e.g. 4.5/5 on Amazon, 8.7/10 on TechRadar)."
    )
    reviews_count: str = Field(
        description="Number of reviews for the product. This should be a specific number, not a range or estimate."
    )
    image_url: List[str] = Field(
        description="List of URLs of the product image. At least one image URL is required. Max 3 URLs. Preferably from the official product page or a reputable retailer."
    )
    product_url: str = Field(
        description="A url for the retailer offering the product in the given country. make sure the product is available for purchase in the given country. If not available, return original product_url with a warning."
    )

class OverallState(TypedDict):
    user_query: str
    country: str
    query_breakdown: QueryBreakDown
    query_tips: QueryTips
    criteria: List[str]
    queries: List[str]
    explored_products: List[ProductSimple]
    researched_products: List[str]
    completed_products: List[ProductFull]
    selected_product_ids: List[str]
    selected_products: List[ProductFull]
    selected_criteria: Criteria
    html_report: str
    max_explore_products: int
    max_research_products: int
    max_explore_queries: int