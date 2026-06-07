"""
Web Research Skill
Fetches SEC filings and recent news for a given ticker.
Returns structured data for downstream agents.
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import datetime


def _fetch(url: str, headers: dict = None) -> str:
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "StockAnalyzer/1.0 research@firm.com",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def get_company_info(ticker: str) -> dict:
    """Resolve ticker to CIK and company name via SEC EDGAR."""
    ticker = ticker.upper()
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt=2020-01-01&forms=10-K".format(ticker)
    
    # Use the company tickers JSON from SEC
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    raw = _fetch(tickers_url)
    data = json.loads(raw)
    
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker:
            return {
                "ticker": ticker,
                "name": entry.get("title", ticker),
                "cik": str(entry.get("cik_str", "")).zfill(10)
            }
    return {"ticker": ticker, "name": ticker, "cik": None}


def get_latest_10k_url(cik: str) -> dict | None:
    """Get the most recent 10-K filing URL from SEC EDGAR."""
    if not cik:
        return None
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    raw = _fetch(url)
    data = json.loads(raw)
    
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    
    for i, form in enumerate(forms):
        if form == "10-K":
            acc = accession[i].replace("-", "")
            doc = primary_docs[i]
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
            return {
                "filing_date": dates[i],
                "url": filing_url,
                "accession": accession[i]
            }
    return None


def get_latest_10q_url(cik: str) -> dict | None:
    """Get the most recent 10-Q filing URL from SEC EDGAR."""
    if not cik:
        return None
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    raw = _fetch(url)
    data = json.loads(raw)
    
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    
    for i, form in enumerate(forms):
        if form == "10-Q":
            acc = accession[i].replace("-", "")
            doc = primary_docs[i]
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
            return {
                "filing_date": dates[i],
                "url": filing_url,
                "accession": accession[i]
            }
    return None


def get_company_facts(cik: str) -> dict:
    """
    Pull structured financial facts from SEC EDGAR XBRL API.
    Returns key financial metrics as time series.
    """
    if not cik:
        return {}
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        raw = _fetch(url)
        facts = json.loads(raw)
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        
        result = {}
        
        # Key metrics to extract
        metrics = {
            "Revenues": "revenue",
            "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue_alt",
            "NetIncomeLoss": "net_income",
            "EarningsPerShareDiluted": "eps_diluted",
            "OperatingIncomeLoss": "operating_income",
            "CashAndCashEquivalentsAtCarryingValue": "cash",
            "LongTermDebt": "long_term_debt",
            "CommonStockSharesOutstanding": "shares_outstanding",
            "ResearchAndDevelopmentExpense": "rd_expense",
        }
        
        for gaap_key, friendly_key in metrics.items():
            if gaap_key in us_gaap:
                units = us_gaap[gaap_key].get("units", {})
                # Try USD first, then pure numbers
                values = units.get("USD", units.get("USD/shares", units.get("shares", [])))
                # Filter to annual 10-K filings only
                annual = [
                    v for v in values
                    if v.get("form") == "10-K" and v.get("fp") == "FY"
                ]
                if annual:
                    # Sort by end date, take last 3 years
                    annual.sort(key=lambda x: x.get("end", ""))
                    result[friendly_key] = annual[-3:]
        
        return result
    except Exception as e:
        return {"error": str(e)}


def get_market_data(ticker: str) -> dict:
    """
    Fetch basic market data from Yahoo Finance chart endpoint.
    Returns price, market cap, P/E, 52-week range.
    """
    # Try multiple Yahoo endpoints
    endpoints = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d",
    ]
    headers_variants = [
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "application/json"},
        {"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    ]
    for url in endpoints:
        for hdrs in headers_variants:
            try:
                raw = _fetch(url, headers=hdrs)
                data = json.loads(raw)
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                if meta.get("regularMarketPrice"):
                    return {
                        "current_price": meta.get("regularMarketPrice"),
                        "previous_close": meta.get("previousClose"),
                        "market_cap": meta.get("marketCap"),
                        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
                        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
                        "currency": meta.get("currency", "USD"),
                        "exchange": meta.get("exchangeName"),
                    }
            except Exception:
                continue
    return {"error": "Market data unavailable (Yahoo Finance auth restricted)"}


def get_key_stats(ticker: str) -> dict:
    """
    Fetch key statistics from Yahoo Finance.
    Falls back to SEC XBRL-derived metrics when Yahoo is unavailable.
    """
    # Try Yahoo first
    for base in ["query1", "query2"]:
        try:
            url = f"https://{base}.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics,financialData,summaryDetail"
            raw = _fetch(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://finance.yahoo.com",
            })
            data = json.loads(raw)
            result_data = data.get("quoteSummary", {}).get("result", [{}])[0]
            stats = result_data.get("defaultKeyStatistics", {})
            fin_data = result_data.get("financialData", {})
            summary = result_data.get("summaryDetail", {})
            def val(d, key):
                v = d.get(key, {})
                return v.get("raw") if isinstance(v, dict) else v
            return {
                "pe_ratio": val(summary, "trailingPE"),
                "forward_pe": val(summary, "forwardPE"),
                "peg_ratio": val(stats, "pegRatio"),
                "price_to_book": val(stats, "priceToBook"),
                "ev_to_ebitda": val(stats, "enterpriseToEbitda"),
                "ev_to_revenue": val(stats, "enterpriseToRevenue"),
                "profit_margin": val(fin_data, "profitMargins"),
                "operating_margin": val(fin_data, "operatingMargins"),
                "return_on_equity": val(fin_data, "returnOnEquity"),
                "return_on_assets": val(fin_data, "returnOnAssets"),
                "revenue_growth": val(fin_data, "revenueGrowth"),
                "earnings_growth": val(fin_data, "earningsGrowth"),
                "total_debt": val(fin_data, "totalDebt"),
                "total_cash": val(fin_data, "totalCash"),
                "free_cashflow": val(fin_data, "freeCashflow"),
                "revenue_ttm": val(fin_data, "totalRevenue"),
                "gross_margin": val(fin_data, "grossMargins"),
                "ebitda": val(fin_data, "ebitda"),
                "beta": val(stats, "beta"),
                "shares_outstanding": val(stats, "sharesOutstanding"),
                "short_ratio": val(stats, "shortRatio"),
                "dividend_yield": val(summary, "dividendYield"),
            }
        except Exception:
            continue
    
    # Yahoo blocked — derive key metrics from SEC XBRL facts
    print("[web_research] Yahoo Finance unavailable, deriving stats from SEC XBRL...")
    return {}  # Will be populated from sec_facts in the financial agent


def _derive_stats_from_sec(cik: str, facts: dict, market: dict) -> dict:
    """
    Derive key financial ratios from SEC XBRL data.
    Used as fallback when Yahoo Finance is unavailable.
    """
    if not facts or facts.get("error"):
        return {}
    
    def latest_annual(key):
        vals = facts.get(key, [])
        if not vals:
            return None
        return vals[-1].get("val")
    
    def prev_annual(key):
        vals = facts.get(key, [])
        if len(vals) < 2:
            return None
        return vals[-2].get("val")
    
    rev = latest_annual("revenue") or latest_annual("revenue_alt")
    rev_prev = prev_annual("revenue") or prev_annual("revenue_alt")
    net_income = latest_annual("net_income")
    op_income = latest_annual("operating_income")
    cash = latest_annual("cash")
    lt_debt = latest_annual("long_term_debt")
    shares = latest_annual("shares_outstanding")
    price = market.get("current_price")
    
    result = {}
    
    if rev:
        result["revenue_ttm"] = rev
        if rev_prev and rev_prev > 0:
            result["revenue_growth"] = (rev - rev_prev) / rev_prev
    
    if net_income and rev and rev > 0:
        result["profit_margin"] = net_income / rev
    
    if op_income and rev and rev > 0:
        result["operating_margin"] = op_income / rev
    
    if net_income and shares and price:
        eps = net_income / shares
        result["pe_ratio"] = price / eps if eps > 0 else None
    
    result["total_cash"] = cash
    result["total_debt"] = lt_debt
    result["ebitda"] = op_income  # Approximation without D&A
    
    if lt_debt and cash:
        result["net_cash"] = cash - lt_debt
    
    # Beta from market data if available
    if market.get("beta"):
        result["beta"] = market.get("beta")
    
    return result


def research_ticker(ticker: str) -> dict:
    """
    Master function. Runs all research for a ticker.
    Returns a single dict consumed by all downstream agents.
    """
    ticker = ticker.upper().strip()
    print(f"[web_research] Starting research for {ticker}...")
    
    # 1. Company identity
    print("[web_research] Resolving company identity...")
    company = get_company_info(ticker)
    
    # 2. Market data
    print("[web_research] Fetching market data...")
    market = get_market_data(ticker)
    
    # 3. Key stats / ratios
    print("[web_research] Fetching key statistics...")
    stats = get_key_stats(ticker)
    
    # 4. SEC filings
    filing_10k = None
    filing_10q = None
    facts = {}
    if company.get("cik"):
        print("[web_research] Fetching SEC filing links...")
        filing_10k = get_latest_10k_url(company["cik"])
        filing_10q = get_latest_10q_url(company["cik"])
        print("[web_research] Fetching XBRL company facts...")
        facts = get_company_facts(company["cik"])
    else:
        print("[web_research] Warning: CIK not found, skipping SEC data")
    
    result = {
        "ticker": ticker,
        "company_name": company.get("name", ticker),
        "cik": company.get("cik"),
        "as_of": datetime.now().strftime("%B %d, %Y"),
        "market": market,
        "stats": stats,
        "filing_10k": filing_10k,
        "filing_10q": filing_10q,
        "sec_facts": facts,
    }
    
    # If Yahoo stats came back empty, derive from SEC XBRL
    if not stats or not stats.get("revenue_ttm"):
        print("[web_research] Enriching with SEC XBRL-derived metrics...")
        sec_derived = _derive_stats_from_sec(company.get("cik"), facts, market)
        result["stats"] = {**sec_derived, **stats}  # Yahoo takes precedence if any keys exist
    
    print(f"[web_research] Done. Company: {result['company_name']}")
    return result


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    result = research_ticker(ticker)
    print(json.dumps(result, indent=2, default=str))
