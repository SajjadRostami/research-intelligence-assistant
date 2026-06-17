# Patent Adapters Status

## Current Status (MVP)

**Active Adapter**: `MockPatentAdapter`

The MVP uses `MockPatentAdapter`, which returns **synthetic patent data** for testing and development purposes. This allows the pipeline to continue while real patent API integration is pending.

## Adapter History

### ❌ GooglePatentsAdapter (Deprecated)
**Problem**: Google Patents renders search results with JavaScript (Polymer SPA)

**Why it fails**:
- HTML fetched via `httpx` contains only `<search-app></search-app>` (empty custom element)
- Actual `<search-result>` elements are rendered client-side by JavaScript
- BeautifulSoup cannot parse dynamically rendered content
- Would require Playwright/Selenium (slow, heavyweight, fragile)

**Evidence**:
```html
<body unresolved>
  <script src="//www.gstatic.com/.../search-app-vulcanized.js"></script>
  <search-app></search-app>  <!-- Empty until JS runs -->
</body>
```

### ❌ PatentsViewAdapter (Deprecated)
**Problem**: PatentsView API has been shut down (redirects to USPTO transition guide)

**Why it fails**:
- API endpoint returns HTTP 301 redirect
- Service has moved to `data.uspto.gov` (different API)
- New USPTO API has different structure/authentication

**Evidence**:
```
301 Moved Permanently
Location: https://data.uspto.gov/support/transition-guide/patentsview
```

### ✅ MockPatentAdapter (Current MVP)
**Purpose**: Synthetic data for testing/development

**Characteristics**:
- Generates plausible-looking patent titles based on query terms
- Returns consistent patent numbers (US10000000B2, etc.)
- Marks all results with `ConfidenceLevel.LOW` (synthetic data)
- Zero external dependencies (no network calls)
- Allows pipeline development to continue

**Limitations**:
- Not real patent data
- Should NOT be used for production research
- Must be replaced before deployment

## Production Options

### Option 1: Google Patents Public Data (BigQuery) ⭐ Recommended
**Pros**:
- Official Google dataset
- Structured data (no parsing)
- Fast SQL queries
- Reliable and maintained

**Cons**:
- Requires Google Cloud account
- Requires BigQuery setup
- May incur costs (free tier available)

**Implementation**: Create `BigQueryPatentAdapter` that queries `patents-public-data` dataset

**Query Example**:
```sql
SELECT patent_id, title, publication_date, assignee
FROM `patents-public-data.patents.publications`
WHERE SEARCH(title, "soft body simulation")
LIMIT 10
```

### Option 2: Lens.org API
**Pros**:
- Free API for scholarly/patent data
- REST API (no JavaScript)
- Includes both patents and papers

**Cons**:
- Requires API key registration
- Rate limits on free tier
- Coverage may vary by region

**Implementation**: Create `LensOrgAdapter` using their REST API

### Option 3: USPTO Open Data Portal
**Pros**:
- Official US government source
- Free and public

**Cons**:
- New API (recently replaced PatentsView)
- May require learning new API structure
- Documentation may be incomplete

**Implementation**: Create `USPTOAdapter` using the new `data.uspto.gov` API

## Recommendation

For MVP → Production:
1. **MVP**: Use `MockPatentAdapter` (current)
2. **V1.0**: Implement `BigQueryPatentAdapter` (most reliable)
3. **V2.0**: Add `LensOrgAdapter` as alternative source (multi-source)

## Implementation Checklist

When replacing `MockPatentAdapter`:

- [ ] Create new adapter class (e.g., `BigQueryPatentAdapter`)
- [ ] Implement `SearchAdapter` interface
- [ ] Update `ria/adapters/__init__.py` to export new adapter
- [ ] Update tests to use real adapter
- [ ] Add adapter to orchestrator configuration
- [ ] Update documentation
- [ ] Remove or clearly mark `MockPatentAdapter` as deprecated

## Testing

Run the test script:
```bash
python test_google_patents.py
```

The script will display:
- Warning if using `MockPatentAdapter`
- Patent titles, numbers, assignees, and URLs
- Confidence level (LOW for mock data)
