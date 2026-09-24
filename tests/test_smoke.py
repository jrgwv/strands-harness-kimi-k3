"""Access smoke tests: confirm the two models agent.py uses are invokable.

These prove the prerequisites in the README are actually satisfied for the current
AWS identity: model access is granted for the Kimi K3 inference profile and for the
Claude Haiku summarizer that web_fetch delegates to.
"""

from conftest import HAIKU, KIMI_K3, converse_text


def test_kimi_k3_converse_invokable(bedrock):
    reply = converse_text(
        bedrock,
        KIMI_K3,
        [{"role": "user", "content": [{"text": "Reply with exactly: SMOKE_OK"}]}],
        # Kimi K3 is a reasoning model: a tiny budget is spent on reasoningContent
        # and leaves no room for the text block, so give it headroom.
        max_tokens=512,
    )
    assert "SMOKE_OK" in reply


def test_haiku_summarizer_invokable(bedrock):
    # web_fetch in agent.py pins this model to summarize fetched pages.
    reply = converse_text(
        bedrock,
        HAIKU,
        [{"role": "user", "content": [{"text": "Reply with exactly: HAIKU_OK"}]}],
        max_tokens=64,
    )
    assert "HAIKU_OK" in reply
