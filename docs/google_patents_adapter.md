# Google Patents Adapter Documentation

## Overview

The `GooglePatentsAdapter` is a concrete implementation of the `SearchAdapter` base class that enables searching and retrieving patent information from Google Patents (patents.google.com).

## Architecture

### Class Hierarchy
```
SearchAdapter (ABC)
    └── GooglePatentsAdapter
```

### Key Components

1. **URL Building**: Constructs Google Patents search URLs with URL-encoded queries
2. **HTTP Client**: Async HTTP requests using `httpx` with browser-like headers
3. **Retry Logic**: Exponential backoff for HTTP 429 (rate limiting) errors
4. **HTML Parsing**: Extracts patent metadata using BeautifulSoup4
5. **Data Mapping**: Converts raw HTML data into `RawSourceItem` Pydantic models

## How It Works

### 1. Search Flow

```python
async def search(query: str, max_results: int = 10) -> list[RawSourceItem]
```

**Steps:**
1. Build search URL from query string
2. Fetch HTML content with retry logic
3. Parse HTML to extract patent information
4. Convert to `RawSourceItem` objects
5. Return up to `max_results` items

### 2. URL Construction

```python
def _build_search_url(query: str) -> str
```

- Takes a natural language query
- URL-encodes the query using `urllib.parse.quote_plus`
- Returns: `https://patents.google.com/?q={encoded_query}`

**Example:**
```python
query = "quantum computing"
url = adapter._build_search_url(query)
# Result: "https://patents.google.com/?q=quantum+computing"
```

### 3. HTTP Fetch with Exponential Backoff

```python
async def _fetch_with_backoff(url: str) -> str
```

**Features:**
- Browser-like User-Agent and headers to avoid anti-scraping blocks
- Automatic retry on HTTP 429 (rate limiting)
- Exponential backoff: delays double on each retry (1s → 2s → 4s)
- Configurable max retries (default: 3)
- Raises immediately on non-429 HTTP errors

**Backoff Strategy:**
```
Attempt 1: Request → Fail (429) → Wait 1.0s
Attempt 2: Request → Fail (429) → Wait 2.0s
Attempt 3: Request → Fail (429) → Wait 4.0s
Attempt 4: Request → Fail (429) → Raise error
```

### 4. HTML Parsing

```python
def _parse_results(html: str, query: str) -> list[RawSourceItem]
```

**Extracted Fields:**
- **Title**: Patent title (from `<h3 class="result-title">`)
- **Patent Number**: Official patent ID (from `<span data-result="patent_number">`)
- **Publication Date**: Patent publication date (from `<span data-result="publication_date">`)
- **Assignee**: Patent holder/company (from `<span data-result="assignee">`)
- **Source URL**: Link to patent detail page (`/patent/{patent_number}`)

**Field Mapping to RawSourceItem:**
```python
RawSourceItem(
    title=title,                           # Required
    source_type=SourceType.PATENT,         # Always PATENT
    source_url=source_url,                 # Required
    publication_date=publication_date,     # Optional
    author_or_assignee=assignee,           # Optional
    patent_number=patent_number,           # Optional
    confidence_level=ConfidenceLevel.HIGH, # Direct from source
    raw_adapter_source="google_patents",   # Adapter identifier
)
```

## Usage Examples

### Basic Search

```python
import asyncio
from ria.adapters import GooglePatentsAdapter

async def main():
    adapter = GooglePatentsAdapter()
    results = await adapter.search("artificial intelligence", max_results=5)
    
    for item in results:
        print(f"{item.patent_number}: {item.title}")

asyncio.run(main())
```

### Custom Configuration

```python
# Increase retries and initial backoff for rate-limited environments
adapter = GooglePatentsAdapter(
    base_url="https://patents.google.com/",
    max_retries=5,
    initial_backoff=2.0
)
```

### Error Handling

```python
import httpx
from ria.adapters import GooglePatentsAdapter

async def robust_search(query: str):
    adapter = GooglePatentsAdapter()
    
    try:
        results = await adapter.search(query, max_results=10)
        return results
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code}")
        return []
    except httpx.RequestError as e:
        print(f"Network error: {e}")
        return []
```

### Integration with Orchestrator

```python
from ria.adapters import GooglePatentsAdapter
from ria.models import OrchestratorResult, SearchQuery

async def search_patents(topic: str) -> OrchestratorResult:
    adapter = GooglePatentsAdapter()
    
    # Create search query record
    query = SearchQuery(
        query_string=topic,
        source="google_patents"
    )
    
    # Execute search
    raw_items = await adapter.search(topic, max_results=20)
    
    return OrchestratorResult(
        topic=topic,
        queries=[query],
        raw_items=raw_items
    )
```

## Configuration

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `"https://patents.google.com/"` | Google Patents base URL |
| `max_retries` | `int` | `3` | Maximum retry attempts for 429 errors |
| `initial_backoff` | `float` | `1.0` | Initial backoff delay in seconds |

### Class Attributes

| Attribute | Type | Value | Description |
|-----------|------|-------|-------------|
| `source_type` | `SourceType` | `SourceType.PATENT` | Type of sources returned |

## Error Handling

### Handled Errors

1. **HTTP 429 (Rate Limiting)**
   - Automatically retries with exponential backoff
   - Logs warning on each retry
   - Raises after max retries exceeded

2. **Other HTTP Errors (4xx, 5xx)**
   - Logged and raised immediately
   - No retry logic

3. **Network Errors**
   - Logged and raised immediately
   - Includes timeout, connection refused, DNS failures

4. **Parsing Errors**
   - Individual result failures logged as warnings
   - Search continues with remaining results
   - Returns partial results

### Return Behavior

- **Success**: Returns `list[RawSourceItem]` (may be empty if no results)
- **All errors**: Returns empty list `[]` and logs error
- **Never raises**: All exceptions are caught and logged

## Logging

The adapter uses Python's standard `logging` module with logger name `ria.adapters.google_patents`.

**Log Levels:**
- `INFO`: Successful searches, result counts
- `WARNING`: Rate limiting retries, parsing failures
- `ERROR`: HTTP errors, network failures, max retries exceeded

**Example Log Output:**
```
INFO: Searching Google Patents: https://patents.google.com/?q=quantum+computing
WARNING: Rate limited (429). Retrying in 1.0s (attempt 1/3)
INFO: Extracted 10 patents from Google Patents
```

## Testing

See `test_google_patents.py` for unit tests covering:
- URL building
- Source type verification
- Field extraction
- Error handling
- Integration testing

## Limitations

1. **Web Scraping**: Depends on Google Patents HTML structure
2. **Rate Limiting**: May be blocked by Google's anti-scraping measures
3. **No Authentication**: Does not support API keys or OAuth
4. **Limited Metadata**: Only extracts fields available in search results
5. **No Advanced Search**: Does not support Google Patents' advanced search syntax

## Future Enhancements

- [ ] Support for Google Patents Public Datasets API
- [ ] Advanced search query syntax
- [ ] Patent family information
- [ ] Citation extraction
- [ ] Full-text patent content retrieval
- [ ] Configurable User-Agent rotation
- [ ] Proxy support for rate limiting mitigation

## Dependencies

- `httpx`: Async HTTP client
- `beautifulsoup4`: HTML parsing
- `pydantic`: Data validation (via `ria.models`)

## See Also

- [SearchAdapter Base Class](./search_adapter.md)
- [RawSourceItem Model](./models.md#rawsourceitem)
- [Orchestration Flow](./orchestration.md)
