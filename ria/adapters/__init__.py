"""
Search adapters for patent and academic paper sources.

Each adapter implements the SearchAdapter interface and handles
source-specific query construction, HTTP requests, and result parsing.
"""

from ria.adapters.base import SearchAdapter
from ria.adapters.google_patents import GooglePatentsAdapter
from ria.adapters.mock_patent import MockPatentAdapter
from ria.adapters.patentsview import PatentsViewAdapter
from ria.adapters.semantic_scholar import SemanticScholarAdapter
from ria.adapters.serpapi_patents import SerpAPIPatentAdapter

# GooglePatentsAdapter is deprecated - Google Patents renders results with JavaScript
# PatentsViewAdapter is deprecated - PatentsView API has been shut down (moved to USPTO)
# MockPatentAdapter is for MVP/testing - fallback for development
# SerpAPIPatentAdapter is the recommended production adapter for MVP
# SemanticScholarAdapter is the recommended adapter for academic papers

__all__ = [
    "SearchAdapter",
    "GooglePatentsAdapter",
    "PatentsViewAdapter",
    "MockPatentAdapter",
    "SerpAPIPatentAdapter",
    "SemanticScholarAdapter",
]
