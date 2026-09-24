"""Characterize how live Bedrock treats prior-turn reasoning content over Converse.

Background
----------
The Kimi K3 model card states that the Converse API can return an
`InternalServerException` when reasoning content from an earlier turn is included in a
multi-turn request, and names Strands Agents' default configuration as affected.
`agent.py` ships a `StripPriorReasoning` hook that removes those blocks before every
model call as a safeguard.

What these tests actually assert
--------------------------------
They send a multi-turn Converse request that carries a faithful-shape prior-turn
`reasoningContent` block (the exact shape Kimi K3 returns), both unstripped and
stripped, and record the outcome. As of the last live run (us-east-1,
global.moonshotai.kimi-k3), BOTH paths succeed -- the documented exception did not
reproduce, so the hook is a correct-but-not-currently-load-bearing safeguard.

These are therefore characterization tests. If Bedrock's behavior changes and the
unstripped path starts raising `InternalServerException`, `test_reasoning_replay_current_behavior`
will fail loudly -- which is the signal that the hook has become load-bearing and the
docs should be updated. `test_stripped_path_succeeds` asserts the invariant the hook
relies on: the stripped request is always accepted.
"""

import pytest
from botocore.exceptions import ClientError

from conftest import KIMI_K3, REASONING_BLOCK, converse_text


def _history(include_reasoning):
    """A 3-message multi-turn history whose assistant turn optionally carries reasoning."""
    assistant_content = ([REASONING_BLOCK] if include_reasoning else []) + [{"text": "391"}]
    return [
        {"role": "user", "content": [{"text": "What is 17 * 23? Think, then give the number."}]},
        {"role": "assistant", "content": assistant_content},
        {"role": "user", "content": [{"text": "Now multiply that result by 2."}]},
    ]


def test_stripped_path_succeeds(bedrock):
    """The invariant the StripPriorReasoning hook guarantees: a request whose history
    has no prior-turn reasoningContent is always accepted."""
    reply = converse_text(bedrock, KIMI_K3, _history(include_reasoning=False))
    assert "782" in reply


def test_reasoning_replay_current_behavior(bedrock):
    """Characterize the unstripped path -- prior-turn reasoning replayed over Converse.

    Documented expectation (model card): may raise InternalServerException.
    Observed live behavior (last run): succeeds.

    We assert the observed behavior so this test becomes a tripwire: if Bedrock
    reverts to rejecting replayed reasoning, this fails and flags that the hook is
    now load-bearing.
    """
    try:
        reply = converse_text(bedrock, KIMI_K3, _history(include_reasoning=True))
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        pytest.fail(
            "Bedrock rejected replayed prior-turn reasoning "
            f"({code}: {exc}). The model-card exception has reappeared, which means "
            "the StripPriorReasoning hook in agent.py is now load-bearing. Update "
            "RESULTS.md and the README accordingly."
        )
    assert "782" in reply
