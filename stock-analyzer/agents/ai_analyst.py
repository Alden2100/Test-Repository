"""
AI Analyst — Qwen via Ollama
Takes structured data from all agents and generates:
- Executive summary (3-4 sentences)
- Valuation commentary
- Risk narrative
- Key investment considerations
- Quick take bullets for the PDF cover

All prompts are tightly scoped so Qwen stays focused and fast.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from skills import llm


def _clean(text: str) -> str:
    """Remove markdown formatting and trim."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"^[-•]\s+", "", text, flags=re.MULTILINE)
    return text.strip()


def _parse_bullets(text: str, max_items: int = 4) -> list:
    """Extract bullet points from LLM output."""
    import re
    lines = text.strip().split("\n")
    bullets = []
    for line in lines:
        line = line.strip()
        # Strip common prefixes
        line = re.sub(r"^[\d]+\.\s+", "", line)
        line = re.sub(r"^[-•*]\s+", "", line)
        line = _clean(line)
        if len(line) > 20:
            bullets.append(line)
        if len(bullets) >= max_items:
            break
    return bullets


def generate_executive_summary(
    ticker: str,
    company_name: str,
    financial: dict,
    return_data: dict,
    risk: dict,
    macro: dict,
    model: str
) -> str:
    """Generate a 3-4 sentence executive summary of the investment case."""

    prompt = f"""You are a senior equity research analyst writing a brief investment summary.
Write exactly 3 sentences about {company_name} ({ticker}). Be specific, use the numbers provided. Do not use markdown.

Data:
- Revenue (TTM): {financial.get('revenue_ttm_fmt', 'N/A')}
- Operating margin: {financial.get('operating_margin_fmt', 'N/A')}
- Revenue growth YoY: {financial.get('revenue_growth_yoy_fmt', 'N/A')}
- Financial health: {financial.get('health_assessment', 'N/A')} ({financial.get('health_score', 'N/A')}/10)
- Valuation verdict: {return_data.get('valuation', {}).get('verdict', 'N/A')}
- Trailing P/E: {return_data.get('pe_ratio_fmt', 'N/A')}
- Current price: {return_data.get('current_price_fmt', 'N/A')}
- Overall risk: {risk.get('overall_risk', 'N/A')}
- Sector: {macro.get('sector_label', 'N/A')}

Write 3 clear, specific sentences covering: (1) what the company does and its financial scale, (2) how it is valued and key financial strengths or concerns, (3) the main risk or macro factor an investor should watch.

Do not use bullet points. Do not use headers. Just 3 sentences."""

    try:
        response = llm.call(prompt, model=model, temperature=0.3)
        return _clean(response)
    except Exception as e:
        return (
            f"{company_name} ({ticker}) generated {financial.get('revenue_ttm_fmt', 'N/A')} in trailing revenue "
            f"with {financial.get('operating_margin_fmt', 'N/A')} operating margins. "
            f"The stock is currently assessed as {return_data.get('valuation', {}).get('verdict', 'N/A')} "
            f"with an overall risk profile rated {risk.get('overall_risk', 'N/A')}. "
            f"Key macro context: {macro.get('macro_posture', 'monitor sector developments closely')}."
        )


def generate_valuation_commentary(
    ticker: str,
    return_data: dict,
    financial: dict,
    model: str
) -> str:
    """Generate 2-sentence valuation commentary."""

    val = return_data.get("valuation", {})
    prompt = f"""You are an equity analyst. Write exactly 2 sentences of valuation commentary for {ticker}. Be specific. No markdown, no headers, no bullets.

Data:
- Valuation verdict: {val.get('verdict', 'N/A')}
- Trailing P/E: {return_data.get('pe_ratio_fmt', 'N/A')}
- Forward P/E: {return_data.get('forward_pe_fmt', 'N/A')}
- EV/EBITDA: {return_data.get('ev_ebitda_fmt', 'N/A')}
- Sector benchmark P/E: {val.get('benchmarks_used', {}).get('pe', 'N/A')}x
- Sector benchmark EV/EBITDA: {val.get('benchmarks_used', {}).get('ev_ebitda', 'N/A')}x
- 52-week position: {return_data.get('positioning_52w', {}).get('label', 'N/A')}
- Revenue growth: {financial.get('revenue_growth_yoy_fmt', 'N/A')}

Sentence 1: State the current valuation level vs sector peers using the specific multiples.
Sentence 2: Explain what would need to be true for the valuation to be justified or what risk it creates."""

    try:
        response = llm.call(prompt, model=model, temperature=0.3)
        return _clean(response)
    except Exception as e:
        signals = val.get("signals", [])
        return signals[0] if signals else f"{ticker} valuation data requires further analysis."


def generate_risk_narrative(
    ticker: str,
    risk: dict,
    model: str
) -> str:
    """Generate a concise risk narrative."""

    prompt = f"""You are a risk analyst. Write exactly 2 sentences summarizing the risk profile of {ticker}. Be specific. No markdown.

Data:
- Overall risk: {risk.get('overall_risk', 'N/A')} (score: {risk.get('risk_score', 'N/A')}/10)
- Leverage risk: {risk.get('leverage', {}).get('risk_level', 'N/A')} — {risk.get('leverage', {}).get('details', ['N/A'])[0]}
- Volatility risk: {risk.get('volatility', {}).get('risk_level', 'N/A')} — {risk.get('volatility', {}).get('details', ['N/A'])[0]}
- Profitability risk: {risk.get('profitability_risk', {}).get('risk_level', 'N/A')} — {risk.get('profitability_risk', {}).get('details', ['N/A'])[0]}
- Top risks: {'; '.join(risk.get('top_risks', ['N/A']))}

Sentence 1: Summarize the overall risk level and the single most important risk factor.
Sentence 2: Describe what the risk means for an investor holding this stock."""

    try:
        response = llm.call(prompt, model=model, temperature=0.3)
        return _clean(response)
    except Exception as e:
        top = risk.get("top_risks", [])
        return top[0] if top else f"{ticker} risk profile requires further analysis."


def generate_investment_considerations(
    ticker: str,
    financial: dict,
    return_data: dict,
    risk: dict,
    macro: dict,
    model: str
) -> list:
    """Generate 4 key investment considerations (2 bull, 2 bear)."""

    prompt = f"""You are an equity analyst preparing an investment brief for {ticker}.
List exactly 4 key investment considerations: 2 bull case points and 2 bear case points.
Each point must be one sentence, specific, and use the data provided.
Format: start each line with BULL: or BEAR: followed by the point. No other text.

Data:
- Revenue: {financial.get('revenue_ttm_fmt', 'N/A')}, growth: {financial.get('revenue_growth_yoy_fmt', 'N/A')}
- Operating margin: {financial.get('operating_margin_fmt', 'N/A')}
- Free cash flow: {financial.get('free_cashflow_fmt', 'N/A')}
- Health positives: {'; '.join(financial.get('health_positives', []))}
- Health flags: {'; '.join(financial.get('health_flags', []))}
- Valuation: {return_data.get('valuation', {}).get('verdict', 'N/A')}
- P/E: {return_data.get('pe_ratio_fmt', 'N/A')}
- Risk: {risk.get('overall_risk', 'N/A')}
- Top risks: {'; '.join(risk.get('top_risks', []))}
- Macro tailwinds: {macro.get('tailwinds', ['N/A'])[0]}
- Macro headwinds: {macro.get('headwinds', ['N/A'])[0]}"""

    try:
        response = llm.call(prompt, model=model, temperature=0.4)
        lines = response.strip().split("\n")
        considerations = []
        for line in lines:
            line = line.strip()
            if line.upper().startswith("BULL:"):
                considerations.append(("bull", _clean(line[5:].strip())))
            elif line.upper().startswith("BEAR:"):
                considerations.append(("bear", _clean(line[5:].strip())))
        return considerations[:4]
    except Exception as e:
        return [
            ("bull", financial.get("health_positives", ["Strong financial profile"])[0]),
            ("bull", macro.get("tailwinds", ["Favorable sector tailwinds"])[0]),
            ("bear", risk.get("top_risks", ["Elevated market risk"])[0]),
            ("bear", macro.get("headwinds", ["Macro headwinds present"])[0]),
        ]


def generate_quick_take_bullets(
    ticker: str,
    financial: dict,
    return_data: dict,
    risk: dict,
    macro: dict,
    model: str
) -> list:
    """
    Generate 4 sharp one-line bullets for the PDF cover page Quick Take section.
    Returns list of (tag, text, color_hint) tuples.
    """

    prompt = f"""Write 4 sharp, specific one-line insights about {ticker} for an investment brief cover page.
Each must be under 15 words. Label each with its category.
Format exactly as: VALUATION: <insight> | RISK: <insight> | FINANCIALS: <insight> | MACRO: <insight>
Use the data below. No markdown, no extra text.

- Revenue: {financial.get('revenue_ttm_fmt', 'N/A')}, margin: {financial.get('operating_margin_fmt', 'N/A')}, growth: {financial.get('revenue_growth_yoy_fmt', 'N/A')}
- Valuation: {return_data.get('valuation', {}).get('verdict', 'N/A')}, P/E {return_data.get('pe_ratio_fmt', 'N/A')}
- 52-week: {return_data.get('positioning_52w', {}).get('label', 'N/A')}
- Risk: {risk.get('overall_risk', 'N/A')}, beta {risk.get('beta_fmt', 'N/A')}
- Macro: {macro.get('tailwinds', ['N/A'])[0][:60]}"""

    try:
        response = llm.call(prompt, model=model, temperature=0.3)
        # Parse the pipe-separated format
        parts = response.split("|")
        result = []
        color_map = {"VALUATION": "val", "RISK": "risk", "FINANCIALS": "fin", "MACRO": "macro"}
        for part in parts:
            part = part.strip()
            if ":" in part:
                tag, text = part.split(":", 1)
                tag = tag.strip().upper()
                text = _clean(text.strip())
                if tag in color_map and len(text) > 5:
                    result.append((tag.title(), text, color_map[tag]))
        if len(result) >= 2:
            return result[:4]
    except Exception:
        pass

    # Fallback to structured data
    return [
        ("Valuation", return_data.get("valuation", {}).get("signals", ["N/A"])[0] if return_data.get("valuation", {}).get("signals") else "N/A", "val"),
        ("Risk", risk.get("top_risks", ["N/A"])[0], "risk"),
        ("Financials", financial.get("health_positives", ["N/A"])[0] if financial.get("health_positives") else "N/A", "fin"),
        ("Macro", macro.get("tailwinds", ["N/A"])[0][:80], "macro"),
    ]


def run(
    financial: dict,
    return_data: dict,
    risk: dict,
    macro: dict,
    model: str = llm.DEFAULT_MODEL
) -> dict:
    """
    Master function. Runs all AI commentary generation.
    Returns a dict of narrative strings consumed by the PDF builder.
    """
    ticker = financial.get("ticker", "UNKNOWN")
    company_name = financial.get("company_name", ticker)

    print(f"[ai_analyst] Generating AI commentary for {ticker} using {model}...")

    print("  → Executive summary...")
    summary = generate_executive_summary(ticker, company_name, financial, return_data, risk, macro, model)

    print("  → Valuation commentary...")
    val_commentary = generate_valuation_commentary(ticker, return_data, financial, model)

    print("  → Risk narrative...")
    risk_narrative = generate_risk_narrative(ticker, risk, model)

    print("  → Investment considerations...")
    considerations = generate_investment_considerations(ticker, financial, return_data, risk, macro, model)

    print("  → Quick take bullets...")
    quick_take = generate_quick_take_bullets(ticker, financial, return_data, risk, macro, model)

    print(f"[ai_analyst] Done.")

    return {
        "executive_summary": summary,
        "valuation_commentary": val_commentary,
        "risk_narrative": risk_narrative,
        "investment_considerations": considerations,
        "quick_take_bullets": quick_take,
    }
