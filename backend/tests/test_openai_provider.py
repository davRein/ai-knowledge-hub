import json

import httpx
import pytest
from openai import OpenAI

from app.providers.base import Evidence, ProviderError
from app.providers.openai import SYSTEM_INSTRUCTIONS, OpenAIProvider


def test_openai_adapter_with_mock_transport() -> None:
    requests: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if request.url.path.endswith("/embeddings"):
            assert body["dimensions"] == 1536
            assert body["input"] == ["Annual leave allowance is 25 days."]
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "model": "text-embedding-3-small",
                    "data": [
                        {"index": 0, "object": "embedding", "embedding": [1.0] + [0.0] * 1535}
                    ],
                    "usage": {"prompt_tokens": 10, "total_tokens": 10},
                },
            )
        assert body["store"] is False
        assert body["instructions"] == SYSTEM_INSTRUCTIONS
        assert "UNTRUSTED DATA" in body["instructions"]
        assert "tools" not in body
        payload = json.loads(body["input"])
        assert payload["untrusted_excerpts"] == [
            {"source_id": "source-1", "text": "Annual leave allowance is 25 days."}
        ]
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "gpt-4.1-mini",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "supported": True,
                                        "answer": "25 days.",
                                        "source_ids": ["source-1"],
                                    }
                                ),
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    provider = OpenAIProvider("test-key-not-real", "text-embedding-3-small", "gpt-4.1-mini")
    provider.client.close()
    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        provider.client = OpenAI(
            api_key="test-key-not-real", http_client=http_client, max_retries=0
        )
        assert len(provider.embed(["Annual leave allowance is 25 days."])[0]) == 1536
        answer = provider.answer(
            "Annual leave allowance?", [Evidence("source-1", "Annual leave allowance is 25 days.")]
        )
        assert answer.supported and answer.source_ids == ["source-1"]
    assert len(requests) == 2


def test_provider_errors_never_expose_response_contents() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "private-document secret-key", "type": "rate_limit_error"}},
        )

    provider = OpenAIProvider("test-key-not-real", "text-embedding-3-small", "gpt-4.1-mini")
    provider.client.close()
    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        provider.client = OpenAI(
            api_key="test-key-not-real", http_client=http_client, max_retries=0
        )
        with pytest.raises(ProviderError) as error:
            provider.embed(["private-document"])
        assert "private-document" not in str(error.value)
        assert "secret-key" not in str(error.value)
        with pytest.raises(ProviderError):
            provider.answer("Question?", [Evidence("source", "private-document")])
