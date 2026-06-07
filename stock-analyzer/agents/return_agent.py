"""
Return Analysis Agent
Evaluates valuation multiples, implied upside/downside,
and return profile relative to sector benchmarks.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


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


def _fmt_price(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"${float(val):.2f}"
    except Exception:
        return "N/A"


# Sector benchmark multiples (P/E, EV/EBITDA, EV/Revenue)
# Used to assess whether a stock is cheap, fair, or expensive
SECTOR_BENCHMARKS = {
    "technology":       {"pe": 28, "ev_ebitda": 20, "ev_rev": 6,  "label": "Technology"},
    "healthcare":       {"pe": 22, "ev_ebitda": 15, "ev_rev": 4,  "label": "Healthcare"},
    "financials":       {"pe": 14, "ev_ebitda": 12, "ev_rev": 3,  "label": "Financials"},
    "consumer_staples": {"pe": 22, "ev_ebitda": 14, "ev_rev": 1.5,"label": "Consumer Staples"},
    "consumer_disc":    {"pe": 24, "ev_ebitda": 15, "ev_rev": 2,  "label": "Consumer Discretionary"},
    "industrials":      {"pe": 20, "ev_ebitda": 12, "ev_rev": 2,  "label": "Industrials"},
    "energy":           {"pe": 12, "ev_ebitda": 7,  "ev_rev": 1.5,"label": "Energy"},
    "utilities":        {"pe": 17, "ev_ebitda": 10, "ev_rev": 2,  "label": "Utilities"},
    "real_estate":      {"pe": 35, "ev_ebitda": 20, "ev_rev": 7,  "label": "Real Estate"},
    "materials":        {"pe": 18, "ev_ebitda": 11, "ev_rev": 2,  "label": "Materials"},
    "default":          {"pe": 20, "ev_ebitda": 13, "ev_rev": 3,  "label": "Market Average"},
}


def infer_sector(company_name: str, ticker: str) -> str:
    """
    Rough sector inference from ticker/name.
    In production this would use an API lookup.
    """
    name_lower = (company_name + " " + ticker).lower()
    
    tech_signals = ["tech", "software", "micro", "apple", "google", "meta", "amazon",
                    "nvidia", "intel", "cisco", "oracle", "salesforce", "msft", "aapl",
                    "googl", "amzn", "nvda", "intc", "crm", "adbe", "now", "snow"]
    health_signals = ["pharma", "bio", "health", "medical", "therapeut", "oncol",
                      "jnj", "pfe", "mrk", "abbv", "lly", "bmy", "amgn", "gild"]
    fin_signals = ["bank", "financial", "insurance", "capital", "credit", "invest",
                   "jpm", "bac", "wfc", "gs", "ms", "c", "usb", "pnc"]
    energy_signals = ["oil", "gas", "energy", "petroleum", "exxon", "chevron",
                      "xom", "cvx", "cop", "slb", "mpc", "psx"]
    consumer_signals = ["consumer", "retail", "food", "beverage", "walmart", "target",
                        "wmt", "tgt", "cost", "ko", "pep", "pg", "mnst"]
    
    for signal in tech_signals:
        if signal in name_lower:
            return "technology"
    for signal in health_signals:
        if signal in name_lower:
            return "healthcare"
    for signal in fin_signals:
        if signal in name_lower:
            return "financials"
    for signal in energy_signals:
        if signal in name_lower:
            return "energy"
    for signal in consumer_signals:
        if signal in name_lower:
            return "consumer_staples"
    
    return "default"


def assess_valuation(stats: dict, market: dict, sector: str) -> dict:
    """
    Compare current multiples vs sector benchmarks.
    Returns valuation assessment and implied upside/downside.
    """
    benchmarks = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["default"])
    
    pe = _safe_float(stats.get("pe_ratio"))
    fwd_pe = _safe_float(stats.get("forward_pe"))
    ev_ebitda = _safe_float(stats.get("ev_to_ebitda"))
    ev_rev = _safe_float(stats.get("ev_to_revenue"))
    peg = _safe_float(stats.get("peg_ratio"))
    price = _safe_float(market.get("current_price"))
    
    signals = []
    premium_discount_signals = []
    
    # P/E vs benchmark
    if pe and pe > 0:
        pe_vs = (pe / benchmarks["pe"] - 1)
        if pe_vs > 0.30:
            signals.append(f"Trading at {pe_vs*100:.0f}% premium to sector on P/E")
        elif pe_vs < -0.20:
            signals.append(f"Trading at {abs(pe_vs)*100:.0f}% discount to sector on P/E")
        else:
            signals.append(f"P/E roughly in-line with sector ({pe:.1f}x vs {benchmarks['pe']}x benchmark)")
        premium_discount_signals.append(pe_vs)
    
    # EV/EBITDA vs benchmark
    if ev_ebitda and ev_ebitda > 0:
        ev_vs = (ev_ebitda / benchmarks["ev_ebitda"] - 1)
        if ev_vs > 0.30:
            signals.append(f"EV/EBITDA premium of {ev_vs*100:.0f}% to sector")
        elif ev_vs < -0.20:
            signals.append(f"EV/EBITDA discount of {abs(ev_vs)*100:.0f}% to sector")
        else:
            signals.append(f"EV/EBITDA in-line with sector ({ev_ebitda:.1f}x vs {benchmarks['ev_ebitda']}x benchmark)")
        premium_discount_signals.append(ev_vs)
    
    # PEG ratio assessment
    if peg and peg > 0:
        if peg < 1.0:
            signals.append(f"PEG ratio of {peg:.2f}x suggests growth may not be fully priced in")
        elif peg > 2.0:
            signals.append(f"PEG ratio of {peg:.2f}x suggests elevated growth expectations")
    
    # Overall premium/discount
    avg_premium = sum(premium_discount_signals) / len(premium_discount_signals) if premium_discount_signals else 0
    
    # Implied fair value from sector average P/E (rough)
    implied_price_pe = None
    implied_upside_pe = None
    if pe and price and pe > 0:
        # If forward P/E, use that; else trailing
        target_pe = fwd_pe if fwd_pe and fwd_pe > 0 else pe
        implied_price_pe = price * (benchmarks["pe"] / target_pe)
        implied_upside_pe = (implied_price_pe / price) - 1
    
    # Valuation verdict
    if avg_premium > 0.25:
        verdict = "Expensive"
        verdict_color = "red"
    elif avg_premium > 0.10:
        verdict = "Slightly Elevated"
        verdict_color = "orange"
    elif avg_premium < -0.20:
        verdict = "Attractive"
        verdict_color = "green"
    elif avg_premium < -0.08:
        verdict = "Modestly Undervalued"
        verdict_color = "green"
    else:
        verdict = "Fairly Valued"
        verdict_color = "neutral"
    
    return {
        "verdict": verdict,
        "verdict_color": verdict_color,
        "sector": SECTOR_BENCHMARKS.get(sector, {}).get("label", "General Market"),
        "avg_premium_discount": avg_premium,
        "avg_premium_discount_fmt": _fmt_pct(avg_premium),
        "signals": signals,
        "implied_price_pe": implied_price_pe,
        "implied_price_pe_fmt": _fmt_price(implied_price_pe),
        "implied_upside_pe": implied_upside_pe,
        "implied_upside_pe_fmt": _fmt_pct(implied_upside_pe),
        "benchmarks_used": benchmarks,
    }


def assess_52w_positioning(market: dict) -> dict:
    """Where is the stock trading in its 52-week range?"""
    price = _safe_float(market.get("current_price"))
    high = _safe_float(market.get("fifty_two_week_high"))
    low = _safe_float(market.get("fifty_two_week_low"))
    
    if not all([price, high, low]) or (high - low) == 0:
        return {"position_pct": None, "label": "N/A", "from_high_pct": None, "from_low_pct": None}
    
    position_pct = (price - low) / (high - low)
    from_high = (price / high) - 1
    from_low = (price / low) - 1
    
    if position_pct > 0.85:
        label = "Near 52-week high"
    elif position_pct > 0.60:
        label = "Upper range"
    elif position_pct > 0.40:
        label = "Mid range"
    elif position_pct > 0.20:
        label = "Lower range"
    else:
        label = "Near 52-week low"
    
    return {
        "position_pct": position_pct,
        "position_pct_fmt": f"{position_pct*100:.0f}% of 52w range",
        "label": label,
        "from_high_pct": from_high,
        "from_high_pct_fmt": _fmt_pct(from_high),
        "from_low_pct": from_low,
        "from_low_pct_fmt": _fmt_pct(from_low),
        "high_fmt": _fmt_price(high),
        "low_fmt": _fmt_price(low),
    }


def run(research_data: dict) -> dict:
    """
    Main entry point for the return analysis agent.
    """
    ticker = research_data.get("ticker", "UNKNOWN")
    company_name = research_data.get("company_name", ticker)
    stats = research_data.get("stats", {})
    market = research_data.get("market", {})

    print(f"[return_agent] Analyzing return profile for {ticker}...")

    sector = infer_sector(company_name, ticker)
    valuation = assess_valuation(stats, market, sector)
    positioning = assess_52w_positioning(market)

    price = _safe_float(market.get("current_price"))
    mkt_cap = _safe_float(market.get("market_cap"))
    beta = _safe_float(stats.get("beta"))
    div_yield = _safe_float(stats.get("dividend_yield"))

    result = {
        "agent": "return_analysis",
        "ticker": ticker,

        # Price info
        "current_price": price,
        "current_price_fmt": _fmt_price(price),
        "market_cap": mkt_cap,
        "market_cap_fmt": _fmt_price(mkt_cap) if mkt_cap else "N/A",

        # Multiples
        "pe_ratio": stats.get("pe_ratio"),
        "pe_ratio_fmt": _fmt_multiple(stats.get("pe_ratio")),
        "forward_pe": stats.get("forward_pe"),
        "forward_pe_fmt": _fmt_multiple(stats.get("forward_pe")),
        "peg_ratio": stats.get("peg_ratio"),
        "peg_ratio_fmt": _fmt_multiple(stats.get("peg_ratio")),
        "ev_ebitda": stats.get("ev_to_ebitda"),
        "ev_ebitda_fmt": _fmt_multiple(stats.get("ev_to_ebitda")),
        "ev_revenue": stats.get("ev_to_revenue"),
        "ev_revenue_fmt": _fmt_multiple(stats.get("ev_to_revenue")),
        "price_to_book": stats.get("price_to_book"),
        "price_to_book_fmt": _fmt_multiple(stats.get("price_to_book")),

        # Valuation assessment
        "valuation": valuation,

        # 52-week positioning
        "positioning_52w": positioning,

        # Income / risk metrics
        "dividend_yield": div_yield,
        "dividend_yield_fmt": _fmt_pct(div_yield),
        "beta": beta,
        "beta_fmt": f"{beta:.2f}" if beta else "N/A",
        "short_ratio": stats.get("short_ratio"),
        "short_ratio_fmt": f"{stats.get('short_ratio', 0):.1f} days" if stats.get("short_ratio") else "N/A",

        # Sector context
        "inferred_sector": sector,
        "sector_label": SECTOR_BENCHMARKS.get(sector, {}).get("label", "General Market"),
    }

    print(f"[return_agent] Done. Valuation: {valuation['verdict']}")
    return result


if __name__ == "__main__":
    import sys
    from skills import web_research
    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    research = web_research.research_ticker(ticker)
    output = run(research)
    print(json.dumps(output, indent=2, default=str))
