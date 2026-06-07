"""
Financial Analysis Agent
Analyzes financial health using SEC XBRL facts and key statistics.
Produces a structured financial summary consumed by the orchestrator.
"""

import json
import os
import sys
import urllib.request

# Add skills dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _safe(val, fallback="N/A"):
    if val is None or val == "":
        return fallback
    return val


def _fmt_million(val) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e12:
            return f"${v/1e12:.2f}T"
        elif abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        elif abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        else:
            return f"${v:,.0f}"
    except Exception:
        return "N/A"


def _fmt_pct(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val)*100:.1f}%"
    except Exception:
        return "N/A"


def _fmt_multiple(val, suffix="x") -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1f}{suffix}"
    except Exception:
        return "N/A"


def extract_revenue_trend(sec_facts: dict) -> list:
    """Pull last 3 years of annual revenue from SEC XBRL facts."""
    revenues = sec_facts.get("revenue") or sec_facts.get("revenue_alt", [])
    if not revenues:
        return []
    trend = []
    for entry in revenues[-3:]:
        trend.append({
            "year": entry.get("end", "")[:4],
            "value": entry.get("val", 0),
            "formatted": _fmt_million(entry.get("val"))
        })
    return trend


def extract_income_trend(sec_facts: dict) -> list:
    """Pull last 3 years of net income from SEC XBRL facts."""
    incomes = sec_facts.get("net_income", [])
    trend = []
    for entry in incomes[-3:]:
        trend.append({
            "year": entry.get("end", "")[:4],
            "value": entry.get("val", 0),
            "formatted": _fmt_million(entry.get("val"))
        })
    return trend


def score_financial_health(stats: dict) -> dict:
    """
    Simple scoring of financial health.
    Returns score 1-10 and qualitative assessment.
    """
    score = 5  # Start neutral
    flags = []
    positives = []
    
    # Profitability
    op_margin = stats.get("operating_margin")
    if op_margin is not None:
        if op_margin > 0.20:
            score += 1.5
            positives.append(f"Strong operating margin ({_fmt_pct(op_margin)})")
        elif op_margin > 0.10:
            score += 0.5
            positives.append(f"Healthy operating margin ({_fmt_pct(op_margin)})")
        elif op_margin < 0:
            score -= 2
            flags.append(f"Negative operating margin ({_fmt_pct(op_margin)})")
        else:
            flags.append(f"Thin operating margin ({_fmt_pct(op_margin)})")
    
    # Return on equity
    roe = stats.get("return_on_equity")
    if roe is not None:
        if roe > 0.20:
            score += 1
            positives.append(f"High ROE ({_fmt_pct(roe)})")
        elif roe < 0:
            score -= 1
            flags.append(f"Negative ROE ({_fmt_pct(roe)})")
    
    # Revenue growth
    rev_growth = stats.get("revenue_growth")
    if rev_growth is not None:
        if rev_growth > 0.15:
            score += 1
            positives.append(f"Strong revenue growth ({_fmt_pct(rev_growth)} YoY)")
        elif rev_growth > 0.05:
            score += 0.5
            positives.append(f"Moderate revenue growth ({_fmt_pct(rev_growth)} YoY)")
        elif rev_growth < 0:
            score -= 1
            flags.append(f"Revenue declining ({_fmt_pct(rev_growth)} YoY)")
    
    # Debt check
    total_debt = stats.get("total_debt")
    total_cash = stats.get("total_cash")
    ebitda = stats.get("ebitda")
    if total_debt and ebitda and ebitda > 0:
        leverage = total_debt / ebitda
        if leverage < 2:
            score += 0.5
            positives.append(f"Conservative leverage ({leverage:.1f}x Debt/EBITDA)")
        elif leverage > 5:
            score -= 1
            flags.append(f"High leverage ({leverage:.1f}x Debt/EBITDA)")
    
    # Free cash flow
    fcf = stats.get("free_cashflow")
    if fcf is not None:
        if fcf > 0:
            positives.append(f"Positive free cash flow ({_fmt_million(fcf)})")
        else:
            flags.append(f"Negative free cash flow ({_fmt_million(fcf)})")
    
    score = max(1, min(10, round(score, 1)))
    
    if score >= 7.5:
        assessment = "Strong"
    elif score >= 5.5:
        assessment = "Solid"
    elif score >= 3.5:
        assessment = "Mixed"
    else:
        assessment = "Weak"
    
    return {
        "score": score,
        "assessment": assessment,
        "positives": positives[:3],
        "flags": flags[:3]
    }


def run(research_data: dict) -> dict:
    """
    Main entry point for the financial analysis agent.
    Input: research_data from web_research skill
    Output: structured financial analysis dict
    """
    ticker = research_data.get("ticker", "UNKNOWN")
    company_name = research_data.get("company_name", ticker)
    stats = research_data.get("stats", {})
    sec_facts = research_data.get("sec_facts", {})
    market = research_data.get("market", {})

    print(f"[financial_agent] Analyzing financials for {ticker}...")

    # Revenue and income trends from SEC XBRL
    revenue_trend = extract_revenue_trend(sec_facts)
    income_trend = extract_income_trend(sec_facts)

    # Compute revenue CAGR if 3 years available
    rev_cagr = None
    if len(revenue_trend) >= 2:
        try:
            v_start = revenue_trend[0]["value"]
            v_end = revenue_trend[-1]["value"]
            n = len(revenue_trend) - 1
            if v_start > 0:
                rev_cagr = (v_end / v_start) ** (1 / n) - 1
        except Exception:
            pass

    # Balance sheet
    total_debt = stats.get("total_debt")
    total_cash = stats.get("total_cash")
    net_cash = None
    if total_debt is not None and total_cash is not None:
        net_cash = total_cash - total_debt

    # Health scoring
    health = score_financial_health(stats)

    result = {
        "agent": "financial_analysis",
        "ticker": ticker,
        "company_name": company_name,

        # Income statement
        "revenue_ttm": stats.get("revenue_ttm"),
        "revenue_ttm_fmt": _fmt_million(stats.get("revenue_ttm")),
        "ebitda": stats.get("ebitda"),
        "ebitda_fmt": _fmt_million(stats.get("ebitda")),
        "free_cashflow": stats.get("free_cashflow"),
        "free_cashflow_fmt": _fmt_million(stats.get("free_cashflow")),

        # Margins
        "gross_margin": stats.get("gross_margin"),
        "gross_margin_fmt": _fmt_pct(stats.get("gross_margin")),
        "operating_margin": stats.get("operating_margin"),
        "operating_margin_fmt": _fmt_pct(stats.get("operating_margin")),
        "profit_margin": stats.get("profit_margin"),
        "profit_margin_fmt": _fmt_pct(stats.get("profit_margin")),

        # Returns
        "roe": stats.get("return_on_equity"),
        "roe_fmt": _fmt_pct(stats.get("return_on_equity")),
        "roa": stats.get("return_on_assets"),
        "roa_fmt": _fmt_pct(stats.get("return_on_assets")),

        # Growth
        "revenue_growth_yoy": stats.get("revenue_growth"),
        "revenue_growth_yoy_fmt": _fmt_pct(stats.get("revenue_growth")),
        "earnings_growth_yoy": stats.get("earnings_growth"),
        "earnings_growth_yoy_fmt": _fmt_pct(stats.get("earnings_growth")),
        "revenue_cagr_3yr": rev_cagr,
        "revenue_cagr_3yr_fmt": _fmt_pct(rev_cagr),

        # Balance sheet
        "total_debt": total_debt,
        "total_debt_fmt": _fmt_million(total_debt),
        "total_cash": total_cash,
        "total_cash_fmt": _fmt_million(total_cash),
        "net_cash": net_cash,
        "net_cash_fmt": _fmt_million(net_cash),

        # Historical trends (for sparklines / table)
        "revenue_trend": revenue_trend,
        "income_trend": income_trend,

        # Health score
        "health_score": health["score"],
        "health_assessment": health["assessment"],
        "health_positives": health["positives"],
        "health_flags": health["flags"],

        # Filing links
        "filing_10k_url": research_data.get("filing_10k", {}).get("url") if research_data.get("filing_10k") else None,
        "filing_10k_date": research_data.get("filing_10k", {}).get("filing_date") if research_data.get("filing_10k") else None,
    }

    print(f"[financial_agent] Done. Health: {health['assessment']} ({health['score']}/10)")
    return result


if __name__ == "__main__":
    # For testing
    import sys, json
    from skills import web_research
    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    research = web_research.research_ticker(ticker)
    output = run(research)
    print(json.dumps(output, indent=2, default=str))
