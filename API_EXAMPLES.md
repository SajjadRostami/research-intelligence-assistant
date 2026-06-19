# API Examples

Quick reference for using the Research Intelligence Assistant API.

## Start the Server

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

For Railway deployment:
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

## API Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "status": "running",
  "message": "Research Intelligence Assistant is running",
  "version": "0.1.0"
}
```

### 2. Detailed Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "api_keys": {
    "serpapi": true,
    "openai": true
  },
  "llm_model": "claude-haiku",
  "base_url": "https://llm.aibricks.io/v1"
}
```

### 3. Generate Report (Basic)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "XPBD soft body simulation algorithm"}'
```

### 4. Generate Report (Custom Parameters)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "machine learning optimization techniques",
    "max_results_per_adapter": 5,
    "workspace_name": "ml_optimization_workspace"
  }'
```

### 5. Generate Report and Save to File

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "quantum computing algorithms"}' \
  | jq -r '.report_content' > report.md
```

## Python Examples

### Using httpx

```python
import asyncio
import httpx


async def generate_report():
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:8000/generate",
            json={
                "topic": "XPBD soft body simulation algorithm",
                "max_results_per_adapter": 10,
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Report generated: {result['report_path']}")
            print(f"Patents found: {result['stats']['patents_found']}")
            print(f"Papers found: {result['stats']['papers_found']}")
            return result
        else:
            print(f"Error: {response.text}")
            return None


asyncio.run(generate_report())
```

### Using requests

```python
import requests

response = requests.post(
    "http://localhost:8000/generate",
    json={
        "topic": "neural network architecture search",
        "max_results_per_adapter": 8,
    },
    timeout=300,
)

if response.status_code == 200:
    result = response.json()
    
    # Save report to file
    with open("output_report.md", "w") as f:
        f.write(result["report_content"])
    
    print(f"Report saved to output_report.md")
    print(f"Statistics: {result['stats']}")
else:
    print(f"Error: {response.text}")
```

## JavaScript/TypeScript Examples

### Using fetch

```javascript
async function generateReport(topic) {
  const response = await fetch('http://localhost:8000/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      topic: topic,
      max_results_per_adapter: 10,
    }),
  });

  if (response.ok) {
    const result = await response.json();
    console.log('Report generated:', result.report_path);
    console.log('Stats:', result.stats);
    return result;
  } else {
    console.error('Error:', await response.text());
    return null;
  }
}

generateReport('XPBD soft body simulation algorithm');
```

### Using axios

```javascript
const axios = require('axios');

async function generateReport(topic) {
  try {
    const response = await axios.post('http://localhost:8000/generate', {
      topic: topic,
      max_results_per_adapter: 10,
    }, {
      timeout: 300000, // 5 minutes
    });

    console.log('Report generated:', response.data.report_path);
    console.log('Stats:', response.data.stats);
    
    // Save report to file
    const fs = require('fs');
    fs.writeFileSync('report.md', response.data.report_content);
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    return null;
  }
}

generateReport('machine learning optimization');
```

## Testing with the Interactive Docs

Visit `http://localhost:8000/docs` to access the interactive Swagger UI where you can:

1. View all available endpoints
2. See request/response schemas
3. Test endpoints directly from the browser
4. Download OpenAPI specification

## Response Format

All `/generate` responses follow this structure:

```json
{
  "success": true,
  "message": "Report generated successfully for topic: ...",
  "report_path": "./workspaces/workspace_name/report.md",
  "report_content": "# Research Intelligence Report...",
  "workspace_dir": "./workspaces/workspace_name",
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

## Error Handling

When an error occurs, the API returns:

```json
{
  "detail": "Error generating report: <error message>"
}
```

**HTTP Status Codes:**
- `200` - Success
- `422` - Validation Error (invalid request body)
- `500` - Internal Server Error (pipeline failure)

## Rate Limiting Considerations

- SerpAPI has rate limits (free tier: 100 searches/month)
- Semantic Scholar API has rate limits (1 request/second recommended)
- LLM API may have rate limits depending on your provider
- Consider implementing request queuing for production use

## Production Tips

1. **Set longer timeouts** - Report generation can take 2-5 minutes
2. **Handle async processing** - Consider webhook callbacks for long-running requests
3. **Cache results** - Store generated reports and reuse when possible
4. **Monitor API keys** - Track usage and rotate keys as needed
5. **Add authentication** - Protect your API in production
6. **Use environment variables** - Never hardcode API keys
