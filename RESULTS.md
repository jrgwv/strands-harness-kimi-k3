# Live test results

This document records what happened when `agent.py` was run against **live Amazon
Bedrock**, not a stub. It replaces the pre-publication `TODO.md`, whose open items were
all verified against the library source and a stubbed Converse stream but never against
Bedrock itself because no AWS credentials were available at the time.

The headline: the example runs end to end against Kimi K3, every Kimi-K3-specific
setting behaves as documented, and the reproducible checks now live in [`tests/`](tests/).
One claim came back **negative** and is reported as such below — the multi-turn
reasoning `InternalServerException` the model card warns about could not be reproduced
on the current endpoint.

## Environment

| | |
|---|---|
| Date | 2026-09-24 |
| Region | `us-east-1` |
| Account | AWS sandbox (…`2124`) |
| Python | 3.12.10 |
| `strands-harness` | 0.1.2 |
| `strands-agents` | 1.57.0 |
| `boto3` | 1.43.101 |
| Model | `global.moonshotai.kimi-k3` (Converse) |
| `web_fetch` summarizer | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |

Both the `strands-harness` and `strands-agents` versions match the ones `TODO.md` was
reviewed against, so these results speak to the exact code paths that review reasoned
about.

## Summary

| # | Claim under test | Result |
|---|---|---|
| 1 | Model access is granted; Kimi K3 and the Haiku summarizer are invokable | **Confirmed** |
| 2 | `agent.py` runs end to end, uses `web_fetch`, and writes `REVIEW.md` | **Confirmed** |
| 3 | Resuming a session that contains prior-turn reasoning does not error (hook enabled) | **Confirmed** |
| 4 | `context_window_limit = 1_000_000` is accepted and no early compaction occurs | **Confirmed** |
| 5 | `caching=False` suppresses the per-request cache-point warning | **Confirmed** |
| 6 | Without the hook, replayed reasoning raises `InternalServerException` (the model-card caveat) | **Not reproduced** — see §"The reasoning caveat" |

## What was verified

### 1. Access and invocation

A minimal Converse call to `global.moonshotai.kimi-k3` returned the requested sentinel
string, and the same for `global.anthropic.claude-haiku-4-5-20251001-v1:0`. This
confirms the README's prerequisites are satisfied for this identity: model access is
granted for both the model and the summarizer `web_fetch` delegates to. Encoded as
`tests/test_smoke.py`.

One behavior worth noting for anyone writing their own probes: Kimi K3 requires
`maxTokens >= 16`, and because it is a reasoning model a very small token budget is
consumed entirely by `reasoningContent`, leaving an empty text block. The smoke test
uses 512 tokens so a text answer is actually returned.

### 2. End-to-end agent run

`python agent.py` was run from a clean state (no `.agent/`, no `REVIEW.md`). It
completed in about 2.5 minutes with exit code 0 and:

- read `agent.py` and the surrounding files,
- called `web_fetch` twice to read the Kimi K3 model card — exercising the pinned
  Claude Haiku summarizer rather than falling back to Kimi K3 itself,
- wrote a ~9.4 KB `REVIEW.md`,
- produced no Python traceback and raised no `InternalServerException`.

The harness printed one startup notice — that the model has no native web search and
`web_search` can be enabled through Exa. That is expected, documented behavior, not an
error. Encoded (in an isolated temp directory with its own session) as the `slow` test
`tests/test_agent_end_to_end.py`.

### 3. Session resume with prior reasoning (hook enabled)

`agent.py` uses a fixed `session={"id": "kimi-k3-demo"}`, so running it a second time
resumes the conversation and replays the earlier turns. The persisted session was
confirmed to contain `reasoningContent` blocks before the second run, so the resume
genuinely exercised the multi-turn-with-reasoning path. With the `StripPriorReasoning`
hook enabled, the second run completed in about 40 seconds, exit code 0, with no
`InternalServerException`.

### 4. Context window

`agent.model.update_config(context_window_limit=1_000_000)` was accepted and the runs
completed with no compaction, consistent with the intended 1M-token limit replacing
Strands' 200K default. (Not independently stress-tested to 170K+ tokens; verified only
that the setting is accepted and no early compaction occurred on these runs.)

### 5. Caching

With `caching=False`, no per-request cache-point warning appeared in the run logs:
explicit cache points are only emitted for Claude model IDs, so for Kimi K3 the setting
only ever suppressed a no-op warning. Bedrock's implicit prompt caching for Kimi K3 is
unaffected.

## The reasoning caveat (the one negative result)

**Claim.** The Kimi K3 model card states the Converse API can return an
`InternalServerException` when reasoning content from an earlier turn is included in a
multi-turn request, and names Strands Agents' default configuration as affected.
`agent.py` ships the `StripPriorReasoning` hook specifically to avoid this. The intent
of this test was to prove that caveat is real by disabling the hook and observing the
failure.

**What was tried.** Three independent attempts to reproduce the exception:

1. **Through the harness.** A copy of `agent.py` with `hooks=[]` (the hook removed) was
   run twice against its own session, so the second run resumed a history containing a
   real `reasoningContent` block. It completed with exit code 0 — no exception.
2. **Directly against Converse.** A hand-built multi-turn request was sent to
   `global.moonshotai.kimi-k3` with a prior-turn assistant message carrying a
   `reasoningContent` block, then a new user turn. It succeeded. The same request with
   the reasoning block stripped also succeeded.
3. **Faithful-shape check.** To rule out the probe sending a shape Bedrock silently
   ignores, the exact block shape Kimi K3 returns was captured from a live response —
   `{"reasoningContent": {"reasoningText": {"text": ...}}}` — and confirmed identical to
   what the probe sent and what the harness persists in a session. The probe was
   faithful; Converse accepted it anyway.

**Conclusion.** On the `global.moonshotai.kimi-k3` endpoint in `us-east-1` as of
2026-09-24, replaying prior-turn reasoning content over Converse does **not** raise
`InternalServerException`, with or without the hook. The most likely explanation is
that the server-side behavior was fixed or relaxed since the model card was written.

**What this means for `agent.py`.** The `StripPriorReasoning` hook is kept in the
example as a documented, low-cost safeguard: it matches the model card's guidance, adds
negligible overhead, and would protect the agent if the stricter behavior returns or is
still present on other Regions, profiles, or model revisions. It is, however, **not
load-bearing on this endpoint today** — the example runs correctly without it. This
belt-and-suspenders framing is the honest reading of the evidence; the earlier
expectation that the fix was strictly required is not supported by the live endpoint.

The characterization test `tests/test_reasoning_replay.py::test_reasoning_replay_current_behavior`
encodes today's passing behavior deliberately, so that if Bedrock ever reverts to
rejecting replayed reasoning the test fails and signals that the hook has become
load-bearing and this document should be updated.

## Reproducing these results

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest

# Fast checks: access + reasoning-replay characterization (~30s)
AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest tests -m "not slow" -v

# Everything, including the full agent.py end-to-end run (~2-3 min, more tokens)
AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest tests -v
```

See [`tests/README.md`](tests/README.md) for what each test proves. The tests make real
Bedrock calls and cost a small amount of tokens; without credentials or model access
they skip cleanly rather than fail.

## Note on the README's Flex-tier pricing

While reviewing its own code, the agent flagged (in `REVIEW.md`) that the README's
pricing section advertises Bedrock's Flex tier ($1.50 / $7.50 per 1M tokens), but the
Strands Bedrock provider uses the Converse API, and Bedrock service tiers such as Flex
are only reachable through the OpenAI-compatible Responses / Chat Completions APIs — not
Converse. So the example as written cannot actually obtain Flex-tier pricing. This is a
documentation/behavior mismatch to reconcile (either qualify the README claim or note
that Flex requires a different API path); it was surfaced by the test run and is
recorded here, but not changed as part of this test pass.
