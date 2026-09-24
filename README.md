# strands-harness-kimi-k3

A minimal example of [Strands harness](https://strandsagents.com/blog/introducing-strands-harness/),
the open-source agent runtime from the Strands Agents team at AWS, running on
[Kimi K3](https://aws.amazon.com/blogs/machine-learning/introducing-kimi-k3-on-amazon-bedrock/),
Moonshot AI's 1M-token model in Amazon Bedrock.

Companion code for the blog post *Building agents with Strands harness and Kimi K3 in Amazon Bedrock*.

## Prerequisites

- An AWS account with access to Amazon Bedrock
- IAM permissions for `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the Kimi K3 inference profile and model
- AWS credentials configured (`aws configure`, IAM Identity Center, or an instance role)
- Python 3.10 or later

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Optionally copy `.env.example` to `.env` to pin a Region; otherwise the harness uses your standard AWS configuration.

## Run

Put a few markdown files in the directory (or run from a project's `docs/` folder), then:

```bash
python agent.py
```

The agent reads each markdown file and writes a combined overview to `SUMMARY.md`.

`agent.py` selects the model with `model="bedrock/global.moonshotai.kimi-k3"`. The `bedrock/` prefix picks the Bedrock provider and the rest is the inference profile ID.

## Resume a session

`agent.py` uses a fixed `session={"id": "kimi-k3-demo"}`, so running it again continues the same conversation. Change the ID to start fresh. Sessions are stored under `./.agent/sessions`.

## Web search

Kimi K3 has no native web search in Bedrock, so the harness disables that tool and logs a warning at startup. To search through Exa (third party, keyless free tier; set `EXA_API_KEY` to lift the rate limit), uncomment the `builtin_tools` line in `agent.py`.

## Kimi K3 inference profiles

| Profile | ID | Coverage |
|---|---|---|
| US | `us.moonshotai.kimi-k3` | US Regions and Canada (Central) |
| Global | `global.moonshotai.kimi-k3` | US, Canada, Europe, Asia Pacific, and more; about 10% cheaper |

Source: [Kimi K3 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-moonshot-ai-kimi-k3.html)

## Clean up

Nothing to tear down: Bedrock bills per token. Delete the local `.agent/` folder to remove saved sessions.

## Links

- [Introducing Strands harness](https://strandsagents.com/blog/introducing-strands-harness/)
- [Strands harness quickstart](https://strandsagents.com/docs/user-guide/harness/quickstart/)
- [Strands Harness SDK on GitHub](https://github.com/strands-agents/harness-sdk)
- [Introducing Kimi K3 on Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/introducing-kimi-k3-on-amazon-bedrock/)
- [Kimi K3 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-moonshot-ai-kimi-k3.html)

## License

Apache License 2.0. See [LICENSE](LICENSE).
