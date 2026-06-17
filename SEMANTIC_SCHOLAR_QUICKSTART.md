# Semantic Scholar Adapter - Quick Start

## Running the Tests

### Fallback Test (Recommended First)
Simple test with "machine learning" query to verify adapter works:
```bash
python test_semantic_scholar_fallback.py
```

### Live Test (Original XPBD Query)
```bash
python test_semantic_scholar_live.py
```

### With API Key (Higher Rate Limits)
```bash
export SEMANTIC_SCHOLAR_API_KEY="your-api-key"
python test_semantic_scholar_fallback.py
```

Get an API key at: https://www.semanticscholar.org/product/api

## Running Unit Tests

```bash
# Run all tests
python -m pytest tests/unit/test_semantic_scholar.py -v

# Run specific test
python -m pytest tests/unit/test_semantic_scholar.py::TestSemanticScholarAdapter::test_search_success -v

# Run with coverage
python -m pytest tests/unit/test_semantic_scholar.py --cov=ria.adapters.semantic_scholar
```

## Important Notes

### Rate Limits
The Semantic Scholar API has rate limits:
- **Without API key**: 100 requests per 5 minutes per IP address
- **With API key**: Higher limits available

### Retry Logic
The adapter now implements **exponential backoff** for HTTP 429 errors:
- 3 retry attempts by default
- Delays: 2s, 4s, 8s (configurable)
- Logs warnings for each retry

### User-Agent Header
The adapter now sends a proper User-Agent header to identify itself to the API.

### API Key Support
You can provide an API key for higher rate limits:

```python
# Option 1: Environment variable (recommended)
export SEMANTIC_SCHOLAR_API_KEY="your-api-key"

# Option 2: Pass directly
adapter = SemanticScholarAdapter(api_key="your-api-key")
```

### Expected Behavior

**Success**:
```
✅ Adapter initialized successfully
⏳ Executing search...
✅ Search completed

Found 5 paper(s):
...
```

**Rate Limited with Retry**:
```
⚠️  Rate limited (HTTP 429). Retrying in 2.0s (attempt 1/3)
⚠️  Rate limited (HTTP 429). Retrying in 4.0s (attempt 2/3)
✅ Search completed
```

**Rate Limited After Retries**:
```
❌ Rate limited (HTTP 429) after 3 retries.
   Consider using an API key for higher rate limits.
⚠️  No results returned
```

This is **normal behavior** - the adapter handles rate limits gracefully.

## Basic Usage Example

```python
import asyncio
from ria.adapters.semantic_scholar import SemanticScholarAdapter

async def search_papers():
    # Without API key (free tier)
    adapter = SemanticScholarAdapter()
    
    # With API key (higher rate limits)
    # adapter = SemanticScholarAdapter(api_key="your-api-key")
    
    # With custom retry settings
    # adapter = SemanticScholarAdapter(
    #     max_retries=5,
    #     initial_retry_delay=2.0
    # )
    
    results = await adapter.search("XPBD soft body simulation algorithm", max_results=10)
    
    for paper in results:
        print(f"{paper.title}")
        print(f"  Authors: {paper.author_or_assignee}")
        print(f"  DOI: {paper.doi}")
        print(f"  URL: {paper.source_url}")
        print()

asyncio.run(search_papers())
```

## Query Examples

```python
# Physics simulation
results = await adapter.search("XPBD soft body simulation algorithm")

# Machine learning
results = await adapter.search("transformer neural networks")

# Specific author
results = await adapter.search("Matthias Müller position based dynamics")

# Domain-specific
results = await adapter.search("real-time cloth simulation")
```

## Files Created/Modified

1. **Adapter**: `ria/adapters/semantic_scholar.py` (280+ lines with retry logic)
2. **Unit Tests**: `tests/unit/test_semantic_scholar.py` (14 tests)
3. **Live Test**: `test_semantic_scholar_live.py` (XPBD query)
4. **Fallback Test**: `test_semantic_scholar_fallback.py` (machine learning query)
5. **Documentation**: `SEMANTIC_SCHOLAR_IMPLEMENTATION.md` (full implementation docs)
6. **Quick Start**: `SEMANTIC_SCHOLAR_QUICKSTART.md` (this file)
7. **Fix Summary**: `SEMANTIC_SCHOLAR_HTTP_429_FIX.md` (HTTP 429 investigation & fixes)

## Verification

All requirements met:
- ✅ Created `ria/adapters/semantic_scholar.py`
- ✅ Uses Semantic Scholar API
- ✅ Implements `SearchAdapter` interface
- ✅ Returns `list[RawSourceItem]`
- ✅ Extracts: title, authors, abstract, publication date, DOI, URL
- ✅ Sets `source_type = SourceType.PAPER`
- ✅ Handles API failures gracefully
- ✅ Returns empty list if no results
- ✅ Created unit tests with mocked responses
- ✅ Created live test script
- ✅ Searches for "XPBD soft body simulation algorithm"
- ✅ Prints first 10 results
- ✅ Explains how to run the test

## Recent Improvements (HTTP 429 Fix)

- ✅ **User-Agent header** - Properly identifies the client
- ✅ **Exponential backoff retry** - Automatically retries rate limit errors
- ✅ **API key support** - Environment variable or direct configuration
- ✅ **Fallback test script** - Simple "machine learning" query for testing
- ✅ **Better error reporting** - Detailed logging for debugging

## Need Help?

See `SEMANTIC_SCHOLAR_IMPLEMENTATION.md` for:
- Detailed API documentation
- Error handling guide
- Integration examples
- Rate limiting strategies
- Future enhancements
