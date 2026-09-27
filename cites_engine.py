"""Core logic: turn a free-text wildlife-trade question into a structured
CITES compliance assessment via the Claude API.

This is a portfolio prototype, not a compliance tool - see the disclaimer
rendered in app.py. Claude's CITES-appendix knowledge is not guaranteed to be
current for every species and every country's domestic rules; the prompt
instructs the model to say so explicitly whenever it is not confident.
"""

import os
from typing import List, Literal

import anthropic
from pydantic import BaseModel, Field, field_validator

MODEL_ID = "claude-opus-5"

SYSTEM_PROMPT = """You are CITES Wildlife Trade Copilot, an educational assistant that \
helps a non-expert understand whether moving a live animal, plant, or wildlife \
product across borders is likely to be restricted under CITES (the Convention \
on International Trade in Endangered Species) and related national rules.

You are NOT a customs broker or lawyer, and your output is a prototype for a \
product-design demo, not legal advice. Follow these rules:

1. Identify the species as specifically as the user's wording allows. If the \
   common name is ambiguous (e.g. "turtle" covers hundreds of species with \
   different CITES status), say so explicitly and give your best guess plus \
   the most likely alternatives, rather than picking one silently.
2. Give the CITES Appendix (I, II, III, or "Not listed") for your best-guess \
   species. If you are not confident, set appendix to "Uncertain" and explain \
   why in appendix_explanation - never state an appendix level you are not \
   reasonably sure of.
3. Explain trade restrictions in plain language: Appendix I generally bans \
   commercial international trade of wild-caught specimens (import AND export \
   permits, and only for non-commercial purposes in most cases); Appendix II \
   requires an export permit from the origin country (and generally no import \
   permit needed) proving the trade won't harm the species' survival; \
   Appendix III requires an export permit only from the specific listing \
   country. Domestic/national laws can be stricter than CITES itself - flag \
   this.
4. List the permits/documents a traveler would realistically need to check \
   for, not just CITES ones (e.g. an export permit from the country of origin, \
   an import permit if required by the destination country, proof of legal \
   acquisition, and any additional national wildlife-protection permits).
5. risk_warnings should call out concrete consequences (confiscation, fines, \
   criminal prosecution for illegal wildlife trade) and any special traps \
   (e.g. captive-bred vs wild-caught status changes the rules; some countries \
   ban a species domestically even if CITES itself would allow trade).
6. sources must point the user to where to verify, not to your own certainty: \
   always include the CITES Species+ database (https://speciesplus.net), the \
   official CITES Appendices (https://cites.org/eng/app/appendices.php), and \
   the destination country's national CITES Management Authority. Add other \
   sources only if clearly relevant.
7. plain_summary is a 2-4 sentence, non-technical answer to the user's exact \
   question, written the way you'd actually tell a friend - lead with the \
   practical bottom line (likely fine / likely restricted / depends on X), \
   then the single biggest caveat.

Always fill in every field. When genuinely uncertain, say so in the field \
itself rather than inventing false precision.
"""


def _normalize_confidence(value: object) -> object:
    if not isinstance(value, str):
        return value
    v = value.strip().lower()
    if v.startswith("high"):
        return "high"
    if v.startswith("low"):
        return "low"
    return "medium"


def _normalize_appendix(value: object) -> object:
    if not isinstance(value, str):
        return value
    v = value.strip().lower()
    # Claude occasionally adds trailing notes, e.g. "II (with reservations)"
    if v.startswith("not listed") or v.startswith("none"):
        return "Not listed"
    if v.startswith("iii"):
        return "III"
    if v.startswith("ii"):
        return "II"
    if v.startswith("i"):
        return "I"
    return "Uncertain"


class SpeciesIdentification(BaseModel):
    user_mentioned: str = Field(description="The species/animal exactly as the user described it")
    likely_common_name: str = Field(description="Best-guess specific common name, e.g. 'Red-eared slider turtle'")
    likely_scientific_name: str = Field(description="Best-guess scientific (Latin) name")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in this species identification")
    note: str = Field(description="One sentence on ambiguity, e.g. other likely species this could be")

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v):
        return _normalize_confidence(v)


class CitesAssessment(BaseModel):
    plain_summary: str = Field(description="2-4 sentence plain-language bottom-line answer")
    species_identification: SpeciesIdentification
    cites_appendix: Literal["I", "II", "III", "Not listed", "Uncertain"]
    appendix_explanation: str = Field(description="Why this appendix level, in plain language")
    trade_restrictions: str = Field(description="What is and isn't allowed, in plain language")
    required_permits: List[str] = Field(description="Concrete permits/documents to check for")
    risk_warnings: List[str] = Field(description="Concrete risks and traps to be aware of")
    sources: List[str] = Field(description="Where to verify this, e.g. official CITES/Species+ links")

    @field_validator("cites_appendix", mode="before")
    @classmethod
    def _coerce_appendix(cls, v):
        return _normalize_appendix(v)

    @field_validator("required_permits", "risk_warnings", "sources", mode="before")
    @classmethod
    def _coerce_to_list(cls, v):
        # Claude occasionally collapses a bulleted list into one string
        if isinstance(v, str):
            return [v]
        return v


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def assess_query(client: anthropic.Anthropic, user_question: str) -> CitesAssessment:
    """Send the user's free-text question to Claude and get back a validated
    CitesAssessment. Raises on API errors - the caller (app.py) is responsible
    for catching and displaying them."""
    response = client.messages.parse(
        model=MODEL_ID,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_question}],
        output_format=CitesAssessment,
    )
    return response.parsed_output
