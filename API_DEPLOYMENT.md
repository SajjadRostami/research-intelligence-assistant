# FastAPI Deployment Guide

This document provides instructions for deploying the Research Intelligence Assistant FastAPI application.

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
# Required: OpenAI-compatible LLM API
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# Optional: SerpAPI for real patent data (uses mock adapter if not set)
SERPAPI_API_KEY=your_serpapi_key
```

### 3. Run the API Server

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Test the API

**Health Check:**
```bash
curl http://localhost:8000/
```

**Generate Report:**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "XPBD soft body simulation algorithm"}'
```

## Railway Deployment

### 1. Railway Configuration

Railway automatically detects the Python environment and will use the following start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 2. Set Environment Variables in Railway

In your Railway project dashboard, add the following environment variables:

- `OPENAI_API_KEY` - Your OpenAI or compatible API key (required)
- `OPENAI_BASE_URL` - Your LLM API base URL (optional, defaults to OpenAI)
- `LLM_MODEL` - Model name (optional, defaults to claude-haiku)
- `SERPAPI_API_KEY` - Your SerpAPI key (optional, uses mock data if not set)

### 3. Deploy

Push your code to GitHub and connect the repository to Railway. Railway will:
1. Install dependencies from `requirements.txt`
2. Start the server with `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. Expose your API on a public URL

## API Endpoints

### GET /

Health check endpoint.

**Response:**
```json
{
  "status": "running",
  "message": "Research Intelligence Assistant is running",
  "version": "0.1.0"
}
```

### GET /health

Detailed health check with configuration status.

**Response:**
```json
{
  "status": "healthy",
  "api_keys": {
    "serpapi": true,
    "openai": true
  },
  "llm_model": "gpt-4",
  "base_url": "https://api.openai.com/v1"
}
```

### POST /generate

Generate a research intelligence report for a given topic.

**Request Body:**
```json
{
  "topic": "XPBD soft body simulation algorithm",
  "max_results_per_adapter": 10,
  "workspace_name": "optional_custom_name"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Report generated successfully for topic: XPBD soft body simulation algorithm",
  "report_path": "./workspaces/workspace_XPBD_soft_body_simulation_algorithm/report.md",
  "report_content": "# Research Intelligence Report: XPBD soft body simulation algorithm\n\n...",
  "workspace_dir": "./workspaces/workspace_XPBD_soft_body_simulation_algorithm",
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

## Alternative Deployment Platforms

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t research-intelligence-assistant .
docker run -p 8000:8000 --env-file .env research-intelligence-assistant
```

### Heroku

Create a `Procfile`:

```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

Deploy:
```bash
heroku create your-app-name
heroku config:set OPENAI_API_KEY=your_key
heroku config:set SERPAPI_API_KEY=your_key
git push heroku main
```

### AWS Lambda (with Mangum)

Install additional dependency:
```bash
pip install mangum
```

Update `app.py`:
```python
from mangum import Mangum

# ... existing code ...

handler = Mangum(app)
```

Deploy using AWS SAM or Serverless Framework.

## Security Notes

- Never commit API keys to the repository
- Use environment variables for all sensitive configuration
- API keys are not exposed in API responses
- Consider adding authentication middleware for production use
- Use HTTPS in production (automatically handled by Railway/Heroku)

## Monitoring and Logs

Check application logs:
- **Railway:** View logs in the Railway dashboard
- **Local:** Logs appear in terminal stdout
- **Docker:** `docker logs <container_id>`

## Troubleshooting

### Server won't start
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check that environment variables are set correctly
- Ensure port is not already in use

### API returns 500 errors
- Check logs for detailed error messages
- Verify OPENAI_API_KEY is valid
- Test individual components (orchestrator, ranking, metrics) separately

### Slow response times
- Reduce `max_results_per_adapter` in request (default: 10)
- Consider using a faster LLM model
- Check network connectivity to external APIs
