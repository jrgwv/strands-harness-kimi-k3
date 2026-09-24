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
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

REGION = os.environ.get("AWS_REGION", "us-east-1")

# botocore error codes that mean "your credentials are missing/expired/invalid",
# as opposed to "the model isn't available here".
_AUTH_ERROR_CODES = {
    "UnrecognizedClientException",  # invalid security token
    "InvalidSignatureException",
    "ExpiredToken",
    "ExpiredTokenException",
    "InvalidClientTokenId",
    "AuthFailure",
    "AccessDeniedException",  # authenticated but not authorized
    "UnauthorizedException",
}

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
    """A bedrock-runtime client, or skip the whole session with a specific reason.

    Skips (rather than fails) so the suite is safe to collect anywhere, but the skip
    message names the actual cause: missing credentials, an invalid/expired token, or
    the model genuinely not being available/authorized in this Region.
    """
    client = boto3.client("bedrock-runtime", region_name=REGION)
    try:
        client.converse(
            modelId=KIMI_K3,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            # Kimi K3 requires maxTokens >= 16.
            inferenceConfig={"maxTokens": 16},
        )
    except NoCredentialsError:
        pytest.skip(
            "No AWS credentials found. Set your profile before running, e.g. "
            "`AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest tests -v`."
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in _AUTH_ERROR_CODES:
            pytest.skip(
                f"AWS auth failed ({code}): credentials are missing, expired, or "
                "invalid -- this is NOT a Region problem. Refresh your credentials "
                "(e.g. re-run your isengardcli/ada/SSO login for the profile), confirm "
                "with `aws sts get-caller-identity`, then re-run. Kimi K3 is available "
                f"in {REGION}."
            )
        pytest.skip(
            f"Bedrock/Kimi K3 not reachable in {REGION} ({code}): {exc}. "
            "Check the model has access granted in this Region/account."
        )
    except BotoCoreError as exc:
        pytest.skip(f"Could not reach Bedrock in {REGION}: {type(exc).__name__}: {exc}")
    return client


def converse_text(client, model_id, messages, max_tokens=256):
    """Call Converse and return the concatenated text of the reply."""
    resp = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens},
    )
    return "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
