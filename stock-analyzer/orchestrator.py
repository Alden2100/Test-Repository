"""
Stock Research Orchestrator
Master entry point. Takes a ticker, runs all agents in sequence,
and produces a professional PDF research brief.

Usage:
    python orchestrator.py AAPL
    python orchestrator.py MSFT --output /path/to/output.pdf
    python orchestrator.py NVDA --model qwen2.5:7b
    python orchestrator.py NVDA --no-ai   (skip Ollama, structured data only)
"""

import sys
import os
import json
import argparse
import traceback
from datetime import datetime

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from skills import web_research, pdf_builder
from agents import financial_agent, return_agent, risk_agent, macro_agent

DEFAULT_MODEL = "qwen2.5:7b"


def run(ticker: str, output_path: str = None, model: str = DEFAULT_MODEL, use_ai: bool = True) -> str:
    """
    Full orchestration pipeline.
    Returns path to the generated PDF.
    """
    ticker = ticker.upper().strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    if not output_path:
        output_dir = os.path.join(ROOT, "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{ticker}_research_{timestamp}.pdf")

    print(f"\n{'='*60}")
    print(f"  Stock Research System — {ticker}")
    print(f"  {datetime.now().strftime('%B %d, %Y  %H:%M')}")
    if use_ai:
        print(f"  AI Model: {model} (Ollama)")
    else:
        print(f"  Mode: Structured data only (no AI)")
    print(f"{'='*60}\n")

    # ── STEP 1: WEB RESEARCH ─────────────────────────────────────────────────
    print("Step 1/6  Web Research")
    print("-" * 40)
    try:
        research_data = web_research.research_ticker(ticker)
        research_data["as_of"] = datetime.now().strftime("%B %d, %Y")
        if research_data.get("market", {}).get("error"):
            print(f"  [warn] Market data: {research_data['market']['error']}")
        if research_data.get("stats", {}).get("error"):
            print(f"  [warn] Stats: {research_data['stats']['error']}")
    except Exception as e:
        print(f"  [error] Web research failed: {e}")
        traceback.print_exc()
        research_data = {
            "ticker": ticker, "company_name": ticker, "cik": None,
            "as_of": datetime.now().strftime("%B %d, %Y"),
            "market": {}, "stats": {}, "filing_10k": None,
            "filing_10q": None, "sec_facts": {},
        }

    # ── STEP 2: FINANCIAL ANALYSIS ───────────────────────────────────────────
    print("\nStep 2/6  Financial Analysis")
    print("-" * 40)
    try:
        financial_data = financial_agent.run(research_data)
        financial_data["as_of"] = research_data["as_of"]
    except Exception as e:
        print(f"  [error] Financial agent failed: {e}")
        traceback.print_exc()
        financial_data = {
            "agent": "financial_analysis", "ticker": ticker,
            "company_name": research_data.get("company_name", ticker),
            "as_of": research_data["as_of"],
            "health_score": 5, "health_assessment": "Data Unavailable",
            "health_positives": [], "health_flags": ["Financial data could not be retrieved"],
            "revenue_ttm_fmt": "N/A", "ebitda_fmt": "N/A", "free_cashflow_fmt": "N/A",
            "gross_margin_fmt": "N/A", "operating_margin_fmt": "N/A", "profit_margin_fmt": "N/A",
            "roe_fmt": "N/A", "roa_fmt": "N/A", "revenue_growth_yoy_fmt": "N/A",
            "earnings_growth_yoy_fmt": "N/A", "total_debt_fmt": "N/A", "net_cash_fmt": "N/A",
        }

    # ── STEP 3: RETURN ANALYSIS ──────────────────────────────────────────────
    print("\nStep 3/6  Return Analysis")
    print("-" * 40)
    try:
        return_data = return_agent.run(research_data)
    except Exception as e:
        print(f"  [error] Return agent failed: {e}")
        traceback.print_exc()
        return_data = {
            "agent": "return_analysis", "ticker": ticker,
            "current_price_fmt": "N/A", "market_cap": None,
            "pe_ratio_fmt": "N/A", "forward_pe_fmt": "N/A",
            "peg_ratio_fmt": "N/A", "ev_ebitda_fmt": "N/A",
            "ev_revenue_fmt": "N/A", "price_to_book_fmt": "N/A",
            "dividend_yield_fmt": "N/A", "beta_fmt": "N/A",
            "valuation": {"verdict": "Unavailable", "signals": [], "benchmarks_used": {}},
            "positioning_52w": {"position_pct": 0.5, "label": "N/A",
                                "low_fmt": "N/A", "high_fmt": "N/A",
                                "position_pct_fmt": "N/A"},
            "inferred_sector": "default", "sector_label": "General Market",
        }

    # ── STEP 4: RISK ANALYSIS ────────────────────────────────────────────────
    print("\nStep 4/6  Risk Analysis")
    print("-" * 40)
    try:
        risk_data = risk_agent.run(research_data)
    except Exception as e:
        print(f"  [error] Risk agent failed: {e}")
        traceback.print_exc()
        risk_data = {
            "agent": "risk_analysis", "ticker": ticker,
            "overall_risk": "Unknown", "risk_score": 5,
            "top_risks": ["Risk data could not be retrieved"],
            "beta_fmt": "N/A", "debt_ebitda_fmt": "N/A", "net_cash_fmt": "N/A",
            "leverage": {"risk_level": "Unknown", "details": ["Data unavailable"]},
            "volatility": {"risk_level": "Unknown", "details": ["Data unavailable"]},
            "profitability_risk": {"risk_level": "Unknown", "details": ["Data unavailable"]},
            "short_interest": {"risk_level": "Unknown", "details": ["Data unavailable"]},
        }

    # ── STEP 5: MACRO CONTEXT ────────────────────────────────────────────────
    print("\nStep 5/6  Macro Context")
    print("-" * 40)
    try:
        sector = return_data.get("inferred_sector", "default")
        macro_data = macro_agent.run(research_data, sector=sector)
    except Exception as e:
        print(f"  [error] Macro agent failed: {e}")
        traceback.print_exc()
        macro_data = {
            "agent": "macro_context", "ticker": ticker,
            "sector": "default", "sector_label": "General Market",
            "rate_environment": "N/A", "cycle_stage": "N/A",
            "tailwinds": ["Macro data unavailable"],
            "headwinds": ["Macro data unavailable"],
            "key_watch": "N/A", "macro_posture": "N/A",
        }

    # ── STEP 6: AI COMMENTARY (Qwen via Ollama) ──────────────────────────────
    ai_data = None
    if use_ai:
        print(f"\nStep 6/6  AI Commentary ({model})")
        print("-" * 40)
        try:
            from skills import llm
            from agents import ai_analyst

            # Verify model is available
            available, resolved_model = llm.check_model(model)
            if not available:
                print(f"  [warn] {resolved_model}")
                print(f"  [warn] Skipping AI commentary. Run: ollama pull {model}")
            else:
                if resolved_model != model:
                    print(f"  [info] Using model: {resolved_model}")
                ai_data = ai_analyst.run(
                    financial=financial_data,
                    return_data=return_data,
                    risk=risk_data,
                    macro=macro_data,
                    model=resolved_model
                )
        except ConnectionError as e:
            print(f"  [warn] Ollama not reachable — skipping AI commentary")
            print(f"  [warn] Start Ollama with: ollama serve")
        except Exception as e:
            print(f"  [warn] AI commentary failed: {e}")
            traceback.print_exc()
    else:
        print("\nStep 6/6  AI Commentary — skipped (--no-ai)")

    # ── BUILD PDF ────────────────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("Building PDF dashboard...")
    print(f"{'─'*40}")

    try:
        pdf_builder.build_pdf(
            financial=financial_data,
            return_data=return_data,
            risk=risk_data,
            macro=macro_data,
            output_path=output_path,
            ai=ai_data,
        )
    except Exception as e:
        print(f"  [error] PDF build failed: {e}")
        traceback.print_exc()
        raise

    # ── SUMMARY ─────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  COMPLETE  ✓  {ticker}  —  {research_data.get('company_name', ticker)}")
    print(f"{'─'*60}")
    print(f"  Valuation:        {return_data.get('valuation', {}).get('verdict', 'N/A')}")
    print(f"  Risk Profile:     {risk_data.get('overall_risk', 'N/A')}")
    print(f"  Financial Health: {financial_data.get('health_assessment', 'N/A')}")
    print(f"  Current Price:    {return_data.get('current_price_fmt', 'N/A')}")
    print(f"  AI Commentary:    {'✓ Included' if ai_data else '✗ Not included'}")
    print(f"{'─'*60}")
    print(f"  PDF → {output_path}")
    print(f"{'='*60}\n")

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Research System")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL, MSFT, NVDA)")
    parser.add_argument("--output", "-o", help="Output PDF path", default=None)
    parser.add_argument("--model", "-m", help=f"Ollama model name (default: {DEFAULT_MODEL})",
                        default=DEFAULT_MODEL)
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip AI commentary (faster, no Ollama required)")
    args = parser.parse_args()

    run(args.ticker, args.output, model=args.model, use_ai=not args.no_ai)
