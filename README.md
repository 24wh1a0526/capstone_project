# 🔍 Competitive Intelligence Briefing Crew

> An agentic AI system that automatically researches competitors, analyzes market
> signals, and generates a professional weekly competitive intelligence report — with
> full source citations, governance against hallucinations, and an interactive
> Streamlit dashboard.

---

## 📋 Project Overview

The **Competitive Intelligence Briefing Crew** is a multi-agent AI application built
with LangGraph and OpenAI. It orchestrates four specialized agents in a pipeline:

```
User Input (Topic)
      │
      ▼
┌─────────────────┐
│  Supervisor     │  Plans search queries, enforces step limits, governs claims
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Researcher     │  Executes Tavily web searches, collects structured sources
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analyst        │  Deduplicates, validates citations, extracts structured insights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Writer         │  Generates professional briefing with mandatory citations
└────────┬────────┘
         │
         ▼
  📄 Professional Report
  📊 Evaluation Dashboard
  📁 Audit Logs
```

---

## 🏗️ Architecture

```
capstone/
│
├── agents/
│   ├── __init__.py
│   ├── supervisor.py     # Plans queries, enforces step limit, governance review
│   ├── researcher.py     # Web search execution, source collection, failure tracking
│   ├── analyst.py        # Dedup, analysis, citation validation, structured output
│   └── writer.py         # Professional report generation with mandatory citations
│
├── tools/
│   ├── __init__.py
│   ├── web_search.py     # Tavily API wrapper — SourceDocument, failure isolation
│   └── rag.py            # FAISS/ChromaDB vector store for context retrieval
│
├── ui/
│   └── app.py            # Streamlit dashboard — input, report, evaluation
│
├── logs/
│   ├── __init__.py
│   ├── logger.py         # Log writers for research/analysis/writer/execution
│   ├── research_log.json     # (generated at runtime)
│   ├── analysis_log.json     # (generated at runtime)
│   ├── writer_log.json       # (generated at runtime)
│   └── execution_trace.json  # (generated at runtime)
│
├── docs/
│   └── Capstone_Project_Catalog.docx
│
├── prompts/              # (for future prompt templates)
│
├── workflow.py           # LangGraph StateGraph pipeline orchestration
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🤖 Agent Workflow

### 1. Supervisor Agent (`agents/supervisor.py`)
- Receives the research topic from the user
- Generates 5–8 targeted, specific search queries using GPT
- Monitors step count against `MAX_STEPS` (default: 40)
- Reviews claims for governance compliance

### 2. Research Agent (`agents/researcher.py`)
- Executes each search query via Tavily API
- Collects up to `MAX_SOURCES` (default: 20) source documents
- Isolates individual URL failures: failed sources are **skipped and logged**, execution continues
- Stores structured `SourceDocument` objects: title, URL, date, content

### 3. Analyst Agent (`agents/analyst.py`)
- Deduplicates sources by URL
- Sends sources to GPT for structured extraction: pricing, product updates, market signals, trends
- **Removes all unsupported/unverified claims** and logs them
- Flags **governance violations** (rumors, bankruptcy claims, speculation)
- Every insight includes a citation (title + URL)

### 4. Writer Agent (`agents/writer.py`)
- Generates a full professional briefing in Markdown
- Every factual statement includes an inline citation
- Empty sections trigger the governance notice:
  `"Unverified information — omitted from final report."`
- Sections: Executive Summary, Competitor Pricing, Product Updates, Market Signals, Recommendations, References, Run Metadata

---

## 🛡️ Governance & Safety

| Rule | Implementation |
|------|----------------|
| Every claim must have a citation | Enforced in Analyst + Writer system prompts |
| No rumors or speculation | Analyst rejects and logs governance violations |
| No hallucinated statistics | Analyst only extracts claims from provided source text |
| Fake bankruptcy/scandal claims | Analyst rejects unless from official verified sources |
| Partial failures continue execution | Researcher catches per-URL exceptions, skips and logs |
| Step limit (max 40) | Enforced at each LangGraph node transition |
| Source limit (max 20) | Enforced in WebSearchTool across all queries |

---

## ⚡ Features

- ✅ Multi-agent LangGraph pipeline (Research → Analysis → Writing)
- ✅ Every claim has a source citation
- ✅ Partial failure handling — failed URLs skipped, execution continues
- ✅ Maximum 20 sources and 40 steps to prevent infinite loops
- ✅ Governance against hallucinations and unverified claims
- ✅ FAISS/ChromaDB RAG for context retrieval
- ✅ Streamlit professional dashboard with evaluation metrics
- ✅ Agent trace visualization
- ✅ Structured JSON audit logs (4 files)
- ✅ Downloadable Markdown report

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- OpenAI API key → https://platform.openai.com/api-keys
- Tavily API key → https://app.tavily.com/

### Steps

```bash
# 1. Clone / navigate to the project
cd capstone

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env   # Windows
# OR
cp .env.example .env     # macOS/Linux

# 5. Edit .env with your API keys
notepad .env   # Windows
# OR
nano .env      # macOS/Linux
```

---

## 🔑 Environment Variables

Edit `.env` with the following:

```env
# Required — OpenRouter API key
# Get from: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here

# OpenRouter model (optional, defaults to openai/gpt-4o-mini)
# Browse all models at: https://openrouter.ai/models
OPENROUTER_MODEL=openai/gpt-4o-mini

# Tavily Search API key (required)
# Get from: https://app.tavily.com/
TAVILY_API_KEY=tvly-your-tavily-key-here

# Optional (defaults shown)
MAX_SOURCES=20
MAX_STEPS=40
LOG_DIR=./logs
VECTOR_STORE=faiss

# Optional — sent as metadata to OpenRouter
OPENROUTER_SITE_URL=http://localhost:8501
OPENROUTER_SITE_NAME=CI Briefing Crew
```

---

## ▶️ How to Run

### Streamlit UI (Recommended)

```bash
# From the capstone/ directory
streamlit run ui/app.py
```

Open http://localhost:8501 in your browser.

1. Enter your API keys in the sidebar (or set them in `.env`)
2. Type a research topic (e.g., `"AI Coding Assistants"`)
3. Click **Generate Competitive Intelligence Briefing**
4. View the full report, evaluation dashboard, and raw data tabs

### Command Line (Python)

```python
from workflow import run_workflow

result = run_workflow("AI Coding Assistants")
print(result["report"])
```

---

## 📊 Evaluation Dashboard

The dashboard (Tab 2 in the UI) shows:

| Metric | Description |
|--------|-------------|
| Sources | Total sources collected |
| Successful | Successfully scraped sources |
| Failed | Sources that failed (skipped) |
| Citations | Number of inline citations in the report |
| Time (s) | Total execution time |
| Steps Used | LangGraph steps consumed |
| Insights | Total structured insights extracted |
| Removed Claims | Claims removed for governance |
| Agent Trace | Per-step agent execution log |
| Workflow Status | completed / stopped_step_limit / error |

---

## 📁 Log Files

All logs are saved to the `logs/` directory after each run:

| File | Contents |
|------|----------|
| `research_log.json` | Sources, failed URLs, search queries |
| `analysis_log.json` | Structured analysis, removed claims, governance violations |
| `writer_log.json` | Report stats, citation count, governance summary |
| `execution_trace.json` | Full agent trace, timing, step count, errors |

Logs are **appended** (not overwritten) — every run creates a new timestamped entry.

---

## 📄 Sample Output

### Example Report Excerpt

```markdown
## Executive Summary

The AI coding assistant market is highly competitive, led by GitHub Copilot,
Cursor, and Tabnine. [Source: TechCrunch AI Tools Review](https://techcrunch.com/...)
Recent months have seen aggressive pricing changes and significant product launches
across all major players. [Source: The Verge](https://theverge.com/...)

## Competitor Pricing

- **GitHub Copilot**: Individual plan at $10/month, Business at $19/user/month
  ([Source: GitHub Pricing](https://github.com/features/copilot))
- **Cursor**: Free tier available, Pro plan at $20/month
  ([Source: Cursor.sh](https://cursor.sh/pricing))

## Competitor Product Updates

- **GitHub Copilot** launched multi-file editing and workspace features in Q3 2024
  ([Source: GitHub Blog](https://github.blog/...))
```

---

## 🧪 Test Scenarios

The system handles all 5 capstone test scenarios:

| Scenario | How it's handled |
|----------|-----------------|
| 1. Normal report generation | Full pipeline runs: Supervisor → Researcher → Analyst → Writer |
| 2. Website unavailable | `WebSearchTool` catches the exception, logs the failure, skips the URL, execution continues |
| 3. Unverified claim removal | Analyst agent's system prompt + governance rules remove unverified claims and log them |
| 4. Execution step limit | `_check_steps()` in each LangGraph node halts execution and sets `status = "stopped_step_limit"` |
| 5. Fake bankruptcy rumor | Analyst governance violation handler rejects and omits; Writer adds `"Unverified information — omitted from final report."` |

---

## 🔧 Configuration

### Changing the AI Model

OpenRouter gives you access to many models with one key:

```env
OPENROUTER_MODEL=openai/gpt-4o-mini        # Default — fast and cheap
OPENROUTER_MODEL=openai/gpt-4o             # Best quality
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_MODEL=google/gemini-flash-1.5
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
```

Browse all available models at: https://openrouter.ai/models

### Adjusting Limits

```env
MAX_SOURCES=15   # Reduce for faster runs
MAX_STEPS=20     # Reduce for testing
```

### Switching Vector Store

```env
VECTOR_STORE=faiss    # Default — no setup needed
VECTOR_STORE=chroma   # Persistent — requires chromadb
```

---

## 🔮 Future Improvements

1. **Scheduled runs** — Cron/Airflow integration for automated weekly briefings
2. **Email delivery** — Send the report via SendGrid or SES
3. **More search providers** — Bing, Google Custom Search, Perplexity
4. **Historical comparison** — Track competitor changes week over week
5. **Multi-language support** — Generate reports in French, German, Spanish
6. **Export to PDF/DOCX** — Professional document output
7. **CrewAI backend option** — Alternative to LangGraph for different orchestration needs
8. **Custom agent personas** — Domain-specific analyst prompts (fintech, healthcare, etc.)
9. **Slack/Teams integration** — Post briefings directly to collaboration channels
10. **Confidence scores** — Rate each insight by source quality and recency

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph 0.2.x |
| LLM | OpenRouter (GPT-4o-mini / Claude / Gemini / etc.) |
| Web Search | Tavily API |
| Vector Store | FAISS (default) / ChromaDB |
| Embeddings | OpenRouter → text-embedding-3-small |
| UI | Streamlit |
| Environment | python-dotenv |
| Retry Logic | tenacity |

---

## 📝 License

This project was created as part of the AI Engineering Capstone Program.

---

*Built with LangGraph + OpenAI + Tavily | Competitive Intelligence Briefing Crew v1.0*
