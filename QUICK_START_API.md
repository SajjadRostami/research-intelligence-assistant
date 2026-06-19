# FastAPI Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Environment Variables

```bash
export OPENAI_API_KEY=your_openai_key
export SERPAPI_API_KEY=your_serpapi_key  # Optional
```

Or create a `.env` file:
```env
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
SERPAPI_API_KEY=your_serpapi_key
```

## 3. Start the Server

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 4. Test the API

**Browser:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/

**curl:**
```bash
# Health check
curl http://localhost:8000/

# Generate report
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "XPBD soft body simulation"}'
```

**Python:**
```bash
python test_api.py
```

## 5. Deploy to Railway

1. Push code to GitHub
2. Connect repository to Railway
3. Add environment variables in Railway dashboard:
   - `OPENAI_API_KEY`
   - `SERPAPI_API_KEY` (optional)
4. Railway auto-deploys with: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## API Endpoints

| Method | Endpoint     | Description                    |
|--------|-------------|--------------------------------|
| GET    | `/`         | Health check                   |
| GET    | `/health`   | Detailed health with config    |
| POST   | `/generate` | Generate research report       |

## Request Example

```json
{
  "topic": "machine learning optimization",
  "max_results_per_adapter": 10,
  "workspace_name": "ml_optimization"
}
```

## Response Example

```json
{
  "success": true,
  "message": "Report generated successfully",
  "report_path": "./workspaces/ml_optimization/report.md",
  "report_content": "# Research Intelligence Report...",
  "workspace_dir": "./workspaces/ml_optimization",
  "stats": {
    "total_raw_items": 20,
    "patents_found": 10,
    "papers_found": 10,
    "ranked_patents": 5,
    "ranked_papers": 5,
    "metrics_generated": 12
  }
}
```

## Troubleshooting

**Server won't start:**
- Check `pip install -r requirements.txt` ran successfully
- Verify environment variables are set
- Ensure port 8000 is not in use

**500 errors:**
- Check logs for detailed error messages
- Verify `OPENAI_API_KEY` is valid
- Test with `python test_mvp_e2e.py` to verify pipeline works

**Slow responses:**
- Reduce `max_results_per_adapter` (try 5 instead of 10)
- Check external API rate limits
- Verify network connectivity

## Files Reference

- `app.py` - FastAPI application
- `API_DEPLOYMENT.md` - Full deployment guide
- `API_EXAMPLES.md` - Code examples
- `test_api.py` - Test script
- `Procfile` - Railway/Heroku config
- `requirements.txt` - Dependencies

## Next Steps

1. ✅ Start server locally
2. ✅ Test with curl or browser
3. ✅ Deploy to Railway
4. 📖 Read [API_DEPLOYMENT.md](API_DEPLOYMENT.md) for advanced deployment
5. 💻 See [API_EXAMPLES.md](API_EXAMPLES.md) for code examples
