# Tests

Live tests for the Kimi K3 Strands harness example. They make **real Amazon Bedrock
calls** and cost a small amount of tokens, so they are opt-in: without AWS credentials
or Bedrock model access they skip cleanly rather than fail.

## Prerequisites

- The example installed: `pip install -r ../requirements.txt`
- `pip install pytest`
- AWS credentials with access to the Kimi K3 and Claude Haiku 4.5 inference profiles
- Model access granted in the target Region (default `us-east-1`)

## Run

From this `tests/` directory:

```bash
# Fast tests only (smoke + reasoning-replay characterization, ~30s)
AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest -m "not slow" -v

# Everything, including the full agent.py end-to-end run (~2-3 min, more tokens)
AWS_PROFILE=your-profile AWS_REGION=us-east-1 pytest -v
```

## What each test proves

| Test | Proves |
|---|---|
| `test_smoke.py::test_kimi_k3_converse_invokable` | The Kimi K3 profile (`global.moonshotai.kimi-k3`) is reachable and model access is granted. |
| `test_smoke.py::test_haiku_summarizer_invokable` | The Claude Haiku 4.5 profile that `web_fetch` delegates to is invokable under the same credentials. |
| `test_reasoning_replay.py::test_stripped_path_succeeds` | The invariant the `StripPriorReasoning` hook relies on: a multi-turn request with no prior-turn `reasoningContent` is accepted. |
| `test_reasoning_replay.py::test_reasoning_replay_current_behavior` | Characterizes the **unstripped** path — prior-turn reasoning replayed over Converse. Currently succeeds; acts as a tripwire (see below). |
| `test_agent_end_to_end.py::test_agent_py_runs_and_writes_review` (`slow`) | Running `agent.py` completes cleanly, exercises `web_fetch`, and writes `REVIEW.md`, with no raised `InternalServerException`. Runs in an isolated temp dir with its own session, so it never touches the repo's `./.agent` or `REVIEW.md`. |

## The reasoning-replay tripwire

The Kimi K3 model card documents that Converse *can* return an
`InternalServerException` when prior-turn reasoning content is replayed in a multi-turn
request, and `agent.py` ships the `StripPriorReasoning` hook as a safeguard. As of the
last live run (`us-east-1`, `global.moonshotai.kimi-k3`) that exception **does not
reproduce** — the unstripped path succeeds — so the hook is correct but not currently
load-bearing. See `../RESULTS.md` for the full write-up.

`test_reasoning_replay_current_behavior` asserts today's observed (passing) behavior on
purpose. If Bedrock reverts to rejecting replayed reasoning, that test will fail — the
signal that the hook has become load-bearing and that `RESULTS.md` / the README should
be updated.

### Reasoning block shape

`conftest.REASONING_BLOCK` uses the exact shape Kimi K3 returns over Converse and that
the harness persists in a session:

```json
{"reasoningContent": {"reasoningText": {"text": "..."}}}
```

Using a faithful shape is what makes the replay test meaningful — a malformed block
could be silently dropped instead of actually replayed.

## Notes

- Kimi K3 requires `maxTokens >= 16`, and because it is a reasoning model a tiny budget
  is consumed by `reasoningContent` before any text is emitted — the smoke test uses
  512 tokens so a text block is actually returned.
