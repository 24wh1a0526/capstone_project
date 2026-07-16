"""
app.py  —  Competitive Intelligence Briefing Crew
Streamlit dashboard: sidebar config, topic input, report display,
evaluation dashboard, PDF + Markdown download.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ── project root ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

# ── page config  (must be the very first Streamlit call) ──────────────
st.set_page_config(
    page_title="CI Briefing Crew",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem !important; }

/* ══ SIDEBAR ══════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: #0a0f1e !important;
    border-right: 1px solid #1e2d4a;
}
section[data-testid="stSidebar"] * { color: #c8d6f0 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 { color: #e8eef8 !important; }
section[data-testid="stSidebar"] .stMetric label { color: #7a92b8 !important; font-size:.7rem; }
section[data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
    color: #60a5fa !important; font-size: 1.15rem !important;
}
section[data-testid="stSidebar"] hr { border-color: #1e2d4a !important; }
section[data-testid="stSidebar"] .stAlert {
    background: rgba(255,255,255,.04) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255,255,255,.08) !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
}

/* ══ HERO ══════════════════════════════════════════════════════════ */
.hero {
    background: linear-gradient(135deg, #060d20 0%, #0d2050 45%, #1a4fa0 100%);
    border-radius: 16px;
    padding: 2.8rem 3rem 2.4rem;
    margin-bottom: 2rem;
    box-shadow: 0 8px 40px rgba(10,40,120,0.35);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(96,165,250,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-eyebrow {
    font-size: .72rem; font-weight: 600; letter-spacing: 2.5px;
    text-transform: uppercase; color: #60a5fa; margin-bottom: .6rem;
}
.hero-title {
    font-size: 2.4rem; font-weight: 800; color: #fff;
    margin: 0 0 .5rem; letter-spacing: -.8px; line-height: 1.15;
}
.hero-title span { color: #60a5fa; }
.hero-sub {
    font-size: 1rem; color: rgba(255,255,255,.6);
    margin: 0 0 1.4rem; font-weight: 400; max-width: 580px;
}
.hero-badges { display: flex; flex-wrap: wrap; gap: 8px; }
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,.08); color: rgba(255,255,255,.85);
    border-radius: 20px; padding: 4px 14px; font-size: .73rem;
    font-weight: 500; border: 1px solid rgba(255,255,255,.14);
    backdrop-filter: blur(4px);
}

/* ══ INPUT CARD ════════════════════════════════════════════════════ */
.input-card {
    background: #fff; border: 1.5px solid #e2e8f4;
    border-radius: 14px; padding: 1.6rem 1.8rem 1.4rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.06); margin-bottom: 1.4rem;
}
.input-label {
    font-size: .72rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #1e40af; margin-bottom: .7rem;
}
div[data-testid="stTextInput"] input {
    border: 1.5px solid #d1daf0 !important; border-radius: 10px !important;
    padding: .65rem 1rem !important; font-size: .95rem !important;
    background: #f8faff !important;
    transition: border-color .2s, box-shadow .2s;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important;
}
div[data-testid="stSelectbox"] > div {
    border: 1.5px solid #d1daf0 !important;
    border-radius: 10px !important; background: #f8faff !important;
}

/* ══ GENERATE BUTTON ═══════════════════════════════════════════════ */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #3b82f6 100%) !important;
    color: #fff !important; border-radius: 12px !important;
    padding: .75rem 2.5rem !important; font-size: 1rem !important;
    font-weight: 700 !important; border: none !important;
    box-shadow: 0 4px 20px rgba(37,99,235,.4) !important;
    letter-spacing: .3px;
    transition: transform .15s, box-shadow .15s !important;
}
div[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(37,99,235,.5) !important;
}
div[data-testid="stButton"] > button:active { transform: translateY(0) !important; }

/* ══ TABS ══════════════════════════════════════════════════════════ */
div[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid #e2e8f4; gap: 0;
}
div[data-testid="stTabs"] button[role="tab"] {
    font-weight: 600; font-size: .9rem; padding: .6rem 1.4rem;
    color: #64748b !important; border-bottom: 2px solid transparent;
    margin-bottom: -2px; transition: color .15s;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #1e40af !important; border-bottom: 2px solid #2563eb;
}

/* ══ SECTION CARDS ═════════════════════════════════════════════════ */
.section-card {
    background: #fff; border: 1px solid #e8edf6; border-radius: 14px;
    padding: 1.4rem 1.6rem 1rem; margin-bottom: 1.2rem;
    box-shadow: 0 1px 8px rgba(0,0,0,.05); transition: box-shadow .2s;
}
.section-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.09); }
.section-card-title {
    font-size: .68rem; font-weight: 700; letter-spacing: 1.8px;
    text-transform: uppercase; color: #1e40af; margin-bottom: .8rem;
    display: flex; align-items: center; gap: 7px;
    padding-bottom: .6rem; border-bottom: 1px solid #eef2fb;
}

/* ══ METRIC TILES ══════════════════════════════════════════════════ */
.metric-row {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 12px; margin-bottom: 1.4rem;
}
.metric-tile {
    background: linear-gradient(145deg, #f0f6ff, #e8f0fe);
    border: 1px solid #d0e0fc; border-radius: 12px;
    padding: 1rem .8rem .85rem; text-align: center;
    box-shadow: 0 1px 4px rgba(30,64,175,.06);
}
.metric-tile .val {
    font-size: 1.8rem; font-weight: 800; color: #1e40af; line-height: 1;
}
.metric-tile .lbl {
    font-size: .68rem; color: #64748b; margin-top: 5px; font-weight: 600;
    letter-spacing: .5px; text-transform: uppercase;
}

/* ══ PIPELINE BAR ══════════════════════════════════════════════════ */
.pipeline { display: flex; align-items: center; gap: 0; margin: 1rem 0 1.6rem; }
.pipe-step {
    flex: 1; text-align: center; background: #eff6ff;
    border: 1.5px solid #bfdbfe; border-radius: 8px;
    padding: .55rem .3rem; font-size: .78rem; font-weight: 700; color: #1d4ed8;
}
.pipe-step.done  { background: #f0fdf4; border-color: #86efac; color: #15803d; }
.pipe-step.error { background: #fef2f2; border-color: #fca5a5; color: #b91c1c; }
.pipe-arrow { width: 24px; text-align: center; color: #94a3b8; font-size: 1rem; flex-shrink: 0; }

/* ══ BANNERS ═══════════════════════════════════════════════════════ */
.gov-banner {
    background: #fffbeb; border-left: 4px solid #f59e0b;
    border-radius: 0 10px 10px 0; padding: .8rem 1.1rem;
    color: #78350f; font-size: .87rem; margin-bottom: 1rem;
    display: flex; align-items: center; gap: 10px;
}

/* ══ DOWNLOAD STRIP ════════════════════════════════════════════════ */
.dl-strip {
    background: linear-gradient(90deg, #eff6ff, #f0f4ff);
    border: 1.5px solid #bfdbfe; border-radius: 12px;
    padding: 1rem 1.4rem; display: flex; align-items: center;
    gap: 14px; margin-top: 1.6rem;
}
.dl-strip-label { font-weight: 700; font-size: .9rem; color: #1e40af; flex: 1; }

/* ══ STATUS ROW ════════════════════════════════════════════════════ */
.status-row { display: flex; align-items: center; gap: 10px; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
for _k, _v in [("result", None), ("running", False), ("api_key_valid", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def check_openrouter_key(key: str) -> bool:
    if not key or not key.startswith("sk-or-"):
        return False
    try:
        import requests
        r = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_citation_count(report: str) -> int:
    total = 0
    for pat in [r'\[Source:.*?\]\(https?://.*?\)',
                r'\[(\d+)\]\s*https?://', r'\[(\d+)\]']:
        total += len(re.findall(pat, report))
    return total


def format_status_badge(status: str) -> str:
    cfg = {
        "completed":          ("#15803d", "#dcfce7", "#86efac", "Completed"),
        "error":              ("#b91c1c", "#fef2f2", "#fca5a5", "Error"),
        "stopped_step_limit": ("#c2410c", "#fff7ed", "#fed7aa", "Step Limit"),
        "running":            ("#1d4ed8", "#eff6ff", "#bfdbfe", "Running"),
    }
    col, bg, bdr, label = cfg.get(
        status, ("#475569", "#f1f5f9", "#cbd5e1", status.replace("_", " ").title())
    )
    return (
        f'<span style="background:{bg};color:{col};border:1px solid {bdr};'
        f'padding:4px 12px;border-radius:20px;font-size:.78rem;font-weight:700;'
        f'letter-spacing:.3px;">{label}</span>'
    )


def run_research(topic: str, openrouter_key: str, tavily_key: str) -> dict:
    os.environ["OPENROUTER_API_KEY"] = openrouter_key
    os.environ["TAVILY_API_KEY"]     = tavily_key
    from workflow import run_workflow
    return run_workflow(topic)


def save_logs(result: dict, topic: str):
    try:
        from logs.logger import save_all_logs
        save_all_logs(result, topic)
    except Exception as exc:
        st.warning(f"Log saving failed: {exc}")


def generate_pdf(report: str, topic: str) -> bytes:
    try:
        from ui.pdf_export import markdown_to_pdf
        return markdown_to_pdf(report, topic)
    except ImportError:
        from pdf_export import markdown_to_pdf
        return markdown_to_pdf(report, topic)


def _parse_sections(report: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    parts = re.split(r'^(##\s+.+)$', report, flags=re.MULTILINE)
    cur = "preamble"
    for p in parts:
        if p.startswith("## "):
            cur = p.strip()
        else:
            sections[cur] = p.strip()
    return sections


def _section_content(sections: dict, *keywords) -> str:
    for key, body in sections.items():
        if any(kw.lower() in key.lower() for kw in keywords):
            return body
    return ""


def _card(icon: str, title: str, body: str):
    fallback = "*No verified information available for this section.*"
    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-card-title">{icon}&nbsp; {title}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(body if body else fallback)



# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── Logo / brand ──────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:20px 4px 18px;text-align:center;
                border-bottom:1px solid #1e2d4a;margin-bottom:20px;">
        <div style="font-size:2rem;margin-bottom:6px;">&#128269;</div>
        <div style="color:#e8eef8;font-size:1.05rem;font-weight:700;letter-spacing:-.3px;">
            CI Briefing Crew
        </div>
        <div style="color:#4a6b9a;font-size:.73rem;margin-top:4px;
                    letter-spacing:.5px;text-transform:uppercase;">
            Multi-Agent Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Configuration label ────────────────────────────────────────────
    st.markdown(
        '<div style="color:#7a92b8;font-size:.68rem;font-weight:700;'
        'letter-spacing:1.8px;text-transform:uppercase;margin-bottom:10px;">'
        'Configuration</div>',
        unsafe_allow_html=True,
    )

    _or_key  = os.getenv("OPENROUTER_API_KEY", "")
    _tav_key = os.getenv("TAVILY_API_KEY", "")
    _model   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    def _key_row(label: str, present: bool):
        dot  = "#22c55e" if present else "#ef4444"
        text = "Loaded"  if present else "Missing"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;'
            f'border-radius:8px;margin-bottom:6px;background:rgba(255,255,255,.04);'
            f'border:1px solid #1e2d4a;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{dot};'
            f'flex-shrink:0;display:inline-block;"></span>'
            f'<span style="font-size:.8rem;color:#c8d6f0;flex:1;">{label}</span>'
            f'<span style="font-size:.72rem;color:{dot};font-weight:600;">{text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _key_row("OpenRouter API Key", bool(_or_key))
    _key_row("Tavily API Key",     bool(_tav_key))

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;'
        f'border-radius:8px;margin-bottom:12px;background:rgba(255,255,255,.04);'
        f'border:1px solid #1e2d4a;">'
        f'<span style="font-size:.85rem;">&#129302;</span>'
        f'<span style="font-size:.78rem;color:#7a92b8;flex:1;">Model</span>'
        f'<code style="font-size:.68rem;color:#60a5fa;background:rgba(96,165,250,.1);'
        f'padding:2px 6px;border-radius:4px;">{_model.split("/")[-1]}</code>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Override keys / model", expanded=False):
        st.caption("Leave blank to use values from .env")
        _or_override  = st.text_input("OpenRouter key", value="", type="password",
                                       key="or_override",  placeholder="sk-or-v1-...")
        _tav_override = st.text_input("Tavily key",     value="", type="password",
                                       key="tav_override", placeholder="tvly-...")
        _mdl_override = st.text_input("Model", value="", key="mdl_override",
                                       placeholder=_model)

    openrouter_key   = _or_override.strip()  or _or_key
    tavily_key       = _tav_override.strip() or _tav_key
    openrouter_model = _mdl_override.strip() or _model

    if st.button("Validate OpenRouter Key", use_container_width=True):
        with st.spinner("Checking..."):
            ok = check_openrouter_key(openrouter_key)
            st.session_state.api_key_valid = ok
    if st.session_state.api_key_valid is True:
        st.success("Key is valid")
    elif st.session_state.api_key_valid is False:
        st.error("Key invalid or unreachable")

    st.markdown('<hr style="border-color:#1e2d4a;margin:18px 0;">', unsafe_allow_html=True)

    # ── Last run stats ────────────────────────────────────────────────
    st.markdown(
        '<div style="color:#7a92b8;font-size:.68rem;font-weight:700;'
        'letter-spacing:1.8px;text-transform:uppercase;margin-bottom:12px;">'
        'Last Run Stats</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.result:
        res    = st.session_state.result
        _cit   = get_citation_count(res.get("report", ""))
        _src_n = len(res.get("sources", []))
        _fail  = len(res.get("failed_sources", []))
        _steps = res.get("step_count", 0)
        _time  = res.get("elapsed_seconds", 0)
        _stat  = res.get("status", "unknown")

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div style="background:rgba(96,165,250,.08);border:1px solid #1e3a6e;
                      border-radius:10px;padding:10px 8px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{_src_n}</div>
            <div style="font-size:.65rem;color:#4a6b9a;text-transform:uppercase;
                        letter-spacing:.5px;margin-top:3px;">Sources</div>
          </div>
          <div style="background:rgba(96,165,250,.08);border:1px solid #1e3a6e;
                      border-radius:10px;padding:10px 8px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{_cit}</div>
            <div style="font-size:.65rem;color:#4a6b9a;text-transform:uppercase;
                        letter-spacing:.5px;margin-top:3px;">Citations</div>
          </div>
          <div style="background:rgba(96,165,250,.08);border:1px solid #1e3a6e;
                      border-radius:10px;padding:10px 8px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{_steps}</div>
            <div style="font-size:.65rem;color:#4a6b9a;text-transform:uppercase;
                        letter-spacing:.5px;margin-top:3px;">Steps</div>
          </div>
          <div style="background:rgba(96,165,250,.08);border:1px solid #1e3a6e;
                      border-radius:10px;padding:10px 8px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{_time:.0f}s</div>
            <div style="font-size:.65rem;color:#4a6b9a;text-transform:uppercase;
                        letter-spacing:.5px;margin-top:3px;">Time</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if _fail:
            st.markdown(
                f'<div style="font-size:.78rem;color:#f87171;padding:4px 8px;">'
                f'&#9888; {_fail} source(s) failed</div>',
                unsafe_allow_html=True,
            )
        st.markdown(format_status_badge(_stat), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#2d4060;font-size:.82rem;font-style:italic;padding:8px 0;">'
            'No run yet — stats will appear here.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="border-color:#1e2d4a;margin:18px 0;">', unsafe_allow_html=True)

    # ── Audit logs ────────────────────────────────────────────────────
    st.markdown(
        '<div style="color:#7a92b8;font-size:.68rem;font-weight:700;'
        'letter-spacing:1.8px;text-transform:uppercase;margin-bottom:10px;">'
        'Audit Logs</div>',
        unsafe_allow_html=True,
    )
    _log_dir = PROJECT_ROOT / "logs"
    _logs    = sorted(_log_dir.glob("*.json")) if _log_dir.exists() else []
    if _logs:
        for _lf in _logs[-4:]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'padding:5px 8px;border-radius:6px;margin-bottom:4px;">'
                f'<span style="color:#3b82f6;font-size:.75rem;">&#9679;</span>'
                f'<span style="font-size:.75rem;color:#4a6b9a;">{_lf.name}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#2d4060;font-size:.78rem;font-style:italic;">'
            'Generated after first run.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="margin-top:24px;padding-top:14px;border-top:1px solid #1e2d4a;'
        'text-align:center;color:#2d4060;font-size:.7rem;">'
        'v1.0 &nbsp;&middot;&nbsp; LangGraph + OpenRouter + Tavily</div>',
        unsafe_allow_html=True,
    )



# ══════════════════════════════════════════════════════════════════════
# MAIN PAGE — HERO
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">Powered by LangGraph &nbsp;&middot;&nbsp; OpenRouter &nbsp;&middot;&nbsp; Tavily</div>
  <div class="hero-title">Competitive <span>Intelligence</span><br>Briefing Crew</div>
  <div class="hero-sub">
    Autonomous multi-agent research platform that produces cited,
    governance-checked competitive intelligence briefings in minutes.
  </div>
  <div class="hero-badges">
    <span class="badge">&#129302; LangGraph Pipeline</span>
    <span class="badge">&#128269; Tavily Web Search</span>
    <span class="badge">&#128737; Governance Engine</span>
    <span class="badge">&#128196; PDF Export</span>
    <span class="badge">&#128202; Eval Dashboard</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TOPIC INPUT
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.markdown(
    '<div class="input-label">&#127919;&nbsp; Research Topic</div>',
    unsafe_allow_html=True,
)

_examples = [
    "AI Coding Assistants",
    "Cloud Computing Platforms",
    "Electric Vehicles",
    "Generative AI Tools",
    "Project Management Software",
    "Cybersecurity Platforms",
    "FinTech Payment Solutions",
    "Healthcare AI Platforms",
]

# Single source of truth for the topic lives in session_state under
# "topic_value". The text input is bound directly to it (key=). The
# "Quick pick" dropdown never controls the topic itself — when the user
# picks an example, a callback copies that value INTO topic_value and then
# resets the dropdown back to its placeholder. Without this reset, Streamlit
# keeps the dropdown's last selection across reruns and it would silently
# override anything typed afterward — which was the original bug.
if "topic_value" not in st.session_state:
    st.session_state.topic_value = ""


def _apply_quick_pick():
    if st.session_state.quick_pick != "Quick examples...":
        st.session_state.topic_value = st.session_state.quick_pick
        st.session_state.quick_pick = "Quick examples..."  # reset so it can't override again


_col_input, _col_pick = st.columns([3, 1], gap="medium")
with _col_input:
    st.text_input(
        "topic_input",
        key="topic_value",
        placeholder="e.g.  AI Coding Assistants, Cloud Computing Platforms...",
        label_visibility="collapsed",
    )
with _col_pick:
    st.selectbox(
        "Quick pick",
        ["Quick examples..."] + _examples,
        key="quick_pick",
        on_change=_apply_quick_pick,
        label_visibility="collapsed",
    )

topic = st.session_state.topic_value

st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# GENERATE BUTTON
# ══════════════════════════════════════════════════════════════════════
_btn_col, _spacer = st.columns([2, 3])
with _btn_col:
    _clicked = st.button(
        "&#128640;  Generate Competitive Intelligence Briefing",
        disabled=st.session_state.running,
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════
# RUN LOGIC
# ══════════════════════════════════════════════════════════════════════
if _clicked:
    if not topic.strip():
        st.warning("Please enter a research topic before generating.")
    elif not openrouter_key:
        st.error("OpenRouter API key is missing. Add OPENROUTER_API_KEY to your .env file.")
    elif not tavily_key:
        st.error("Tavily API key is missing. Add TAVILY_API_KEY to your .env file.")
    else:
        os.environ["OPENROUTER_API_KEY"] = openrouter_key
        os.environ["TAVILY_API_KEY"]     = tavily_key
        os.environ["OPENROUTER_MODEL"]   = openrouter_model
        st.session_state.running = True
        st.session_state.result  = None

        _rc: dict = {}
        with st.status("Multi-Agent Workflow Running...", expanded=True) as _status_widget:
            st.markdown("""
            <div style="display:flex;flex-direction:column;gap:10px;padding:8px 0;">
              <div style="display:flex;align-items:center;gap:12px;color:#374151;">
                <span style="font-size:1.2rem;">&#129504;</span>
                <span><strong>Supervisor</strong> &mdash; planning search strategy</span>
              </div>
              <div style="display:flex;align-items:center;gap:12px;color:#374151;">
                <span style="font-size:1.2rem;">&#128269;</span>
                <span><strong>Researcher</strong> &mdash; collecting web sources</span>
              </div>
              <div style="display:flex;align-items:center;gap:12px;color:#374151;">
                <span style="font-size:1.2rem;">&#128202;</span>
                <span><strong>Analyst</strong> &mdash; extracting structured insights</span>
              </div>
              <div style="display:flex;align-items:center;gap:12px;color:#374151;">
                <span style="font-size:1.2rem;">&#9999;&#65039;</span>
                <span><strong>Writer</strong> &mdash; generating professional report</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                _rc["result"] = run_research(topic, openrouter_key, tavily_key)
                _status_widget.update(label="Briefing generated successfully!", state="complete")
            except Exception as e:
                _rc["error"] = str(e)
                _status_widget.update(label="Workflow error — see details below.", state="error")

        st.session_state.running = False

        if "error" in _rc:
            st.error(f"Workflow error: {_rc['error']}")
        else:
            st.session_state.result = _rc["result"]
            try:
                save_logs(st.session_state.result, topic)
            except Exception:
                pass
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# RESULTS — render helpers
# ══════════════════════════════════════════════════════════════════════

def _render_report(sections: dict, full_report: str, topic: str):
    """Tab 1 — styled report cards + downloads."""
    exec_body = _section_content(sections, "Executive Summary")
    st.markdown(
        '<div class="section-card">'
        '<div class="section-card-title">&#128203;&nbsp; Executive Summary</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(exec_body or "*No summary available.*")
    st.markdown("<br>", unsafe_allow_html=True)

    # "What Changed Since Last Briefing" — populated by the Analyst/Writer
    # when a prior briefing exists for this exact topic. Rendered here so it
    # doesn't just live invisibly inside the raw report text.
    changes_body = _section_content(sections, "What Changed", "Since Last Briefing")
    if changes_body:
        _card("&#128260;", "What Changed Since Last Briefing", changes_body)
        st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        _card("&#128176;", "Competitor Pricing",
              _section_content(sections, "Competitor Pricing", "Pricing"))
        _card("&#128225;", "Market Signals",
              _section_content(sections, "Market Signals"))
    with col_r:
        _card("&#128640;", "Competitor Product Updates",
              _section_content(sections, "Product Update", "Product Move"))
        _card("&#128161;", "Strategic Recommendations",
              _section_content(sections, "Recommendation")
              or "*No verified recommendations available.*")

    refs_body = _section_content(sections, "Reference")
    if refs_body:
        with st.expander("References", expanded=False):
            st.markdown(refs_body)

    meta_body = _section_content(sections, "Metadata", "Run Metadata")
    if meta_body:
        with st.expander("Run Metadata", expanded=False):
            st.markdown(meta_body)

    fname_base = f"ci_briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.markdown(
        '<div class="dl-strip">'
        '<div class="dl-strip-label">&#11015;&#65039;&nbsp; Download your briefing</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    dl1, dl2 = st.columns(2, gap="medium")
    with dl1:
        st.download_button(
            label="Download as PDF",
            data=generate_pdf(full_report, topic),
            file_name=fname_base + ".pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            label="Download as Markdown",
            data=full_report,
            file_name=fname_base + ".md",
            mime="text/markdown",
            use_container_width=True,
        )


def _render_dashboard(r: dict):
    """Tab 2 — metrics, pipeline, agent trace."""
    report   = r.get("report", "")
    sources  = r.get("sources", [])
    failed   = r.get("failed_sources", [])
    trace    = r.get("agent_trace", [])
    status   = r.get("status", "unknown")
    elapsed  = r.get("elapsed_seconds", 0)
    steps    = r.get("step_count", 0)
    analysis = r.get("analysis", {})
    citations = get_citation_count(report)
    insights  = (len(analysis.get("competitor_pricing", [])) +
                 len(analysis.get("product_updates", [])) +
                 len(analysis.get("market_signals", [])))
    removed   = (len(analysis.get("removed_claims", [])) +
                 len(analysis.get("governance_violations", [])))

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-tile"><div class="val">{len(sources)}</div><div class="lbl">Sources</div></div>
      <div class="metric-tile"><div class="val">{len(sources)-len(failed)}</div><div class="lbl">Successful</div></div>
      <div class="metric-tile"><div class="val">{len(failed)}</div><div class="lbl">Failed</div></div>
      <div class="metric-tile"><div class="val">{citations}</div><div class="lbl">Citations</div></div>
      <div class="metric-tile"><div class="val">{insights}</div><div class="lbl">Insights</div></div>
      <div class="metric-tile"><div class="val">{removed}</div><div class="lbl">Removed</div></div>
      <div class="metric-tile"><div class="val">{steps}</div><div class="lbl">Steps</div></div>
      <div class="metric-tile"><div class="val">{elapsed:.0f}s</div><div class="lbl">Time</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div class="status-row"><strong>Workflow Status</strong>&nbsp;'
        f'{format_status_badge(status)}</div>',
        unsafe_allow_html=True,
    )

    completed_agents = {t["agent"] for t in trace if "error" not in t}
    stages    = ["Supervisor", "Researcher", "Analyst", "Writer"]
    pipe_html = ""
    for i, s in enumerate(stages):
        cls = "done" if s in completed_agents else "error"
        pipe_html += f'<div class="pipe-step {cls}">{s}</div>'
        if i < len(stages) - 1:
            pipe_html += '<div class="pipe-arrow">&#8250;</div>'
    st.markdown(f'<div class="pipeline">{pipe_html}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Agent Execution Trace")
    if trace:
        for t in trace:
            with st.expander(
                f"Step {t.get('step','?')} · {t.get('agent','?')} — {t.get('action','')}",
                expanded=False,
            ):
                if t.get("result"):
                    st.markdown(f"**Result:** {t['result']}")
                if t.get("error"):
                    st.error(f"**Error:** {t['error']}")
    else:
        st.info("No trace available.")

    if failed:
        st.divider()
        st.markdown("#### Failed Sources")
        st.caption(f"{len(failed)} source(s) skipped — execution continued.")
        for f in failed:
            st.markdown(f"- `{f.get('url','?')}` — *{f.get('reason','?')}*")


def _render_raw(r: dict):
    """Tab 3 — raw JSON."""
    with st.expander("Analysis JSON", expanded=False):
        st.json(r.get("analysis", {}))
    with st.expander("Source Documents", expanded=False):
        srcs = r.get("sources", [])
        st.caption(f"{len(srcs)} sources collected")
        for i, s in enumerate(srcs[:10]):
            st.markdown(
                f"**{i+1}. {s.get('title','Untitled')}**  \n"
                f"URL: {s.get('url','')}  \n"
                f"Date: {s.get('published_date','N/A')}  \n"
                f"Preview: *{s.get('content','')[:200]}...*"
            )
            st.divider()
    with st.expander("Failed Sources", expanded=False):
        fails = r.get("failed_sources", [])
        if fails:
            for f in fails:
                st.markdown(f"- `{f.get('url','?')}`: {f.get('reason','')}")
        else:
            st.success("No failures — all sources loaded successfully.")
    with st.expander("Full Workflow State (JSON)", expanded=False):
        safe = {k: v for k, v in r.items()
                if k not in ("openrouter_key", "openai_key", "tavily_key")}
        st.json(safe)


# ══════════════════════════════════════════════════════════════════════
# RESULTS SECTION
# ══════════════════════════════════════════════════════════════════════
if st.session_state.result:
    _r      = st.session_state.result
    _report = _r.get("report", "")
    _status = _r.get("status", "unknown")
    _topic  = _r.get("topic", "Competitive Intelligence Report")

    if _status == "completed":
        st.success("Briefing generated successfully!")
    elif _status == "stopped_step_limit":
        st.warning("Step limit reached — partial report available.")
    elif _status == "error":
        st.error("; ".join(_r.get("errors", ["Unknown error"])))

    if _status == "completed" and _r.get("errors"):
        st.warning("; ".join(_r["errors"]))

    _flags = _r.get("governance_flags", [])
    if _flags:
        st.markdown(
            f'<div class="gov-banner">'
            f'&#128737;&nbsp; <strong>Governance:</strong>&nbsp;'
            f' {len(_flags)} claim(s) removed as unverified &mdash;'
            f' "Unverified information omitted from final report."'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    _tab1, _tab2, _tab3 = st.tabs([
        "&#128196;  Full Report",
        "&#128202;  Evaluation Dashboard",
        "&#128270;  Raw Data",
    ])

    with _tab1:
        if _report:
            _render_report(_parse_sections(_report), _report, _topic)
        else:
            st.info("No report content to display.")

    with _tab2:
        _render_dashboard(_r)

    with _tab3:
        _render_raw(_r)