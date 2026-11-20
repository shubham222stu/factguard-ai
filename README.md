# FactGuard AI — Automated PDF Fact-Checking Agent

> **Live Demo:** [https://factguard-ai.streamlit.app](https://factguard-ai.streamlit.app) *(deploy link goes here)*

---

## What is FactGuard AI?

**FactGuard AI** is an automated fact-checking web application that acts as a "Truth Layer" for any PDF document. It uses AI to:

1. **Extract** specific verifiable claims (statistics, dates, financial figures, technical facts) from uploaded PDFs
2. **Verify** each claim against live web data using Tavily's AI-powered search engine
3. **Report** findings with color-coded verdicts:
   - ✅ **Verified** — Claim matches live web evidence
   - ⚠️ **Inaccurate** — Claim contains outdated or partially wrong data
   - ❌ **False** — Claim is contradicted by evidence or no evidence found

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend/UI** | Streamlit (Python) |
| **PDF Parsing** | pypdf |
| **Claim Extraction** | Google Gemini 1.5 Flash |
| **Web Search** | Tavily Search API |
| **Verdict Generation** | Google Gemini 1.5 Flash |
| **Deployment** | Streamlit Community Cloud |

---

## Features

- **Premium dark-mode UI** with glassmorphism-style cards
- **Smart claim extraction** — identifies stats, dates, financial figures, technical claims
- **Live web verification** via Tavily's advanced search
- **Confidence scoring** (HIGH / MEDIUM / LOW) per verdict
- **Corrections provided** for inaccurate/false claims with real data
- **Source citations** — links to web pages used for verification
- **Downloadable reports** in JSON and plain text formats
- **Filterable results** by verdict type (All / Verified / Inaccurate / False)
- **Accuracy score** — overall document truth percentage

---

## Local Setup

### Prerequisites
- Python 3.9+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))
- Tavily API key (free at [tavily.com](https://tavily.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/factguard-ai.git
cd factguard-ai/fact_checker_app

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## Deployment on Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"**
4. Select your repository and set:
   - **Main file path:** `fact_checker_app/app.py`
5. Click **"Deploy!"**

The app will be live at `https://your-app-name.streamlit.app`

> **Note:** API keys are entered by users in the sidebar at runtime — no secrets.toml required.

---

## How It Works (Pipeline)

```
PDF Upload
    │
    ▼
Text Extraction (pypdf)
    │
    ▼
Claim Identification (Gemini 1.5 Flash)
    │  "Extract up to N verifiable claims with search queries"
    ▼
For each claim:
  ┌─────────────────────────────┐
  │  Web Search (Tavily API)    │
  │  5 results, advanced depth  │
  └─────────────┬───────────────┘
                │
                ▼
  ┌─────────────────────────────┐
  │  Verdict Generation         │
  │  (Gemini 1.5 Flash)         │
  │  VERIFIED / INACCURATE /    │
  │  FALSE + explanation        │
  └─────────────────────────────┘
    │
    ▼
Results Dashboard + Download Report
```

---

## Project Structure

```
fact_checker_app/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

---

## Evaluation: Trap Document Test

This app is designed to catch intentional falsehoods:

| Scenario | Expected Behavior |
|----------|------------------|
| Fake statistic ("70% of X do Y" when real figure is 23%) | INACCURATE — provides correct figure |
| Completely fabricated claim | FALSE — no web evidence found |
| Outdated data (old market size, superseded figures) | INACCURATE — provides current data |
| Accurate claim | VERIFIED — with supporting source |

---

## API Keys

| Key | Where to Get | Cost |
|-----|-------------|------|
| Google Gemini | [aistudio.google.com](https://aistudio.google.com) | Free tier available |
| Tavily Search | [tavily.com](https://tavily.com) | Free tier (1000 searches/mo) |

---

## License

MIT License — feel free to use and modify.

---

*Built for the GEO Product Assignment — Part 2: The Fact-Check Agent*
