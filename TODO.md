# TODO — verify against live Bedrock before publishing

No AWS credentials were available in the review environments, so everything below was
checked by reading the `strands-harness` 0.1.2 / `strands-agents` 1.57.0 source and by
running `agent.py` against a stubbed Converse stream, not against Bedrock itself.

## 1. Converse API + multi-turn reasoning content — mitigated, needs a live run

The Kimi K3 model card says Converse returns `InternalServerException` when reasoning
content from earlier turns is included in a multi-turn request, and names Strands Agents'
default configuration as affected. Strands only strips prior-turn `reasoningContent` for
DeepSeek model IDs (`strands/models/bedrock.py`), not Kimi K3.

**Done:** `agent.py` registers a `StripPriorReasoning` hook (`BeforeModelCallEvent`) that
removes `reasoningContent` blocks from earlier assistant turns before every model call.
The harness forwards consumer hooks to sub-agents. Verified with a stubbed Converse stream
that returns reasoning + text: without the hook the second request contains
`reasoningContent`; with the hook it doesn't.

**To do:** run `python agent.py` twice in a row against Bedrock (the second run resumes the
session and replays earlier turns) and confirm neither run raises `InternalServerException`.
If it still does, fall back to the OpenAI-compatible Responses/Chat Completions path the
model card recommends.

## 2. Explicit prompt caching over Converse — resolved

`BedrockModel._cache_strategy` maps `strategy="auto"` to `None` for non-Claude model IDs, so
no `cachePoint` blocks are ever sent for Kimi K3; the only effect was a warning logged on
every request. `agent.py` now passes `caching=False`. Bedrock's automatic (implicit) prompt
caching for Kimi K3 still applies.

## 3. Context window — resolved

Strands has no built-in context window for Kimi K3 and falls back to 200K tokens, so the
harness's context manager would compact at ~170K. `agent.py` now calls
`agent.model.update_config(context_window_limit=1_000_000)`.

Note: sub-agents are rebuilt from the model string, so they still assume 200K. That only
matters if a delegated subtask needs more than ~170K tokens of context.
