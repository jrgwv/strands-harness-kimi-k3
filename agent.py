"""
Strands harness + Kimi K3 on Amazon Bedrock.

Prerequisites:
- AWS account with Amazon Bedrock access
- IAM permissions for bedrock:InvokeModel and bedrock:InvokeModelWithResponseStream
  on the Kimi K3 inference profile and model
- AWS credentials configured (aws configure, IAM Identity Center, or an instance role)
- Python 3.10+ and `pip install -r requirements.txt`

Run from a directory that contains some markdown docs:
    python agent.py
"""

from strands_harness import create_harness

# "bedrock/" selects the Bedrock provider; the rest is the inference profile ID.
# Use "us.moonshotai.kimi-k3" instead to keep inference in US Regions.
MODEL_ID = "bedrock/global.moonshotai.kimi-k3"

agent = create_harness(
    model=MODEL_ID,
    # A fixed session ID lets you re-run the script and continue the same conversation.
    # Sessions are stored under ./.agent/sessions by default.
    session={"id": "kimi-k3-demo"},
    builtin_tools={
        # Kimi K3 has no native web search in Bedrock. To enable search through Exa
        # (third party, keyless free tier; set EXA_API_KEY to lift the rate limit), uncomment:
        # "web_search": "exa",
        # The harness can't identify Kimi K3's family to pick a small web_fetch summarizer,
        # so left alone it falls back to Kimi K3 itself -- a 1M-context model summarizing
        # single web pages. Pin a cheap Bedrock summarizer instead (same AWS credentials).
        "web_fetch": {"model": "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"},
    },
)

TASK = (
    "Read every markdown file in this directory, summarize what each one covers, "
    "and write a combined overview to SUMMARY.md."
)

if __name__ == "__main__":
    agent(TASK)
