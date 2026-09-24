"""
Strands harness + Kimi K3 on Amazon Bedrock.

Prerequisites:
- AWS account with Amazon Bedrock access
- IAM permissions for bedrock:InvokeModel and bedrock:InvokeModelWithResponseStream
  on the Kimi K3 inference profile and model
- AWS credentials configured (aws configure, IAM Identity Center, or an instance role)
- Python 3.10+ and `pip install -r requirements.txt`

Run from this directory (the agent reviews agent.py itself):
    python agent.py
"""

from typing import Any

from strands.hooks import BeforeModelCallEvent, HookProvider, HookRegistry
from strands_harness import create_harness

# "bedrock/" selects the Bedrock provider; the rest is the inference profile ID.
# Use "us.moonshotai.kimi-k3" instead to keep inference in US Regions.
MODEL_ID = "bedrock/global.moonshotai.kimi-k3"


class StripPriorReasoning(HookProvider):
    """Remove reasoning blocks from earlier turns before each model call.

    The Kimi K3 model card notes that the Bedrock Converse API (which the harness's
    Bedrock provider uses) returns an InternalServerException when reasoning content
    from earlier turns is included in a multi-turn request, and recommends removing
    it. Strands does this automatically only for DeepSeek models, so this hook does
    it for Kimi K3. The harness forwards hooks to sub-agents, so delegated subtasks
    are covered too.
    """

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeModelCallEvent, self._strip)

    def _strip(self, event: BeforeModelCallEvent) -> None:
        for message in event.agent.messages:
            if message["role"] != "assistant":
                continue
            kept = [block for block in message["content"] if "reasoningContent" not in block]
            if len(kept) != len(message["content"]):
                # Converse rejects empty content, so keep a placeholder if a turn was
                # nothing but reasoning.
                message["content"] = kept or [{"text": "(reasoning omitted)"}]


agent = create_harness(
    model=MODEL_ID,
    # A fixed session ID lets you re-run the script and continue the same conversation.
    # Sessions are stored under ./.agent/sessions by default.
    session={"id": "kimi-k3-demo"},
    # Strands only adds explicit cache points for Claude models on Bedrock, so for
    # Kimi K3 this setting does nothing except log a warning on every request.
    # Bedrock's automatic prompt caching for Kimi K3 still applies.
    caching=False,
    builtin_tools={
        # Kimi K3 has no native web search in Bedrock. To enable search through Exa
        # (third party, keyless free tier; set EXA_API_KEY to lift the rate limit), uncomment:
        # "web_search": "exa",
        # The harness can't identify Kimi K3's family to pick a small web_fetch summarizer,
        # so left alone it falls back to Kimi K3 itself -- a 1M-context model summarizing
        # single web pages. Pin a cheap Bedrock summarizer instead (same AWS credentials).
        "web_fetch": {"model": "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"},
    },
    hooks=[StripPriorReasoning()],
)

# Strands doesn't know Kimi K3's context window yet and assumes 200K tokens, so the harness
# would start compacting at ~170K tokens. Give it the real 1M-token limit.
agent.model.update_config(context_window_limit=1_000_000)

TASK = (
    "Read agent.py in this directory and explain what each Kimi K3-specific setting does. "
    "Then fetch https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-moonshot-ai-kimi-k3.html "
    "and check whether agent.py covers the caveats it lists. Write your findings to REVIEW.md."
)

if __name__ == "__main__":
    agent(TASK)
