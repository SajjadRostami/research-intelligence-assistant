# Semantic Scholar Adapter Implementation

## Overview

The `SemanticScholarAdapter` is a search adapter that queries the [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/) to retrieve scientific papers. It implements the `SearchAdapter` interface and returns structured paper metadata as `RawSourceItem` objects.

## Features

✅ **Free API Access**: No API key required (but rate limits apply)  
✅ **Comprehensive Metadata**: Extracts title, authors, abstract, DOI, publication date  
✅ **Error Handling**: Gracefully handles API failures, network errors, and rate limits  
✅ **Type Safety**: Fully typed with Python type hints  
✅ **Well Tested**: 14 unit tests with mocked responses + live test script  

## Files Created

### 1. Adapter Implementation
**File**: `ria/adapters/semantic_scholar.py`

Implements the `SemanticScholarAdapter` class with:
- `search(query, max_results)` - Main search method
- `_build_search_params()` - Constructs API query parameters
- `_parse_paper_result()` - Parses individual paper results

### 2. Unit Tests
**File**: `tests/unit/test_semantic_scholar.py`

14 comprehensive unit tests covering:
- Initialization (default and custom parameters)
- Query parameter construction
- Successful searches with full/partial/minimal data
- Empty results
- HTTP errors (500, 429 rate limit)
- Network errors
- Edge cases (missing fields, long abstracts)

### 3. Live Test Script
**File**: `test_semantic_scholar_live.py`

Executable script that performs a real API search and displays results.

### 4. Module Export
**File**: `ria/adapters/__init__.py` (updated)

Added `SemanticScholarAdapter` to the public API exports.

## Usage

### Basic Usage

```python
from ria.adapters.semantic_scholar import SemanticScholarAdapter

# Initialize adapter (no API key required)
adapter = SemanticScholarAdapter()

# Search for papers
results = await adapter.search("XPBD soft body simulation algorithm", max_results=10)

# Process results
for paper in results:
    print(f"Title: {paper.title}")
    print(f"Authors: {paper.author_or_assignee}")
    print(f"DOI: {paper.doi}")
    print(f"URL: {paper.source_url}")
```

### Custom Configuration

```python
adapter = SemanticScholarAdapter(
    base_url="https://api.semanticscholar.org/graph/v1",
    timeout=60.0  # Request timeout in seconds
)
```

## Data Extracted

The adapter extracts the following fields from each paper:

| Field | Source | Type | Description |
|-------|--------|------|-------------|
| `title` | `title` | str | Paper title (required) |
| `source_type` | - | SourceType.PAPER | Always "paper" |
| `source_url` | `url` or constructed | str | Link to Semantic Scholar page |
| `publication_date` | `publicationDate` or `year` | str | Publication date or year |
| `author_or_assignee` | `authors[].name` | str | Comma-separated author names |
| `doi` | `externalIds.DOI` | str | Digital Object Identifier |
| `relevance_explanation` | `abstract` | str | First 200 chars of abstract |
| `confidence_level` | - | ConfidenceLevel.HIGH | Always "High" (direct from API) |
| `raw_adapter_source` | - | str | Always "semantic_scholar" |

## Running Tests

### Unit Tests (Mocked)

Run all unit tests with mocked API responses:

```bash
python -m pytest tests/unit/test_semantic_scholar.py -v
```

Expected output:
```
tests/unit/test_semantic_scholar.py::TestSemanticScholarAdapter::test_initialization_defaults PASSED
tests/unit/test_semantic_scholar.py::TestSemanticScholarAdapter::test_initialization_custom PASSED
...
============================== 14 passed in 0.18s ==============================
```

### Live Test (Real API)

⚠️ **Important**: The Semantic Scholar API has rate limits:
- **100 requests per 5 minutes per IP address**
- If you exceed this, you'll get HTTP 429 errors

Run the live test:

```bash
python test_semantic_scholar_live.py
```

Or make it executable first:

```bash
chmod +x test_semantic_scholar_live.py
./test_semantic_scholar_live.py
```

**Expected Output** (successful):

```
================================================================================
Semantic Scholar Adapter - Live Test
================================================================================

ℹ️  Note: Semantic Scholar API is free (no API key required)
   Rate limit: 100 requests per 5 minutes per IP address

✅ Adapter initialized successfully
📝 Query: 'XPBD soft body simulation algorithm'
📊 Requesting: 10 results

--------------------------------------------------------------------------------

Found 10 paper(s):

================================================================================
Result #1
================================================================================
Title:            XPBD: Position-Based Simulation of Compliant Constrained Dynamics
Authors:          Miles Macklin, Matthias Müller
Publication Date: 2016-07-01
DOI:              10.1145/2994258.2994272
URL:              https://www.semanticscholar.org/paper/...
Source Type:      paper
Adapter:          semantic_scholar
Confidence:       High
Abstract:         We present an extension of Position Based Dynamics...

...
```

**If Rate Limited**:

```
================================================================================
Semantic Scholar Adapter - Live Test
================================================================================

✅ Adapter initialized successfully
📝 Query: 'XPBD soft body simulation algorithm'
📊 Requesting: 10 results

⚠️  No results returned
```

This is expected behavior if you've made too many requests recently. The adapter handles this gracefully by:
1. Logging the error
2. Returning an empty list
3. Not crashing the application

**Solution**: Wait 5 minutes and try again.

## API Rate Limits

The Semantic Scholar API enforces rate limits:

- **100 requests per 5 minutes** per IP address
- **No authentication required** (public access)
- **Recommended**: Add delays between requests in production

The adapter does **not** implement automatic rate limiting or exponential backoff. For production use, consider:

1. **Caching results** to avoid repeated queries
2. **Adding delays** between requests (e.g., `await asyncio.sleep(1)`)
3. **Monitoring HTTP 429 errors** and backing off appropriately
4. **Using Semantic Scholar's Partner API** for higher limits (requires partnership)

## Error Handling

The adapter handles the following error scenarios:

| Error Type | HTTP Code | Behavior |
|------------|-----------|----------|
| Rate limit exceeded | 429 | Log error, return empty list |
| Server error | 500 | Log error, return empty list |
| Not found | 404 | Log error, return empty list |
| Network timeout | - | Log error, return empty list |
| Connection error | - | Log error, return empty list |
| Invalid JSON | - | Log error, return empty list |

All errors are logged and handled gracefully - the adapter **never raises exceptions** from the `search()` method.

## Integration Example

To integrate with the research orchestrator:

```python
from ria.adapters import SemanticScholarAdapter
from ria.orchestrator import SearchOrchestrator

# Initialize adapter
semantic_scholar = SemanticScholarAdapter()

# Add to orchestrator
orchestrator = SearchOrchestrator()
orchestrator.add_adapter("papers", semantic_scholar)

# Search across all adapters
results = await orchestrator.search("XPBD algorithm")
```

## API Documentation

For complete API documentation, see:
- [Semantic Scholar API Docs](https://api.semanticscholar.org/)
- [Paper Search Endpoint](https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_paper_search)

## Comparison with Other Adapters

| Adapter | Source Type | API Key Required | Rate Limit | Status |
|---------|-------------|------------------|------------|--------|
| `SemanticScholarAdapter` | Paper | ❌ No | 100/5min | ✅ Active |
| `SerpAPIPatentAdapter` | Patent | ✅ Yes | Varies | ✅ Active |
| `GooglePatentsAdapter` | Patent | ❌ No | Unknown | ⚠️ Deprecated |
| `PatentsViewAdapter` | Patent | ❌ No | - | ❌ Shut down |
| `MockPatentAdapter` | Patent | ❌ No | None | 🧪 Testing only |

## Future Enhancements

Potential improvements for future versions:

1. **Rate Limiting**: Add exponential backoff for HTTP 429 errors
2. **Pagination**: Support fetching more than 100 results
3. **Field Selection**: Allow custom field selection
4. **Filtering**: Add filters for publication year, venue, citation count
5. **Caching**: Cache results to reduce API calls
6. **Bulk Queries**: Support batch paper lookups by DOI/ArXiv ID

## License

This implementation follows the same license as the main project.

---

**Implementation Date**: June 17, 2026  
**API Version**: Semantic Scholar Graph API v1  
**Status**: ✅ Production Ready
