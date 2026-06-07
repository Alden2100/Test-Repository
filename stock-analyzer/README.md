# Stock Research System

AI-powered single-stock research brief generator.
Pulls live data from SEC EDGAR, analyzes it with structured agents,
generates AI commentary via Qwen (local, private), and produces a
professional 2-page PDF dashboard.

---

## Setup (one time)

### 1. Install Python dependencies

```bash
pip install reportlab requests
```

### 2. Make sure Ollama is running

Open a terminal and run:
```bash
ollama serve
```

Then pull the Qwen model (first time only):
```bash
ollama pull qwen2.5:7b
```

---

## Running the system

Open a terminal, navigate to this folder, and run:

```bash
python orchestrator.py AAPL
```

Replace `AAPL` with any US-listed stock ticker.

The PDF will be saved in the `output/` folder inside this directory.

### Options

```bash
# Use a different Qwen model
python orchestrator.py MSFT --model qwen2.5:14b

# Skip AI commentary (faster, no Ollama needed)
python orchestrator.py NVDA --no-ai

# Save PDF to a specific location
python orchestrator.py TSLA --output ~/Desktop/TSLA_brief.pdf
```

---

## What each file does

```
orchestrator.py          ← Run this. Coordinates everything.

skills/
  web_research.py        ← Fetches SEC EDGAR data and market prices
  pdf_builder.py         ← Builds the PDF dashboard
  llm.py                 ← Talks to Ollama/Qwen locally

agents/
  financial_agent.py     ← Analyzes revenue, margins, health
  return_agent.py        ← Evaluates valuation and upside
  risk_agent.py          ← Scores leverage, volatility, risk
  macro_agent.py         ← Sector tailwinds and headwinds
  ai_analyst.py          ← Qwen generates narrative commentary
```

---

## What the PDF contains

**Page 1 — Cover**
- Three-verdict scorecard: Valuation / Risk / Financial Health
- Key metrics grid (price, P/E, margins, FCF, beta, etc.)
- AI-generated executive summary (3 sentences)
- Quick take bullets with tagged insights

**Page 2 — Full Analysis**
- Detailed financial metrics table
- Valuation multiples vs sector benchmarks with analyst commentary
- 52-week price positioning
- Risk breakdown across 4 dimensions with risk narrative
- Bull/bear investment considerations (AI-generated)
- Macro tailwinds, headwinds, and key watch items

---

## Data sources

- **Financial data**: SEC EDGAR XBRL API (free, no API key needed)
- **Market prices**: Yahoo Finance chart endpoint
- **AI commentary**: Qwen via Ollama (runs locally on your machine)

---

## Troubleshooting

**"Cannot reach Ollama"**
→ Open a new terminal window and run `ollama serve`, then try again.

**"Model not found"**
→ Run `ollama pull qwen2.5:7b` to download the model first.

**"N/A" for many metrics**
→ Yahoo Finance occasionally restricts access. SEC EDGAR data will
  still populate the key financial figures.

**PDF not opening**
→ Check the `output/` folder inside this project directory.
