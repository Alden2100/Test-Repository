"""
Risk Analysis Agent
Identifies and scores key risk factors across multiple dimensions:
leverage, liquidity, volatility, concentration, and market risk.
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


def _fmt_million(val) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        elif abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        else:
            return f"${v:,.0f}"
    except Exception:
        return "N/A"


def assess_leverage_risk(stats: dict) -> dict:
    """Assess debt burden and solvency risk."""
    total_debt = _safe_float(stats.get("total_debt"))
    total_cash = _safe_float(stats.get("total_cash"))
    ebitda = _safe_float(stats.get("ebitda"))
    fcf = _safe_float(stats.get("free_cashflow"))

    risk_level = "Low"
    details = []

    debt_ebitda = None
    if total_debt and ebitda and ebitda > 0:
        debt_ebitda = total_debt / ebitda
        if debt_ebitda > 5:
            risk_level = "High"
            details.append(f"Debt/EBITDA of {debt_ebitda:.1f}x is elevated — limited financial flexibility")
        elif debt_ebitda > 3:
            risk_level = "Moderate"
            details.append(f"Debt/EBITDA of {debt_ebitda:.1f}x warrants monitoring")
        else:
            details.append(f"Debt/EBITDA of {debt_ebitda:.1f}x is manageable")
    elif total_debt and (total_debt > 1e10):
        risk_level = "Moderate"
        details.append(f"Significant absolute debt load ({_fmt_million(total_debt)})")

    net_cash = None
    if total_debt is not None and total_cash is not None:
        net_cash = total_cash - total_debt
        if net_cash > 0:
            details.append(f"Net cash position of {_fmt_million(net_cash)} — low insolvency risk")
        else:
            details.append(f"Net debt position of {_fmt_million(abs(net_cash))}")

    if fcf and fcf < 0:
        risk_level = "High" if risk_level != "High" else risk_level
        details.append("Negative free cash flow — reliant on external financing")

    return {
        "risk_level": risk_level,
        "debt_ebitda": debt_ebitda,
        "debt_ebitda_fmt": f"{debt_ebitda:.1f}x" if debt_ebitda else "N/A",
        "net_cash": net_cash,
        "net_cash_fmt": _fmt_million(net_cash),
        "details": details,
    }


def assess_volatility_risk(stats: dict, market: dict) -> dict:
    """Assess market price volatility and beta."""
    beta = _safe_float(stats.get("beta"))
    price = _safe_float(market.get("current_price"))
    high = _safe_float(market.get("fifty_two_week_high"))
    low = _safe_float(market.get("fifty_two_week_low"))

    risk_level = "Moderate"
    details = []

    if beta:
        if beta > 1.5:
            risk_level = "High"
            details.append(f"Beta of {beta:.2f} — significantly more volatile than the market")
        elif beta > 1.2:
            risk_level = "Moderate"
            details.append(f"Beta of {beta:.2f} — moderately above market volatility")
        elif beta < 0.7:
            risk_level = "Low"
            details.append(f"Beta of {beta:.2f} — defensive, low-volatility stock")
        else:
            details.append(f"Beta of {beta:.2f} — broadly in line with market")

    # 52-week drawdown
    if high and low and high > 0:
        max_drawdown = (low / high) - 1
        if abs(max_drawdown) > 0.40:
            details.append(f"52-week drawdown of {abs(max_drawdown)*100:.0f}% — significant price risk realized this year")
        elif abs(max_drawdown) > 0.20:
            details.append(f"52-week range implies {abs(max_drawdown)*100:.0f}% maximum drawdown")
        else:
            details.append(f"Relatively stable 52-week price range (max drawdown ~{abs(max_drawdown)*100:.0f}%)")

    return {
        "risk_level": risk_level,
        "beta": beta,
        "beta_fmt": f"{beta:.2f}" if beta else "N/A",
        "details": details,
    }


def assess_short_interest_risk(stats: dict) -> dict:
    """Assess short interest as a contrarian / risk signal."""
    short_ratio = _safe_float(stats.get("short_ratio"))
    details = []
    risk_level = "Low"

    if short_ratio:
        if short_ratio > 10:
            risk_level = "High"
            details.append(f"Short ratio of {short_ratio:.1f} days — heavy short interest, possible short squeeze or fundamental concern")
        elif short_ratio > 5:
            risk_level = "Moderate"
            details.append(f"Short ratio of {short_ratio:.1f} days — elevated bearish positioning")
        else:
            details.append(f"Short ratio of {short_ratio:.1f} days — low short interest")
    else:
        details.append("Short interest data not available")

    return {
        "risk_level": risk_level,
        "short_ratio": short_ratio,
        "details": details,
    }


def assess_profitability_risk(stats: dict) -> dict:
    """Assess margin and earnings sustainability."""
    op_margin = _safe_float(stats.get("operating_margin"))
    profit_margin = _safe_float(stats.get("profit_margin"))
    rev_growth = _safe_float(stats.get("revenue_growth"))
    earn_growth = _safe_float(stats.get("earnings_growth"))

    risk_level = "Low"
    details = []

    if op_margin is not None:
        if op_margin < 0:
            risk_level = "High"
            details.append(f"Negative operating margin ({_fmt_pct(op_margin)}) — burning cash at the operating level")
        elif op_margin < 0.05:
            risk_level = "Moderate"
            details.append(f"Thin operating margin ({_fmt_pct(op_margin)}) — limited buffer against revenue shortfalls")
        else:
            details.append(f"Operating margin of {_fmt_pct(op_margin)} provides reasonable buffer")

    if earn_growth is not None and earn_growth < -0.20:
        risk_level = "High" if risk_level != "High" else risk_level
        details.append(f"Earnings declining sharply ({_fmt_pct(earn_growth)} YoY)")
    elif rev_growth is not None and rev_growth < 0:
        risk_level = "Moderate" if risk_level == "Low" else risk_level
        details.append(f"Revenue declining ({_fmt_pct(rev_growth)} YoY) — demand headwind")

    return {
        "risk_level": risk_level,
        "details": details,
    }


def compute_overall_risk(leverage, volatility, short_interest, profitability) -> dict:
    """Aggregate individual risk scores into an overall risk profile."""
    level_scores = {"Low": 1, "Moderate": 2, "High": 3}
    scores = [
        level_scores.get(leverage["risk_level"], 2),
        level_scores.get(volatility["risk_level"], 2),
        level_scores.get(short_interest["risk_level"], 2),
        level_scores.get(profitability["risk_level"], 2),
    ]
    avg = sum(scores) / len(scores)

    if avg >= 2.5:
        overall = "High"
    elif avg >= 1.7:
        overall = "Moderate"
    else:
        overall = "Low"

    # Numerical score 1-10 (inverse of risk)
    risk_score = round(10 - (avg - 1) * 4, 1)
    risk_score = max(1, min(10, risk_score))

    return {
        "overall_risk": overall,
        "risk_score": risk_score,
        "avg_component_score": round(avg, 2),
    }


def run(research_data: dict) -> dict:
    """
    Main entry point for the risk analysis agent.
    """
    ticker = research_data.get("ticker", "UNKNOWN")
    stats = research_data.get("stats", {})
    market = research_data.get("market", {})

    print(f"[risk_agent] Analyzing risk profile for {ticker}...")

    leverage = assess_leverage_risk(stats)
    volatility = assess_volatility_risk(stats, market)
    short_interest = assess_short_interest_risk(stats)
    profitability = assess_profitability_risk(stats)
    overall = compute_overall_risk(leverage, volatility, short_interest, profitability)

    # Consolidate top risk flags across all dimensions
    all_flags = (
        leverage["details"][:1] +
        volatility["details"][:1] +
        profitability["details"][:1] +
        short_interest["details"][:1]
    )
    top_risks = [f for f in all_flags if any(
        word in f.lower() for word in ["elevated", "negative", "declining", "heavy", "significant", "thin", "limited", "burning"]
    )][:3]

    if not top_risks:
        top_risks = ["No major risk flags identified across monitored dimensions"]

    result = {
        "agent": "risk_analysis",
        "ticker": ticker,

        # Overall
        "overall_risk": overall["overall_risk"],
        "risk_score": overall["risk_score"],
        "top_risks": top_risks,

        # Components
        "leverage": leverage,
        "volatility": volatility,
        "short_interest": short_interest,
        "profitability_risk": profitability,

        # Key metrics for display
        "beta": _safe_float(stats.get("beta")),
        "beta_fmt": f"{_safe_float(stats.get('beta')):.2f}" if _safe_float(stats.get("beta")) else "N/A",
        "debt_ebitda_fmt": leverage["debt_ebitda_fmt"],
        "net_cash_fmt": leverage["net_cash_fmt"],
    }

    print(f"[risk_agent] Done. Overall risk: {overall['overall_risk']} (score: {overall['risk_score']}/10)")
    return result


if __name__ == "__main__":
    import sys
    from skills import web_research
    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    research = web_research.research_ticker(ticker)
    output = run(research)
    print(json.dumps(output, indent=2, default=str))
