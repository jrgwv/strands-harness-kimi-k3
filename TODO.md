# TODO — verify against live Bedrock before publishing

No AWS credentials were available in the review environment, so these two items are
confirmed only via source inspection (`strands-harness` 0.1.2) and the AWS Kimi K3
model card, not by running the agent. Both need a real run against Bedrock.

## 1. Converse API + multi-turn reasoning content

The harness's `bedrock/` provider builds a `strands.models.bedrock.BedrockModel`, which
calls the Converse API. The Kimi K3 model card's "Usage Considerations" section says:

> **Prefer the OpenAI-compatible APIs over Converse** — Although Kimi K3 can be called
> through the Converse and ConverseStream APIs, we recommend using the OpenAI-compatible
> Responses or Chat Completions APIs where possible. Converse has known limitations with
> this model, including a failure (`InternalServerException`) when reasoning content from
> earlier turns is included in a multi-turn request, which affects frameworks such as
> LangChain and Strands Agents in their default configurations, and rejection of attached
> document inputs such as PDF and HTML.

`agent.py` is multi-turn by construction (an agent loop, plus `session={"id":
"kimi-k3-demo"}` specifically so re-runs replay prior turns).

Mitigating factor: the harness reports `supports_thinking()` as `False` for this model
(`_bedrock_levels("moonshotai.kimi-k3")` is empty), so the harness itself never requests
reasoning output. Whether Kimi K3 emits reasoning content on Converse anyway,
independent of the harness's thinking config, is the open question.

**To do:** run `python agent.py` twice in a row (second run resumes the session and
replays turn 1) and confirm neither run raises `InternalServerException`. If it does,
switch the example to the OpenAI-compatible path: set `OPENAI_BASE_URL` to
`https://bedrock-runtime.{region}.amazonaws.com/openai/v1`, authenticate with
`aws_bedrock_token_generator.provide_token()`, and use `model="openai/moonshotai.kimi-k3"`
(or however the harness's `openai` provider expects the id) instead of `bedrock/...`.

## 2. Explicit prompt caching over Converse

The harness defaults `caching=True` for every Bedrock model except Claude 3 Haiku, so
Kimi K3 gets a `CacheConfig` with `cachePoint` blocks over Converse. The model card lists
explicit prompt caching as supported only on "Responses and Chat Completions APIs" — not
Converse.

**To do:** run the agent and check for a caching-related error or a silently ignored
cache config. If it errors or clutters the trace, pass `caching=False` to `create_harness`
in `agent.py` and note in the README why (implicit caching, which Bedrock does
automatically for Kimi K3 regardless of this setting, still applies).
