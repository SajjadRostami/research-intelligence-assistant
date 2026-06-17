"""
Search adapters for patent and academic paper sources.

Each adapter implements the SearchAdapter interface and handles
source-specific query construction, HTTP requests, and result parsing.
"""

from ria.adapters.base import SearchAdapter
from ria.adapters.google_patents import GooglePatentsAdapter
from ria.adapters.mock_patent import MockPatentAdapter
from ria.adapters.patentsview import PatentsViewAdapter

# GooglePatentsAdapter is deprecated - Google Patents renders results with JavaScript
# PatentsViewAdapter is deprecated - PatentsView API has been shut down (moved to USPTO)
# MockPatentAdapter is for MVP/testing - replace with BigQuery or Lens.org for production

__all__ = [
    "SearchAdapter",
    "GooglePatentsAdapter",
    "PatentsViewAdapter",
    "MockPatentAdapter",
]
