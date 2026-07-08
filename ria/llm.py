"""
LLM client for interacting with OpenAI-compatible API endpoints.

Provides a unified interface for both standard chat completions and structured
JSON responses with retry logic and timeout handling.
"""

from __future__ import annotations

import json
import os
from typing import Any, TypeVar, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

# Optional LangSmith tracing - graceful degradation if not available
try:
    from langsmith import traceable
    from langsmith.run_trees import RunTree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    RunTree = None  # type: ignore
    # No-op decorator when LangSmith is unavailable
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if len(args) == 0 else decorator(args[0])

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Client for interacting with OpenAI-compatible LLM endpoints.

    Supports both standard chat completions and structured JSON responses.
    Handles retries and timeouts transparently.

    Configuration is loaded from environment variables:
    - OPENAI_API_KEY: API key for authentication
    - OPENAI_BASE_URL: Base URL for the API endpoint
    - LLM_MODEL: Model name to use (default: gpt-4o-mini)
    - LLM_TIMEOUT: Request timeout in seconds (default: 60)
    - LLM_MAX_RETRIES: Maximum number of retries (default: 3)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        report_id: str | None = None,
        topic: str | None = None,
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL (defaults to OPENAI_BASE_URL env var)
            model: Model name (defaults to LLM_MODEL env var or claude-haiku)
            timeout: Request timeout in seconds (defaults to LLM_TIMEOUT env var or 60)
            max_retries: Maximum retry attempts (defaults to LLM_MAX_RETRIES env var or 3)
            report_id: Optional report ID for LangSmith trace metadata
            topic: Optional topic for LangSmith trace metadata
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("LLM_MODEL", "claude-haiku")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        self.max_retries = max_retries or int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.report_id = report_id
        self.topic = topic

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or provided")
        if not self.base_url:
            raise ValueError("OPENAI_BASE_URL must be set in environment or provided")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        # Check if LangSmith tracing is enabled
        # API key priority: LANGSMITH_API_KEY (current) -> LANGCHAIN_API_KEY (legacy)
        langsmith_api_key = (
            os.getenv("LANGSMITH_API_KEY", "").strip() or
            os.getenv("LANGCHAIN_API_KEY", "").strip()
        )

        # Tracing priority: LANGSMITH_TRACING (current) -> LANGCHAIN_TRACING_V2 (legacy)
        tracing_enabled = (
            os.getenv("LANGSMITH_TRACING", "false").lower() == "true" or
            os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        )

        self.langsmith_enabled = (
            LANGSMITH_AVAILABLE
            and tracing_enabled
            and langsmith_api_key != ""
        )

        # Store metadata from last LLM call (tokens, trace info)
        self.last_call_metadata: Optional[dict[str, Any]] = None

    def _extract_metadata(self, response: ChatCompletion) -> None:
        """
        Extract token usage and trace information from LLM response.

        Stores metadata in self.last_call_metadata for optional analytics tracking.
        Does not expose API keys or sensitive prompts.
        """
        metadata: dict[str, Any] = {
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
        }

        # Extract LangSmith trace info if enabled (optional)
        # Note: We don't extract trace_id here since we're creating RunTree objects directly
        # The trace_id would need to be passed from the calling method if needed

        self.last_call_metadata = metadata

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request and return the response text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 to 2.0)
            **kwargs: Additional arguments to pass to the API

        Returns:
            The assistant's response text

        Raises:
            openai.APIError: If the API request fails after retries

        Example:
            >>> client = LLMClient()
            >>> response = client.chat([
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ])
            >>> print(response)
            "2+2 equals 4."
        """
        # Wrap LLM call with LangSmith tracing if enabled
        if self.langsmith_enabled and LANGSMITH_AVAILABLE:
            from langsmith.run_trees import RunTree

            # Build metadata for trace
            metadata = {
                "workflow_name": "research_intelligence_assistant",
            }
            if self.report_id:
                metadata["report_id"] = self.report_id
            if self.topic:
                metadata["topic"] = self.topic

            # Create a RunTree for this LLM call
            run_tree = RunTree(
                name="llm_chat",
                run_type="llm",
                inputs={"messages": messages, "temperature": temperature, "model": self.model},
                project_name=os.getenv("LANGSMITH_PROJECT", "research-intelligence-assistant"),
                extra={"metadata": metadata}
            )

            try:
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    **kwargs,
                )
                # Mark run as successful
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty response")

                # Include token usage in the outputs
                outputs = {"content": content}
                if response.usage:
                    outputs["usage"] = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }

                run_tree.end(outputs=outputs)
                run_tree.post()
            except Exception as e:
                # Mark run as failed
                run_tree.end(error=str(e))
                run_tree.post()
                raise
        else:
            # Direct call without tracing
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=temperature,
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty response")

        # Extract metadata for analytics tracking
        self._extract_metadata(response)

        return content

    def chat_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> T:
        """
        Send a chat completion request and parse the response as a Pydantic model.

        Uses structured output mode to guarantee valid JSON conforming to the
        response_model schema. The LLM is instructed to respond with JSON only.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            response_model: Pydantic model class to parse the response into
            temperature: Sampling temperature (0.0 to 2.0)
            **kwargs: Additional arguments to pass to the API

        Returns:
            Parsed and validated instance of response_model

        Raises:
            openai.APIError: If the API request fails after retries
            pydantic.ValidationError: If the response doesn't match the schema
            json.JSONDecodeError: If the response is not valid JSON

        Example:
            >>> from ria.models import BenchmarkMetric
            >>> client = LLMClient()
            >>> metric = client.chat_json(
            ...     messages=[
            ...         {"role": "system", "content": "Generate a benchmark metric."},
            ...         {"role": "user", "content": "Create a metric for AI model accuracy"}
            ...     ],
            ...     response_model=BenchmarkMetric
            ... )
            >>> print(metric.name)
            "Model Accuracy"
        """
        # Add JSON instruction to the last user message
        augmented_messages = messages.copy()
        schema = response_model.model_json_schema()

        if augmented_messages and augmented_messages[-1]["role"] == "user":
            augmented_messages[-1] = {
                "role": "user",
                "content": (
                    f"{augmented_messages[-1]['content']}\n\n"
                    f"IMPORTANT: Respond with ONLY valid JSON matching this exact schema. "
                    f"Do not include any explanatory text, markdown formatting, or code blocks.\n\n"
                    f"Required JSON schema:\n{json.dumps(schema, indent=2)}\n\n"
                    f"Return your response as a raw JSON object."
                ),
            }

        # Request JSON response (some APIs don't support response_format for all models)
        # Wrap LLM call with LangSmith tracing if enabled
        if self.langsmith_enabled and LANGSMITH_AVAILABLE:
            from langsmith.run_trees import RunTree

            # Build metadata for trace
            metadata = {
                "workflow_name": "research_intelligence_assistant",
                "response_type": "json",
                "response_model": response_model.__name__,
            }
            if self.report_id:
                metadata["report_id"] = self.report_id
            if self.topic:
                metadata["topic"] = self.topic

            # Create a RunTree for this LLM call
            run_tree = RunTree(
                name="llm_chat_json",
                run_type="llm",
                inputs={"messages": augmented_messages, "temperature": temperature, "model": self.model},
                project_name=os.getenv("LANGSMITH_PROJECT", "research-intelligence-assistant"),
                extra={"metadata": metadata}
            )

            try:
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=augmented_messages,  # type: ignore
                    temperature=temperature,
                    **kwargs,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty response")

                # Strip markdown code blocks if present
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                # Parse and validate the JSON response
                parsed_data = json.loads(content)
                validated = response_model.model_validate(parsed_data)

                # Mark run as successful with token usage in outputs
                outputs = {"content": content, "parsed": parsed_data}
                if response.usage:
                    outputs["usage"] = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }

                run_tree.end(outputs=outputs)
                run_tree.post()

                # Extract metadata for analytics tracking
                self._extract_metadata(response)

                return validated

            except Exception as e:
                # Mark run as failed
                run_tree.end(error=str(e))
                run_tree.post()
                raise
        else:
            # Direct call without tracing
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=augmented_messages,  # type: ignore
                temperature=temperature,
                **kwargs,
            )

            # Extract metadata for analytics tracking
            self._extract_metadata(response)

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty response")

            # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
            content = content.strip()
            if content.startswith("```"):
                # Remove opening ```json or ```
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                # Remove closing ```
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            # Parse and validate the JSON response
            parsed_data = json.loads(content)
            return response_model.model_validate(parsed_data)
