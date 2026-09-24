"""Shared fixtures and configuration for the Kimi K3 harness tests.

These tests make real calls to Amazon Bedrock and therefore cost tokens. They are
skipped automatically when AWS credentials or Bedrock model access are unavailable,
so a checkout without credentials still collects and skips cleanly.

Run them with your AWS profile and Region exported, e.g.:

    AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest -v

or target a single file:

    AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest tests/test_reasoning_replay.py -v
"""

import os

import boto3
import pytest
from botocore.exceptions import BotoCoreError, ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")

# The two inference profiles agent.py depends on.
KIMI_K3 = "global.moonshotai.kimi-k3"
HAIKU = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

# The exact reasoningContent block shape Kimi K3 returns over Converse and that the
# harness persists in a session. Captured from a live response; see
# tests/README.md ("Reasoning block shape").
REASONING_BLOCK = {
    "reasoningContent": {"reasoningText": {"text": "17*20=340, 17*3=51, total 391."}}
}


@pytest.fixture(scope="session")
def bedrock():
    """A bedrock-runtime client, or skip the whole session if unusable.

    Skips (rather than fails) when there are no credentials or when the account
    lacks access to the Kimi K3 profile, so the suite is safe to collect anywhere.
    """
    client = boto3.client("bedrock-runtime", region_name=REGION)
    try:
        client.converse(
            modelId=KIMI_K3,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            # Kimi K3 requires maxTokens >= 16.
            inferenceConfig={"maxTokens": 16},
        )
    except (ClientError, BotoCoreError) as exc:
        pytest.skip(f"Bedrock/Kimi K3 not reachable in {REGION}: {type(exc).__name__}: {exc}")
    return client


def converse_text(client, model_id, messages, max_tokens=256):
    """Call Converse and return the concatenated text of the reply."""
    resp = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens},
    )
    return "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
