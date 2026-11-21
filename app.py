"""
FactGuard AI — Automated PDF Fact-Checking Agent
==================================================
Extracts factual claims from PDFs, verifies them against live web data,
and flags each as: Verified | Inaccurate | False (No Evidence)

Tech Stack:
  - Streamlit (UI)
  - pypdf (PDF extraction)
  - Google Gemini 1.5 Flash (Claim extraction + Verdict generation)
  - Tavily Search API (Live web verification)
"""

import streamlit as st
import json
import time
import re
from io import BytesIO

# -- PDF Reading --
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

# -- LLM (new google-genai SDK) --
from google import genai
from google.genai import types

# -- Search --
from tavily import TavilyClient

# ==============================================================================
# PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="FactGuard AI -- PDF Fact Checker",
    page_icon="magnifying_glass",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# CUSTOM CSS -- Premium Dark Mode
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
html, body, [data-testid="stAppViewContainer"] {
    background: #0d1117 !important; color: #e6edf3 !important;
}
[data-testid="stSidebar"] {
    background: #161b22 !important; border-right: 1px solid #30363d !important;
}
.header-banner {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 50%, #0a0e14 100%);
    border: 1px solid #30363d; border-radius: 16px; padding: 32px 36px;
    margin-bottom: 24px; position: relative; overflow: hidden;
}
.header-banner::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #58a6ff, #3fd6a4, #c792ea);
}
.header-title {
    font-size: 2.4rem; font-weight: 800;
    background: linear-gradient(135deg, #58a6ff 0%, #3fd6a4 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin: 0 0 8px 0; line-height: 1.1;
}
.header-subtitle { color: #8b94a3; font-size: 1.0rem; font-weight: 400; margin: 0; }
.badge { padding: 4px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.5px; }
.badge-blue  { background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.3); }
.badge-green { background: rgba(63,214,164,0.15); color: #3fd6a4; border: 1px solid rgba(63,214,164,0.3); }
.badge-purple{ background: rgba(199,146,234,0.15); color: #c792ea; border: 1px solid rgba(199,146,234,0.3); }
[data-testid="stFileUploader"] {
    background: #161b22 !important; border: 2px dashed #30363d !important;
    border-radius: 12px !important; padding: 20px !important;
}
[data-testid="stTextInput"] input {
    background: #0d1117 !important; border: 1px solid #30363d !important;
    border-radius: 8px !important; color: #e6edf3 !important;
}
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    padding: 12px 28px !important; font-weight: 600 !important; width: 100%;
    box-shadow: 0 4px 15px rgba(31,111,235,0.3) !important;
}
.claim-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px;
}
.claim-card.verified   { border-left: 4px solid #2ea043; }
.claim-card.inaccurate { border-left: 4px solid #e3b341; }
.claim-card.false      { border-left: 4px solid #cf222f; }
.verdict-pill { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.pill-verified   { background: rgba(46,160,67,0.2);  color: #3fb950; border: 1px solid rgba(46,160,67,0.4); }
.pill-inaccurate { background: rgba(227,179,65,0.2); color: #e3b341; border: 1px solid rgba(227,179,65,0.4); }
.pill-false      { background: rgba(207,34,47,0.2);  color: #f85149; border: 1px solid rgba(207,34,47,0.4); }
.claim-text { font-size: 0.95rem; font-weight: 500; color: #e6edf3; margin-bottom: 10px; line-height: 1.5; }
.explanation-text { font-size: 0.85rem; color: #8b94a3; line-height: 1.6; margin-bottom: 12px; }
.correction-box {
    background: rgba(63,214,164,0.08); border: 1px solid rgba(63,214,164,0.3);
    border-radius: 8px; padding: 10px 14px; font-size: 0.84rem; color: #3fd6a4; margin-bottom: 10px;
}
.source-link { color: #58a6ff; font-size: 0.78rem; text-decoration: none; margin-right: 10px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }
.stat-number { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.stat-label  { font-size: 0.78rem; color: #8b94a3; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }
.stat-verified   { color: #3fb950; } .stat-inaccurate { color: #e3b341; }
.stat-false      { color: #f85149; } .stat-total      { color: #58a6ff; }
.section-header { font-size: 1.1rem; font-weight: 700; color: #e6edf3; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }
.info-box { background: rgba(88,166,255,0.08); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px 18px; font-size: 0.85rem; color: #8b94a3; margin: 16px 0; }
.warning-box { background: rgba(227,179,65,0.08); border: 1px solid rgba(227,179,65,0.3); border-radius: 10px; padding: 14px 18px; font-size: 0.85rem; color: #e3b341; margin: 16px 0; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 20px;">
        <div style="font-size:2.5rem;">&#128269;</div>
        <div style="font-size:1.1rem; font-weight:700; color:#58a6ff;">FactGuard AI</div>
        <div style="font-size:0.75rem; color:#8b94a3;">PDF Truth Layer</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="color:#8b94a3; font-size:0.78rem; font-weight:600; letter-spacing:1px; margin-bottom:6px;">API CREDENTIALS</div>', unsafe_allow_html=True)

    gemini_key = st.text_input("Google Gemini API Key", type="password", placeholder="AIza...", help="Get free key at: aistudio.google.com (use API key, not OAuth)")
    tavily_key = st.text_input("Tavily Search API Key", type="password", placeholder="tvly-...", help="Get free key at: tavily.com")

    st.markdown("---")
    st.markdown('<div style="color:#8b94a3; font-size:0.78rem; font-weight:600; letter-spacing:1px; margin-bottom:6px;">SETTINGS</div>', unsafe_allow_html=True)

    max_claims = st.slider("Max claims to verify", min_value=3, max_value=15, value=8)
    search_depth = st.selectbox("Search depth", ["basic", "advanced"], index=1)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; color:#8b94a3; line-height:1.8;">
        <strong style="color:#e6edf3;">How it works</strong><br>
        1. Upload a PDF document<br>
        2. AI extracts factual claims<br>
        3. Live web search verifies each<br>
        4. Report flags Verified / Inaccurate / False
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#8b94a3;">
        <a href="https://aistudio.google.com" style="color:#58a6ff;">Get Gemini Key</a>
        &nbsp;&middot;&nbsp;
        <a href="https://tavily.com" style="color:#58a6ff;">Get Tavily Key</a>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# HEADER
# ==============================================================================
st.markdown("""
<div class="header-banner">
    <h1 class="header-title">FactGuard AI</h1>
    <p class="header-subtitle">
        Automated PDF fact-checking powered by AI. Upload any document and instantly verify
        every claim against live web data.
    </p>
    <div style="display:flex; gap:10px; margin-top:16px; flex-wrap:wrap;">
        <span class="badge badge-blue">PDF Analysis</span>
        <span class="badge badge-green">Live Web Verification</span>
        <span class="badge badge-purple">Gemini + Tavily</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def extract_pdf_text(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.read()))
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n\n"
    return text.strip(), len(reader.pages)


def extract_claims_with_gemini(text, client, max_claims):
    prompt = f"""You are an expert fact-checker analyzing a document for verifiable claims.

Analyze the following text and extract up to {max_claims} distinct, specific, verifiable factual claims.
Focus on: statistics and percentages, financial figures, dates and historical facts, scientific/technical claims, named entity facts, rankings.

Only extract claims that CAN be verified against external sources. Skip vague opinions.

Return ONLY a valid JSON array (no markdown, no explanation):
[
  {{
    "claim": "The exact verifiable claim as stated in the document",
    "category": "one of: statistic|financial|date|technical|scientific|comparative|other",
    "search_query": "optimized search query to verify this claim on the web"
  }}
]

Document text:
{text[:20000]}"""

    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    raw = response.text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)

    try:
        claims = json.loads(raw)
        if not isinstance(claims, list):
            claims = []
    except json.JSONDecodeError:
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            try:
                claims = json.loads(match.group())
            except Exception:
                claims = []
        else:
            claims = []

    return claims[:max_claims]


def verify_claim(claim_obj, tavily_client, client, search_depth):
    claim = claim_obj.get("claim", "")
    search_query = claim_obj.get("search_query", claim)

    try:
        results = tavily_client.search(query=search_query, max_results=5, search_depth=search_depth, include_raw_content=False)
        web_results = results.get("results", [])
    except Exception:
        web_results = []

    context = ""
    source_urls = []
    for r in web_results:
        context += f"SOURCE: {r.get('title', '')} ({r.get('url', '')})\nCONTENT: {r.get('content', '')}\n\n"
        source_urls.append({"title": r.get("title", r.get("url", "")), "url": r.get("url", "")})

    if context:
        verification_prompt = f"""You are a strict, professional fact-checker. Verify this claim using the web evidence.

CLAIM: "{claim}"

WEB EVIDENCE:
{context}

Respond with ONLY valid JSON (no markdown):
{{
  "verdict": "VERIFIED" | "INACCURATE" | "FALSE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "explanation": "2-3 sentence explanation citing specific evidence",
  "correction": "If INACCURATE or FALSE: provide the correct fact. If VERIFIED: null",
  "real_data": "If the claim has a wrong number/date/figure: state the correct value. Otherwise: null"
}}

Verdict definitions:
- VERIFIED: Claim is accurate and supported by evidence
- INACCURATE: Claim contains outdated, exaggerated, or partially wrong data
- FALSE: Claim is directly contradicted by evidence or no credible evidence supports it"""
    else:
        verification_prompt = f"""No web results were found for this claim: "{claim}"

Respond with ONLY valid JSON:
{{
  "verdict": "FALSE",
  "confidence": "LOW",
  "explanation": "No credible web evidence found to support this claim.",
  "correction": "Unable to verify -- claim may be fabricated or highly niche.",
  "real_data": null
}}"""

    try:
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=verification_prompt)
        raw = resp.text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        verdict_data = json.loads(raw)
    except Exception:
        verdict_data = {"verdict": "FALSE", "confidence": "LOW", "explanation": "Verification failed.", "correction": None, "real_data": None}

    return {**claim_obj, "verdict": verdict_data.get("verdict", "FALSE"), "confidence": verdict_data.get("confidence", "LOW"),
            "explanation": verdict_data.get("explanation", ""), "correction": verdict_data.get("correction"),
            "real_data": verdict_data.get("real_data"), "sources": source_urls}


def render_verdict_pill(verdict):
    mapping = {
        "VERIFIED":   ("pill-verified",   "VERIFIED"),
        "INACCURATE": ("pill-inaccurate", "INACCURATE"),
        "FALSE":      ("pill-false",      "FALSE"),
    }
    cls, label = mapping.get(verdict, ("pill-unverified", "UNVERIFIED"))
    return f'<span class="verdict-pill {cls}">{label}</span>'


def render_claim_card(result, index):
    verdict = result.get("verdict", "FALSE").upper()
    card_class = verdict.lower() if verdict in ["VERIFIED", "INACCURATE", "FALSE"] else "unverified"
    category = result.get("category", "other").upper()
    pill_html = render_verdict_pill(verdict)
    confidence = result.get("confidence", "")

    html = f"""
    <div class="claim-card {card_class}">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            {pill_html}
            <span style="font-size:0.72rem; color:#8b94a3; background:#0d1117; padding:3px 10px; border-radius:12px;">#{index} &middot; {category}</span>
            <span style="font-size:0.72rem; color:#8b94a3; margin-left:auto;">Confidence: <strong style="color:#e6edf3;">{confidence}</strong></span>
        </div>
        <div class="claim-text">"{result.get('claim', '')}"</div>
        <div class="explanation-text">{result.get('explanation', '')}</div>
    """
    correction = result.get("correction")
    real_data = result.get("real_data")
    if correction and verdict in ["INACCURATE", "FALSE"]:
        html += f'<div class="correction-box"><strong>Correct Info:</strong> {correction}'
        if real_data:
            html += f'<br><strong>Real Data:</strong> {real_data}'
        html += '</div>'
    sources = result.get("sources", [])
    if sources:
        html += '<div style="margin-top:8px;"><span style="font-size:0.75rem; color:#8b94a3; font-weight:600;">SOURCES: </span>'
        for s in sources[:3]:
            url = s.get("url", "")
            title = s.get("title", url)[:50] + ("..." if len(s.get("title", url)) > 50 else "")
            html += f'<a href="{url}" target="_blank" class="source-link">{title}</a>'
        html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ==============================================================================
# MAIN APP
# ==============================================================================

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown('<div class="section-header">Upload Document</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Drop your PDF here", type=["pdf"], label_visibility="collapsed")
with col2:
    st.markdown('<div class="section-header">Status</div>', unsafe_allow_html=True)
    if uploaded_file:
        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #2ea043; border-radius:10px; padding:14px; margin-top:4px;">
            <div style="color:#3fb950; font-weight:600; font-size:0.9rem;">{uploaded_file.name}</div>
            <div style="color:#8b94a3; font-size:0.78rem; margin-top:4px;">{uploaded_file.size / 1024:.1f} KB &middot; PDF Document</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">Upload a PDF to begin automated fact-checking.</div>', unsafe_allow_html=True)

if not gemini_key or not tavily_key:
    st.markdown('<div class="warning-box"><strong>API Keys Required</strong> -- Enter your Gemini and Tavily API keys in the sidebar. Both are free to obtain.</div>', unsafe_allow_html=True)

run_btn = st.button("Run Fact-Check Analysis", disabled=(not uploaded_file or not gemini_key or not tavily_key))

# ==============================================================================
# ANALYSIS PIPELINE
# ==============================================================================
if run_btn and uploaded_file and gemini_key and tavily_key:

    try:
        client = genai.Client(api_key=gemini_key)
        tavily_client = TavilyClient(api_key=tavily_key)
    except Exception as e:
        st.error(f"Failed to initialize API clients: {e}")
        st.stop()

    st.markdown("---")

    with st.spinner("Reading and extracting PDF text..."):
        try:
            pdf_text, page_count = extract_pdf_text(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read PDF: {e}")
            st.stop()

    if not pdf_text:
        st.error("Could not extract text from this PDF. It may be scanned/image-based.")
        st.stop()

    with st.expander(f"Extracted Text Preview ({page_count} pages)", expanded=False):
        st.text(pdf_text[:3000] + ("..." if len(pdf_text) > 3000 else ""))

    with st.spinner(f"AI analyzing document and extracting up to {max_claims} factual claims..."):
        try:
            claims = extract_claims_with_gemini(pdf_text, client, max_claims)
        except Exception as e:
            st.error(f"Claim extraction failed: {e}")
            st.stop()

    if not claims:
        st.warning("No verifiable factual claims were found in this document.")
        st.stop()

    st.success(f"Extracted {len(claims)} verifiable claims. Beginning live web verification...")

    results = []
    progress_bar = st.progress(0, text="Verifying claims against live web data...")

    for i, claim_obj in enumerate(claims):
        progress_pct = i / len(claims)
        progress_bar.progress(progress_pct, text=f"Verifying claim {i+1}/{len(claims)}: {claim_obj.get('claim', '')[:60]}...")
        try:
            result = verify_claim(claim_obj, tavily_client, client, search_depth)
            results.append(result)
        except Exception as e:
            results.append({**claim_obj, "verdict": "FALSE", "confidence": "LOW",
                            "explanation": f"Verification error: {str(e)}", "correction": None, "real_data": None, "sources": []})
        time.sleep(0.5)

    progress_bar.progress(1.0, text="Analysis complete!")
    time.sleep(0.5)
    progress_bar.empty()

    # -- RESULTS DASHBOARD --
    st.markdown("---")
    st.markdown('<h2 style="color:#e6edf3; font-size:1.6rem; font-weight:800;">Fact-Check Report</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#8b94a3;">Analyzed <strong style="color:#e6edf3;">{len(results)}</strong> claims from <strong style="color:#e6edf3;">{uploaded_file.name}</strong></p>', unsafe_allow_html=True)

    n_verified   = sum(1 for r in results if r.get("verdict") == "VERIFIED")
    n_inaccurate = sum(1 for r in results if r.get("verdict") == "INACCURATE")
    n_false      = sum(1 for r in results if r.get("verdict") == "FALSE")
    n_total      = len(results)
    accuracy_pct = round(n_verified / n_total * 100) if n_total > 0 else 0

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card"><div class="stat-number stat-total">{n_total}</div><div class="stat-label">Total Claims</div></div>
        <div class="stat-card"><div class="stat-number stat-verified">{n_verified}</div><div class="stat-label">Verified</div></div>
        <div class="stat-card"><div class="stat-number stat-inaccurate">{n_inaccurate}</div><div class="stat-label">Inaccurate</div></div>
        <div class="stat-card"><div class="stat-number stat-false">{n_false}</div><div class="stat-label">False / No Evidence</div></div>
    </div>
    """, unsafe_allow_html=True)

    gauge_color = "#3fb950" if accuracy_pct >= 70 else "#e3b341" if accuracy_pct >= 40 else "#f85149"
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:16px 20px; margin-bottom:24px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:0.85rem; color:#8b94a3; font-weight:600;">DOCUMENT ACCURACY SCORE</span>
            <span style="font-size:1.4rem; font-weight:800; color:{gauge_color};">{accuracy_pct}%</span>
        </div>
        <div style="background:#0d1117; border-radius:6px; height:8px; overflow:hidden;">
            <div style="width:{accuracy_pct}%; height:100%; background:{gauge_color}; border-radius:6px;"></div>
        </div>
        <div style="font-size:0.78rem; color:#8b94a3; margin-top:8px;">
            {'High accuracy document.' if accuracy_pct >= 70 else 'Contains questionable claims -- review recommended.' if accuracy_pct >= 40 else 'WARNING: Document contains significant inaccuracies or false claims.'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_all, tab_verified, tab_inaccurate, tab_false = st.tabs([
        f"All ({n_total})", f"Verified ({n_verified})", f"Inaccurate ({n_inaccurate})", f"False ({n_false})"
    ])

    def render_filtered(verdict_filter=None):
        filtered = results if verdict_filter is None else [r for r in results if r.get("verdict") == verdict_filter]
        if not filtered:
            st.markdown('<div class="info-box">No claims in this category.</div>', unsafe_allow_html=True)
        else:
            for i, result in enumerate(filtered, 1):
                render_claim_card(result, i)

    with tab_all:        render_filtered(None)
    with tab_verified:   render_filtered("VERIFIED")
    with tab_inaccurate: render_filtered("INACCURATE")
    with tab_false:      render_filtered("FALSE")

    # -- Download Report --
    st.markdown("---")
    st.markdown('<div class="section-header">Export Report</div>', unsafe_allow_html=True)

    report_json = json.dumps({
        "document": uploaded_file.name, "total_claims": n_total,
        "verified": n_verified, "inaccurate": n_inaccurate, "false": n_false,
        "accuracy_score": f"{accuracy_pct}%", "claims": results
    }, indent=2)

    report_lines = [
        "=" * 70, "FACTGUARD AI -- FACT-CHECK REPORT", "=" * 70,
        f"Document: {uploaded_file.name}",
        f"Total: {n_total} | Verified: {n_verified} | Inaccurate: {n_inaccurate} | False: {n_false}",
        f"Accuracy Score: {accuracy_pct}%", "=" * 70, "",
    ]
    for i, r in enumerate(results, 1):
        report_lines += [
            f"CLAIM #{i}: {r.get('claim', '')}", f"VERDICT: {r.get('verdict', '')} (Confidence: {r.get('confidence', '')})",
            f"EXPLANATION: {r.get('explanation', '')}",
        ]
        if r.get("correction"): report_lines.append(f"CORRECTION: {r.get('correction')}")
        if r.get("real_data"):  report_lines.append(f"REAL DATA: {r.get('real_data')}")
        if r.get("sources"):    report_lines.append(f"SOURCES: {', '.join(s.get('url','') for s in r.get('sources',[])[:3])}")
        report_lines.append("-" * 60)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("Download JSON Report", data=report_json,
            file_name=f"factguard_report.json", mime="application/json")
    with dl2:
        st.download_button("Download Text Report", data="\n".join(report_lines),
            file_name=f"factguard_report.txt", mime="text/plain")

elif not run_btn:
    st.markdown("---")
    st.markdown("""
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-top:8px;">
        <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px;">
            <div style="font-size:1.8rem; margin-bottom:12px;">&#128196;</div>
            <div style="font-weight:700; color:#e6edf3; margin-bottom:8px;">Smart Extraction</div>
            <div style="color:#8b94a3; font-size:0.85rem; line-height:1.6;">Gemini AI reads your PDF and identifies specific verifiable claims -- statistics, dates, figures, and technical assertions.</div>
        </div>
        <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px;">
            <div style="font-size:1.8rem; margin-bottom:12px;">&#127760;</div>
            <div style="font-weight:700; color:#e6edf3; margin-bottom:8px;">Live Web Verification</div>
            <div style="color:#8b94a3; font-size:0.85rem; line-height:1.6;">Each claim is cross-referenced against live web data using Tavily's AI-optimized search engine for maximum accuracy.</div>
        </div>
        <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px;">
            <div style="font-size:1.8rem; margin-bottom:12px;">&#127919;</div>
            <div style="font-weight:700; color:#e6edf3; margin-bottom:8px;">Verdict Report</div>
            <div style="color:#8b94a3; font-size:0.85rem; line-height:1.6;">Claims are flagged as <strong style="color:#3fb950;">Verified</strong>, <strong style="color:#e3b341;">Inaccurate</strong>, or <strong style="color:#f85149;">False</strong>, with corrections and sources.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
