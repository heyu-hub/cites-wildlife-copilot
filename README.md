# CITES Wildlife Trade Copilot

An AI product demo: paste in a plain-language wildlife-trade question ("I want
to buy a turtle in Thailand and bring it to Singapore, is that legal?") and get
back a structured assessment - species identification, CITES Appendix level,
trade restrictions, required permits, risk warnings, and sources to verify.

**This is a portfolio prototype, not a compliance tool.** Always verify with
the official [CITES Species+ database](https://speciesplus.net) and the
destination country's CITES Management Authority before actually moving any
wildlife or wildlife product across a border.

## Why this exists

Built as a small product-design exercise: define the problem (non-experts
can't quickly parse CITES trade rules), design the interaction flow (free-text
question -> species identification -> rule lookup -> structured answer), and
implement it end-to-end with Claude Code + the Claude API + Streamlit.

## Architecture

- `cites_engine.py` - the product logic. Defines the structured output schema
  (`CitesAssessment`, a Pydantic model) and the system prompt that constrains
  Claude to fill it in conservatively (flag uncertainty instead of guessing).
  Uses `client.messages.parse()` so the API response is validated against the
  schema before the UI ever sees it.
- `app.py` - the Streamlit UI: input box, example questions, and a rendered
  breakdown of every field in the structured response.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your own key from https://console.anthropic.com/settings/keys
```

## Run

```bash
source venv/bin/activate
streamlit run app.py
```

Opens at http://localhost:8501.

## Notes on the model

Uses `claude-opus-5` by default. For a demo you'll be testing repeatedly
during development, swapping `MODEL_ID` in `cites_engine.py` to
`claude-sonnet-5` or `claude-haiku-4-5` cuts cost significantly with only a
modest quality tradeoff for this task - see pricing at
https://docs.claude.com/en/docs/about-claude/pricing.
