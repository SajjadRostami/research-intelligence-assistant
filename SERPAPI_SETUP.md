# SerpAPI Patent Adapter Setup Guide

## Overview

The `SerpAPIPatentAdapter` provides real patent search results for the MVP using SerpAPI's Google Patents engine. This is a production-ready adapter that queries the Google Patents database through SerpAPI's structured API without web scraping.

## Prerequisites

1. **SerpAPI Account**: Sign up at [https://serpapi.com/](https://serpapi.com/)
2. **API Key**: Get your API key from the SerpAPI dashboard
3. **Python Dependencies**: `httpx` (already in requirements.txt)

## Setup Instructions

### 1. Configure API Key

Add your SerpAPI key to the `.env` file:

```bash
# Copy the example file if you haven't already
cp .env.example .env

# Edit .env and add your key
SERPAPI_API_KEY=your_actual_serpapi_key_here
```

Alternatively, export it as an environment variable:

```bash
export SERPAPI_API_KEY=your_actual_serpapi_key_here
```

### 2. Verify Installation

Run the unit tests to verify everything is configured correctly:

```bash
python -m pytest tests/unit/test_serpapi_patents.py -v
```

All 13 tests should pass.

### 3. Run Live Test

Test the adapter with a real SerpAPI query:

```bash
python test_serpapi_patents_live.py
```

This will search for "XPBD soft body simulation algorithm" and display 5 patent results.

**Expected output:**
```
================================================================================
SerpAPI Patent Adapter - Live Test
================================================================================

✅ Adapter initialized successfully
📝 Query: 'XPBD soft body simulation algorithm'
📊 Requesting: 5 results

--------------------------------------------------------------------------------

✅ Found 5 patent(s) via SerpAPI

================================================================================
Result #1
================================================================================
Title:            [Patent Title]
Patent Number:    [Patent ID]
Assignee:         [Company/Organization]
Publication Date: [YYYY-MM-DD]
URL:              https://patents.google.com/patent/...
Source Type:      patent
Adapter:          serpapi_patents
Confidence:       High
Snippet:          [Abstract/description excerpt...]

...
```

## Usage in Code

### Basic Usage

```python
from ria.adapters import SerpAPIPatentAdapter

# Initialize adapter (reads SERPAPI_API_KEY from environment)
adapter = SerpAPIPatentAdapter()

# Search for patents
results = await adapter.search("quantum computing", max_results=10)

# Process results
for patent in results:
    print(f"{patent.title} ({patent.patent_number})")
    print(f"  Assignee: {patent.author_or_assignee}")
    print(f"  Date: {patent.publication_date}")
    print(f"  URL: {patent.source_url}")
```

### With Explicit API Key

```python
adapter = SerpAPIPatentAdapter(api_key="your_key_here")
```

### Error Handling

The adapter handles errors gracefully and returns an empty list on failure:

```python
results = await adapter.search("query")

if not results:
    print("No results found or an error occurred")
else:
    print(f"Found {len(results)} patents")
```

## Data Structure

Each result is a `RawSourceItem` with the following fields:

- **title**: Patent title
- **patent_number**: Patent ID (e.g., "US1234567A")
- **author_or_assignee**: Patent holder/assignee
- **publication_date**: Publication date (YYYY-MM-DD format)
- **source_url**: URL to patent document
- **relevance_explanation**: Abstract/snippet text
- **source_type**: Always `SourceType.PATENT`
- **confidence_level**: Always `ConfidenceLevel.HIGH` (structured API data)
- **raw_adapter_source**: Always "serpapi_patents"

## API Limits

- **SerpAPI Rate Limits**: Check your plan's rate limits on the SerpAPI dashboard
- **Results per Query**: Must be between 10 and 100 (SerpAPI constraint for google_patents engine)
  - If you request fewer than 10, the adapter automatically clamps to 10
  - If you request more than 100, the adapter automatically clamps to 100
- **Timeout**: 30 seconds per request

## Cost Considerations

SerpAPI has a free tier with limited searches per month. Monitor your usage:

- Free tier: 100 searches/month
- Paid plans: Starting at $50/month for 5,000 searches
- See [SerpAPI Pricing](https://serpapi.com/pricing) for details

## Troubleshooting

### Error: "SERPAPI_API_KEY must be set"

**Solution**: Ensure the API key is set in `.env` or exported as an environment variable.

### Error: "Invalid API key provided"

**Solution**: Verify your API key is correct and active in the SerpAPI dashboard.

### No results returned

**Possible causes:**
1. Query is too specific or misspelled
2. No matching patents in Google Patents database
3. API rate limit exceeded

**Debug steps:**
```bash
# Enable logging to see detailed error messages
export LOG_LEVEL=DEBUG
python test_serpapi_patents_live.py
```

### HTTP 429 (Too Many Requests)

**Solution**: You've exceeded your API rate limit. Wait or upgrade your SerpAPI plan.

## Integration with MVP

The `SerpAPIPatentAdapter` is the recommended adapter for MVP production use. To use it in your application:

```python
# In your orchestrator or search module
from ria.adapters import SerpAPIPatentAdapter

# Replace MockPatentAdapter with SerpAPIPatentAdapter
patent_adapter = SerpAPIPatentAdapter()

# Use in orchestrator
results = await patent_adapter.search(query, max_results=10)
```

## Comparison with Other Adapters

| Adapter | Status | Data Source | Requires API Key |
|---------|--------|-------------|------------------|
| `SerpAPIPatentAdapter` | ✅ Recommended | Google Patents via SerpAPI | Yes |
| `MockPatentAdapter` | Dev/Testing | Hardcoded mock data | No |
| `GooglePatentsAdapter` | Deprecated | Direct scraping (broken) | No |
| `PatentsViewAdapter` | Deprecated | PatentsView (shut down) | No |

## Development vs Production

**Development/Testing:**
- Use `MockPatentAdapter` when you don't have a SerpAPI key
- Mock adapter returns hardcoded results for testing

**Production/MVP:**
- Use `SerpAPIPatentAdapter` with a valid API key
- Real patent data from Google Patents database
- High-quality structured results

## Next Steps

For production at scale, consider:

1. **BigQuery Public Patents**: Direct access to Google's patents dataset
2. **Lens.org API**: Comprehensive scholarly and patent data
3. **USPTO API**: Direct USPTO patent database access
4. **Caching**: Implement result caching to reduce API costs

## Support

- **SerpAPI Docs**: [https://serpapi.com/google-patents-api](https://serpapi.com/google-patents-api)
- **SerpAPI Support**: [https://serpapi.com/support](https://serpapi.com/support)
- **Project Issues**: File issues in your project repository
