# LLM Client Implementation (Task 2.1)

## Overview

The `LLMClient` class in `ria/llm.py` provides a unified interface for interacting with OpenAI-compatible LLM endpoints. It supports both standard text responses and structured JSON outputs validated against Pydantic models.

## Design Decisions

### 1. **Configuration via Environment Variables**
- Uses `OPENAI_API_KEY` and `OPENAI_BASE_URL` for API credentials
- Supports optional environment variables for fine-tuning:
  - `LLM_MODEL`: Model name (default: `claude-haiku`)
  - `LLM_TIMEOUT`: Request timeout in seconds (default: 60)
  - `LLM_MAX_RETRIES`: Maximum retry attempts (default: 3)
- All settings can be overridden via constructor parameters

### 2. **Two Core Methods**

#### `chat(messages, temperature=0.7, **kwargs) -> str`
- Standard chat completion returning plain text
- Accepts list of message dictionaries with `role` and `content`
- Returns the assistant's response as a string

#### `chat_json(messages, response_model, temperature=0.7, **kwargs) -> T`
- Structured JSON response parsed into Pydantic models
- Automatically augments prompts with JSON schema instructions
- Strips markdown code blocks (````json...````) from responses
- Validates and returns typed Pydantic model instance

### 3. **Error Handling**
- Automatic retries via OpenAI client's built-in retry mechanism
- Validates API credentials at initialization time
- Raises clear exceptions for empty responses
- Pydantic validation ensures JSON schema compliance

### 4. **Markdown Code Block Handling**
- Claude models often wrap JSON in markdown blocks
- The client automatically strips ````json` and ```` ``` delimiters
- Ensures clean JSON parsing regardless of model behavior

### 5. **API Compatibility Notes**
- Does not use `response_format={'type': 'json_object'}` parameter
- This parameter causes Claude models to return empty objects `{}`
- Instead relies on explicit prompting for JSON format

## Usage Examples

### Basic Chat Completion

```python
from ria.llm import LLMClient

client = LLMClient()

response = client.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is a patent?"}
])

print(response)
# Output: "A patent is a legal right granted by a government..."
```

### Structured JSON Response

```python
from ria.llm import LLMClient
from ria.models import BenchmarkMetric

client = LLMClient()

metric = client.chat_json(
    messages=[
        {"role": "system", "content": "You create benchmark metrics."},
        {"role": "user", "content": "Create a metric for Novelty."}
    ],
    response_model=BenchmarkMetric,
    temperature=0.5
)

print(f"Name: {metric.name}")
print(f"Description: {metric.description}")
# Output is a validated BenchmarkMetric Pydantic object
```

### Custom Configuration

```python
from ria.llm import LLMClient

# Override default settings
client = LLMClient(
    model="claude-sonnet",  # More capable model
    timeout=30,             # Shorter timeout
    max_retries=5           # More retries
)
```

### Environment Variable Configuration

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://llm.aibricks.io/v1
LLM_MODEL=claude-haiku
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
```

## Implementation Details

### Retry Strategy
- Uses OpenAI SDK's built-in exponential backoff
- Retries on network errors and rate limits
- Configurable via `max_retries` parameter

### Timeout Handling
- Applied at the HTTP client level
- Prevents indefinite hangs on slow responses
- Configurable via `timeout` parameter

### JSON Schema Injection
- Schema automatically added to user's last message
- Includes clear instructions to return raw JSON
- Displays full Pydantic schema for the model

### Type Safety
- Generic type parameter `T` for `chat_json()` return type
- Full type hints for IDE autocomplete
- Pydantic validation catches schema mismatches

## Testing

Run the comprehensive test:

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from ria.llm import LLMClient
from ria.models import BenchmarkMetric

client = LLMClient()

# Test chat()
response = client.chat([
    {'role': 'user', 'content': 'Hello!'}
])
print('chat() works:', response)

# Test chat_json()
metric = client.chat_json(
    messages=[{'role': 'user', 'content': 'Create a Novelty metric'}],
    response_model=BenchmarkMetric
)
print('chat_json() works:', metric.name)
"
```

## Future Enhancements

Task 2.1 does not include:
- Search adapter implementations (Task 2.2)
- Streaming responses
- Function calling / tool use
- Token counting
- Caching strategies

These will be addressed in subsequent tasks.

## Dependencies

- `openai==1.54.3` - OpenAI Python client
- `pydantic==2.9.2` - Data validation
- `python-dotenv==1.0.1` - Environment variable loading

## File Location

- Implementation: `ria/llm.py`
- Usage examples: `examples/llm_usage_example.py`
- Documentation: `docs/llm_client.md`
