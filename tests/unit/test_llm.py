"""
Unit tests for the LLM client.

Tests the LLMClient class with mocked OpenAI API calls to ensure proper
behavior without making real API requests.
"""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from pydantic import BaseModel

from ria.llm import LLMClient


class SampleResponse(BaseModel):
    """Sample Pydantic model for testing JSON responses."""

    name: str
    value: int
    active: bool


class TestLLMClientInitialization:
    """Tests for LLMClient initialization and configuration."""

    def test_init_with_explicit_params(self):
        """Test initialization with all parameters provided explicitly."""
        client = LLMClient(
            api_key="test-key",
            base_url="https://api.example.com",
            model="gpt-4",
            timeout=30,
            max_retries=5,
        )

        assert client.api_key == "test-key"
        assert client.base_url == "https://api.example.com"
        assert client.model == "gpt-4"
        assert client.timeout == 30
        assert client.max_retries == 5

    def test_init_with_env_vars(self):
        """Test initialization using environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-key",
                "OPENAI_BASE_URL": "https://env.example.com",
                "LLM_MODEL": "claude-opus",
                "LLM_TIMEOUT": "90",
                "LLM_MAX_RETRIES": "5",
            },
        ):
            client = LLMClient()

            assert client.api_key == "env-key"
            assert client.base_url == "https://env.example.com"
            assert client.model == "claude-opus"
            assert client.timeout == 90
            assert client.max_retries == 5

    def test_init_defaults(self):
        """Test default values when env vars are not set."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "https://api.example.com",
            },
            clear=True,
        ):
            client = LLMClient()

            assert client.model == "claude-haiku"
            assert client.timeout == 60
            assert client.max_retries == 3

    def test_init_missing_api_key(self):
        """Test that initialization fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
                LLMClient()

    def test_init_missing_base_url(self):
        """Test that initialization fails when base URL is missing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_BASE_URL must be set"):
                LLMClient()

    def test_explicit_params_override_env_vars(self):
        """Test that explicit parameters take precedence over environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-key",
                "OPENAI_BASE_URL": "https://env.example.com",
                "LLM_MODEL": "claude-opus",
            },
        ):
            client = LLMClient(
                api_key="explicit-key",
                base_url="https://explicit.example.com",
                model="gpt-4",
            )

            assert client.api_key == "explicit-key"
            assert client.base_url == "https://explicit.example.com"
            assert client.model == "gpt-4"


class TestLLMClientChat:
    """Tests for the chat() method."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked OpenAI client."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "https://api.example.com",
            },
        ):
            return LLMClient()

    def test_chat_success(self, client):
        """Test successful chat completion."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = "Hello! How can I help you?"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        response = client.chat(messages)

        assert response == "Hello! How can I help you?"
        client.client.chat.completions.create.assert_called_once_with(
            model=client.model,
            messages=messages,
            temperature=0.7,
        )

    def test_chat_with_custom_temperature(self, client):
        """Test chat with custom temperature parameter."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = "Response text"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Test"}]
        response = client.chat(messages, temperature=0.3)

        assert response == "Response text"
        client.client.chat.completions.create.assert_called_once_with(
            model=client.model,
            messages=messages,
            temperature=0.3,
        )

    def test_chat_with_additional_kwargs(self, client):
        """Test chat with additional keyword arguments."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = "Response text"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Test"}]
        response = client.chat(messages, max_tokens=100, top_p=0.9)

        assert response == "Response text"
        client.client.chat.completions.create.assert_called_once_with(
            model=client.model,
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            top_p=0.9,
        )

    def test_chat_empty_response(self, client):
        """Test that chat raises ValueError when response content is None."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = None
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(ValueError, match="LLM returned empty response"):
            client.chat(messages)


class TestLLMClientChatJSON:
    """Tests for the chat_json() method."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked OpenAI client."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "https://api.example.com",
            },
        ):
            return LLMClient()

    def test_chat_json_success(self, client):
        """Test successful JSON response parsing."""
        json_response = {"name": "test", "value": 42, "active": True}
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = json.dumps(json_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        result = client.chat_json(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.name == "test"
        assert result.value == 42
        assert result.active is True

    def test_chat_json_strips_markdown_json_block(self, client):
        """Test that markdown JSON code blocks are properly stripped."""
        json_response = {"name": "test", "value": 42, "active": True}
        markdown_wrapped = f"```json\n{json.dumps(json_response)}\n```"

        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = markdown_wrapped
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        result = client.chat_json(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.name == "test"
        assert result.value == 42
        assert result.active is True

    def test_chat_json_strips_markdown_code_block(self, client):
        """Test that markdown code blocks without 'json' tag are stripped."""
        json_response = {"name": "test", "value": 42, "active": True}
        markdown_wrapped = f"```\n{json.dumps(json_response)}\n```"

        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = markdown_wrapped
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        result = client.chat_json(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.name == "test"
        assert result.value == 42

    def test_chat_json_malformed_json(self, client):
        """Test that malformed JSON raises JSONDecodeError."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = "{invalid json content"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        with pytest.raises(json.JSONDecodeError):
            client.chat_json(messages, SampleResponse)

    def test_chat_json_invalid_schema(self, client):
        """Test that JSON not matching schema raises ValidationError."""
        # Missing required field 'active'
        json_response = {"name": "test", "value": 42}
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = json.dumps(json_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            client.chat_json(messages, SampleResponse)

    def test_chat_json_empty_response(self, client):
        """Test that empty response raises ValueError."""
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = None
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        with pytest.raises(ValueError, match="LLM returned empty response"):
            client.chat_json(messages, SampleResponse)

    def test_chat_json_augments_user_message(self, client):
        """Test that chat_json augments the last user message with schema instructions."""
        json_response = {"name": "test", "value": 42, "active": True}
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = json.dumps(json_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Generate data"},
        ]
        client.chat_json(messages, SampleResponse)

        # Check that the create method was called
        call_args = client.client.chat.completions.create.call_args
        called_messages = call_args[1]["messages"]

        # The last message should be augmented
        assert len(called_messages) == 2
        assert called_messages[0]["role"] == "system"
        assert called_messages[1]["role"] == "user"
        assert "Generate data" in called_messages[1]["content"]
        assert "IMPORTANT: Respond with ONLY valid JSON" in called_messages[1]["content"]
        assert "Required JSON schema:" in called_messages[1]["content"]

    def test_chat_json_with_custom_temperature(self, client):
        """Test chat_json with custom temperature."""
        json_response = {"name": "test", "value": 42, "active": True}
        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = json.dumps(json_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        result = client.chat_json(messages, SampleResponse, temperature=0.2)

        assert isinstance(result, SampleResponse)
        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.2

    def test_chat_json_whitespace_handling(self, client):
        """Test that extra whitespace around JSON is handled correctly."""
        json_response = {"name": "test", "value": 42, "active": True}
        content_with_whitespace = f"\n\n  {json.dumps(json_response)}  \n\n"

        mock_response = Mock(spec=ChatCompletion)
        mock_choice = Mock(spec=Choice)
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = content_with_whitespace
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Generate data"}]
        result = client.chat_json(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.name == "test"
        assert result.value == 42
        assert result.active is True
