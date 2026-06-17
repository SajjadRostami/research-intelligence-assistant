"""
Search adapters for patent and academic paper sources.

Each adapter implements the SearchAdapter interface and handles
source-specific query construction, HTTP requests, and result parsing.
"""

from ria.adapters.base import SearchAdapter
from ria.adapters.google_patents import GooglePatentsAdapter

__all__ = ["SearchAdapter", "GooglePatentsAdapter"]
