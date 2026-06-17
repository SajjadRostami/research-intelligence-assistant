# Quick Start: SerpAPI Patent Adapter

## TL;DR

```bash
# 1. Get API key from https://serpapi.com/
# 2. Add to .env file
echo "SERPAPI_API_KEY=your_key_here" >> .env

# 3. Test it
python test_serpapi_patents_live.py
```

## Running Tests

```bash
# Unit tests (no API key needed - uses mocks)
python -m pytest tests/unit/test_serpapi_patents.py -v

# Live test (requires API key)
python test_serpapi_patents_live.py
```

## Usage in Code

```python
from ria.adapters import SerpAPIPatentAdapter

# Initialize
adapter = SerpAPIPatentAdapter()

# Search
results = await adapter.search("machine learning", max_results=10)

# Use results
for patent in results:
    print(f"{patent.title} - {patent.patent_number}")
```

## File Locations

| File | Purpose |
|------|---------|
| `ria/adapters/serpapi_patents.py` | Main adapter implementation |
| `tests/unit/test_serpapi_patents.py` | Unit tests (13 tests) |
| `test_serpapi_patents_live.py` | Live test script |
| `SERPAPI_SETUP.md` | Complete setup guide |
| `IMPLEMENTATION_SUMMARY.md` | Implementation details |

## API Key Setup

**Option 1: .env file (recommended)**
```bash
SERPAPI_API_KEY=your_api_key_here
```

**Option 2: Environment variable**
```bash
export SERPAPI_API_KEY=your_api_key_here
```

**Option 3: Pass directly in code**
```python
adapter = SerpAPIPatentAdapter(api_key="your_key_here")
```

## Verification Checklist

- [ ] API key obtained from serpapi.com
- [ ] API key added to .env
- [ ] Unit tests pass: `python -m pytest tests/unit/test_serpapi_patents.py -v`
- [ ] Live test runs: `python test_serpapi_patents_live.py`
- [ ] Adapter imports: `from ria.adapters import SerpAPIPatentAdapter`

## Common Issues

**"SERPAPI_API_KEY must be set"**
→ Add API key to .env file or export as environment variable

**"Invalid API key"**
→ Check API key is correct in SerpAPI dashboard

**"No results found"**
→ Try a different query or check SerpAPI dashboard for usage limits

## Next Steps

1. ✅ Test with sample query
2. ✅ Verify results match expectations
3. 🔄 Integrate into orchestrator (replace MockPatentAdapter)
4. 📊 Monitor API usage in SerpAPI dashboard

## Production Checklist

- [ ] API key configured in production environment
- [ ] Usage monitoring set up (SerpAPI dashboard)
- [ ] Rate limiting considered
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Cost budget established

## Support

- **Full Setup Guide**: See `SERPAPI_SETUP.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **SerpAPI Docs**: https://serpapi.com/google-patents-api
- **SerpAPI Support**: https://serpapi.com/support
