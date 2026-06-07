"""
Macro Context Agent
Assesses the macro and industry environment for a stock.
Uses inferred sector data and available market signals.
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


# Macro context library by sector
# In a full build, this would pull live economic data from FRED API
# For v1, we use curated sector-level context with current macro environment
SECTOR_MACRO_CONTEXT = {
    "technology": {
        "tailwinds": [
            "AI infrastructure spending remains strong, benefiting cloud and semiconductor companies",
            "Enterprise software demand driven by digital transformation and automation initiatives",
            "Strong labor productivity pressures creating demand for automation tools",
        ],
        "headwinds": [
            "Elevated valuations leave limited margin of safety if earnings disappoint",
            "Rising interest rates increase discount rates, pressuring high-multiple stocks",
            "Regulatory scrutiny of large-cap tech increasing across US and EU",
        ],
        "key_watch": "AI monetization timelines, enterprise IT budget cycles, interest rate trajectory",
    },
    "healthcare": {
        "tailwinds": [
            "Aging demographics driving structural demand for healthcare services and products",
            "GLP-1 drug class creating significant value in obesity and cardiometabolic diseases",
            "Biosimilar launches improving access and creating competition dynamics",
        ],
        "headwinds": [
            "IRA drug pricing negotiations creating revenue pressure on pharma companies",
            "CMS reimbursement changes affecting hospital and payer economics",
            "Regulatory timelines for FDA approvals remain unpredictable",
        ],
        "key_watch": "Drug pricing legislation, FDA pipeline decisions, Medicare reimbursement rates",
    },
    "financials": {
        "tailwinds": [
            "Higher-for-longer interest rate environment supporting net interest income",
            "Strong capital markets activity benefiting investment banking and trading",
            "Consumer credit quality remaining resilient despite economic uncertainty",
        ],
        "headwinds": [
            "Commercial real estate exposure a lingering concern for regional banks",
            "Deposit competition and funding costs compressing net interest margins",
            "Regulatory capital requirements increasing under Basel III endgame proposals",
        ],
        "key_watch": "Fed rate decisions, deposit flows, credit loss provisions, CRE exposure",
    },
    "consumer_staples": {
        "tailwinds": [
            "Volume recovery as price elasticity normalizes post-inflation cycle",
            "Private label competition driving premiumization in defensible brand categories",
            "Emerging market growth providing incremental volume opportunity",
        ],
        "headwinds": [
            "Consumer trading down to private label in price-sensitive categories",
            "Input cost normalization limiting pricing power relative to pandemic era",
            "GLP-1 drugs creating uncertainty around long-term food consumption trends",
        ],
        "key_watch": "Volume trends vs. price/mix, private label share, GLP-1 demand impact",
    },
    "consumer_disc": {
        "tailwinds": [
            "Resilient high-income consumer spending supporting premium brands",
            "Travel and experiences continuing to outperform goods spending",
            "Housing market activity creating demand for home improvement and furnishings",
        ],
        "headwinds": [
            "Lower-income consumer stress weighing on value-oriented categories",
            "Tariff risk on imported goods compressing margins for manufacturers",
            "Student loan repayment resumption reducing discretionary spending capacity",
        ],
        "key_watch": "Consumer confidence, savings rate trends, tariff policy developments",
    },
    "industrials": {
        "tailwinds": [
            "Infrastructure investment bill driving multi-year spending cycle",
            "Reshoring and nearshoring creating domestic manufacturing demand",
            "Defense spending increases benefiting aerospace and defense companies",
        ],
        "headwinds": [
            "Global PMI contraction signaling softening industrial end-market demand",
            "Supply chain normalization reducing pricing power versus pandemic peak",
            "China economic weakness dampening global industrial activity",
        ],
        "key_watch": "Global PMI readings, defense budget negotiations, reshoring investment flows",
    },
    "energy": {
        "tailwinds": [
            "Energy security focus driving sustained government and private investment",
            "Data center power demand creating new domestic electricity consumption growth",
            "LNG export infrastructure build-out supporting long-cycle natural gas demand",
        ],
        "headwinds": [
            "OPEC+ production decisions creating oil price volatility",
            "Energy transition accelerating long-term demand risk for fossil fuels",
            "Permitting and regulatory complexity slowing new project timelines",
        ],
        "key_watch": "OPEC+ quotas, US rig count, power demand growth, renewable cost curves",
    },
    "default": {
        "tailwinds": [
            "Resilient US labor market supporting consumer spending capacity",
            "Productivity gains from technology adoption improving corporate margins",
            "Potential Fed rate cuts in 2025 could provide equity valuation tailwind",
        ],
        "headwinds": [
            "Geopolitical uncertainty introducing supply chain and demand volatility",
            "Higher-for-longer rates increasing cost of capital across the economy",
            "Election year policy uncertainty affecting corporate planning cycles",
        ],
        "key_watch": "Fed policy trajectory, employment data, geopolitical developments, earnings revisions",
    },
}


def assess_macro_sensitivity(stats: dict, sector: str) -> dict:
    """
    Assess how sensitive this company is to macro factors
    based on its financial profile.
    """
    beta = _safe_float(stats.get("beta"))
    debt = _safe_float(stats.get("total_debt"))
    fcf = _safe_float(stats.get("free_cashflow"))
    rev_growth = _safe_float(stats.get("revenue_growth"))

    sensitivities = []
    
    # Interest rate sensitivity
    if debt and debt > 5e9:
        sensitivities.append("High interest rate sensitivity — large debt load")
    elif beta and beta > 1.3:
        sensitivities.append("Moderate-high interest rate sensitivity given growth profile")
    else:
        sensitivities.append("Moderate interest rate sensitivity")

    # Economic cycle sensitivity
    if beta and beta > 1.5:
        sensitivities.append("Cyclical — performance likely to be amplified by economic cycles")
    elif beta and beta < 0.7:
        sensitivities.append("Defensive — tends to be insulated from economic downturns")
    else:
        sensitivities.append("Semi-cyclical — some exposure to economic cycles")

    # Growth vs value dynamic
    if rev_growth and rev_growth > 0.15:
        sensitivities.append("Growth-oriented — sensitive to earnings expectations and rate moves")
    elif rev_growth and rev_growth < 0.03:
        sensitivities.append("Mature/value profile — less sensitive to growth narrative shifts")

    return {"sensitivities": sensitivities[:3]}


def run(research_data: dict, sector: str = None) -> dict:
    """
    Main entry point for the macro context agent.
    """
    ticker = research_data.get("ticker", "UNKNOWN")
    company_name = research_data.get("company_name", ticker)
    stats = research_data.get("stats", {})

    print(f"[macro_agent] Assessing macro context for {ticker}...")

    # Use provided sector or infer
    if not sector:
        # Try to infer from name/ticker
        name_lower = (company_name + " " + ticker).lower()
        inferred = "default"
        if any(s in name_lower for s in ["tech", "software", "micro", "aapl", "msft", "googl", "nvda", "amzn"]):
            inferred = "technology"
        elif any(s in name_lower for s in ["pharma", "bio", "health", "jnj", "pfe"]):
            inferred = "healthcare"
        elif any(s in name_lower for s in ["bank", "financial", "capital", "jpm", "bac"]):
            inferred = "financials"
        elif any(s in name_lower for s in ["oil", "gas", "energy", "xom", "cvx"]):
            inferred = "energy"
        elif any(s in name_lower for s in ["consumer", "retail", "food", "walmart", "wmt"]):
            inferred = "consumer_staples"
        sector = inferred

    context = SECTOR_MACRO_CONTEXT.get(sector, SECTOR_MACRO_CONTEXT["default"])
    sensitivity = assess_macro_sensitivity(stats, sector)

    result = {
        "agent": "macro_context",
        "ticker": ticker,
        "sector": sector,

        "tailwinds": context["tailwinds"],
        "headwinds": context["headwinds"],
        "key_watch": context["key_watch"],

        "macro_sensitivities": sensitivity["sensitivities"],
        
        # Overall macro posture
        "macro_posture": "Cautiously constructive — resilient labor market and corporate earnings offset by elevated rates and geopolitical uncertainty",
        "rate_environment": "Higher-for-longer",
        "cycle_stage": "Late cycle",
    }

    print(f"[macro_agent] Done. Sector: {sector}")
    return result


if __name__ == "__main__":
    import sys
    from skills import web_research
    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    research = web_research.research_ticker(ticker)
    output = run(research)
    print(json.dumps(output, indent=2, default=str))
