"""
app.py — Streamlit UI wrapper around the Résumé × JD Analyser pipeline.

Run with:  streamlit run app.py

Reuses parse.py / analyzer.py / report.py unchanged — this file only
handles input widgets, progress, and presentation.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Anchor all relative paths (.env, inputs/) to this file's folder,
# regardless of where `streamlit run` was invoked from.
os.chdir(Path(__file__).parent)
load_dotenv()

import llm  # noqa: E402  (must come after load_dotenv)
from parse import read_resume_pdf, read_jd_text  # noqa: E402
from analyzer import (  # noqa: E402
    extract_resume_profile,
    extract_jd_profile,
    analyse_keyword_match,
    analyse_bullets,
    analyse_jargon,
    analyse_structure,
    analyse_background_fit,
    summarise_overall,
    compute_overall_score,
)
from report import _build_lines  # noqa: E402

MODELS = ["openai/gpt-4o-mini", "ollama/gemma4:e2b"]
BUNDLED_JDS = sorted(Path("inputs").glob("*.txt"))

st.set_page_config(page_title="Résumé × JD Analyser", page_icon="📄", layout="wide")


# ---------------------------------------------------------------------------
# Sidebar — model picker
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")
    model = st.selectbox("LLM model", MODELS, index=MODELS.index(os.getenv("MODEL"))
                         if os.getenv("MODEL") in MODELS else 0)
    st.caption(
        "OpenAI needs `OPENAI_API_KEY` in `.env`. "
        "Ollama needs `ollama serve` running locally."
    )
    st.divider()
    st.markdown(
        "**How scoring works**\n\n"
        "| Component | Weight |\n|---|---|\n"
        "| Keyword match | 40% |\n| Bullet quality | 25% |\n"
        "| Structure | 15% |\n| Jargon | 10% |\n| Background fit | 10% |\n\n"
        "Pass threshold: **60/100** (typical ATS)."
    )


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

st.title("📄 Résumé × JD Analyser")
st.caption(
    "Feedback-only ATS screening: the pipeline scores and explains — "
    "it never rewrites your résumé."
)

col_resume, col_jd = st.columns(2)

with col_resume:
    st.subheader("1 · Résumé (PDF)")
    pdf_file = st.file_uploader("Upload a PDF résumé", type=["pdf"])

with col_jd:
    st.subheader("2 · Job description")
    jd_source = st.radio("JD source", ["Bundled sample", "Paste text"],
                         horizontal=True, label_visibility="collapsed")
    if jd_source == "Bundled sample":
        jd_choice = st.selectbox("Sample JD", BUNDLED_JDS,
                                 format_func=lambda p: p.name)
        jd_text_input = jd_choice.read_text(encoding="utf-8") if jd_choice else ""
    else:
        jd_text_input = st.text_area("Paste the job description",
                                     height=220,
                                     placeholder="Paste the full JD text here…")
    if jd_text_input:
        with st.expander("Preview JD"):
            st.text(jd_text_input[:3000])

run = st.button("🔍 Analyse", type="primary",
                disabled=not (pdf_file and jd_text_input and jd_text_input.strip()))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

if run:
    # llm.py reads _MODEL once at import; point it at the picked model.
    os.environ["MODEL"] = model
    llm._MODEL = model

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_file.getvalue())
            tmp_path = tmp.name
        try:
            resume_text = read_resume_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)

        jd_text = jd_text_input.strip()
        if len(jd_text) < 100:
            raise ValueError("Job description has fewer than 100 characters.")

        stages = 8
        progress = st.progress(0, text="Starting…")

        def step(i: int, label: str):
            progress.progress(i / stages, text=f"[{i}/{stages}] {label}")

        step(1, "Extracting résumé profile (LLM)…")
        resume_profile = extract_resume_profile(resume_text)
        step(2, "Extracting JD profile (LLM)…")
        jd_profile = extract_jd_profile(jd_text)
        step(3, "Keyword match (LLM)…")
        keyword_match = analyse_keyword_match(resume_profile, jd_profile)
        step(4, "Bullet audit (LLM)…")
        bullets = analyse_bullets(resume_profile)
        step(5, "Jargon audit (LLM)…")
        jargon = analyse_jargon(resume_profile, jd_profile)
        step(6, "Structure audit (LLM)…")
        structure = analyse_structure(resume_text)
        step(7, "Background fit (LLM)…")
        background_fit = analyse_background_fit(resume_profile, jd_profile)

        report = {
            "meta": {
                "resume_path": pdf_file.name,
                "job_path": "(streamlit input)",
                "model": model,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            },
            "resume_profile": resume_profile,
            "jd_profile": jd_profile,
            "keyword_match": keyword_match,
            "bullets": bullets,
            "jargon": jargon,
            "structure": structure,
            "background_fit": background_fit,
        }
        report["overall_score"] = compute_overall_score(report)
        report["passes_ats_threshold"] = report["overall_score"] >= 60

        step(8, "Final summary (LLM)…")
        report["summary"] = summarise_overall(report)
        progress.progress(1.0, text="Done")

        st.session_state["report"] = report
    except (ValueError, RuntimeError) as exc:
        st.error(f"{exc}")
        st.stop()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

report = st.session_state.get("report")
if report:
    score = report["overall_score"]
    passed = report["passes_ats_threshold"]
    km = report["keyword_match"]
    bl = report["bullets"]
    ja = report["jargon"]
    stru = report["structure"]
    bg = report["background_fit"]

    st.divider()
    head_l, head_r = st.columns([1, 2])
    with head_l:
        st.metric("Overall score", f"{score}/100",
                  delta=f"{score - 60:+d} vs threshold")
        if passed:
            st.success("**PASS** — clears the 60% ATS threshold")
        else:
            st.error("**FAIL** — below the 60% ATS threshold")
        st.caption(f"Model: `{report['meta']['model']}` · "
                   f"{report['meta']['generated_at']}")
    with head_r:
        st.markdown("#### Executive summary")
        st.markdown(report["summary"])

    st.markdown("#### Score breakdown")
    components = [
        ("Keyword match", km.get("keyword_match_score", 0), 0.40),
        ("Bullet quality", bl.get("bullet_quality_avg", 0), 0.25),
        ("Structure", stru.get("structure_score", 0), 0.15),
        ("Jargon", ja.get("jargon_score", 0), 0.10),
        ("Background fit", bg.get("background_fit_score", 0), 0.10),
    ]
    for name, raw, weight in components:
        c1, c2, c3 = st.columns([2, 6, 2])
        c1.write(f"**{name}**")
        c2.progress(min(max(int(raw), 0), 100) / 100)
        c3.write(f"{raw}/100 × {int(weight * 100)}% = "
                 f"**{round(raw * weight, 1)}**")

    with st.expander(f"🔑 Keyword match — {km.get('keyword_match_score', 0)}/100",
                     expanded=not passed):
        kc1, kc2 = st.columns(2)
        kc1.markdown("**Present**")
        kc1.dataframe(km.get("present", []), width="stretch")
        kc2.markdown("**Missing**")
        kc2.dataframe(km.get("missing", []), width="stretch")

    with st.expander(f"📝 Bullet quality — {bl.get('bullet_quality_avg', 0)}/100 "
                     "(Action → Technology → Impact)"):
        st.dataframe(bl.get("bullets", []), width="stretch")

    with st.expander(f"🗣️ Terminology / jargon — {ja.get('jargon_score', 0)}/100"):
        flags = ja.get("flags", [])
        if flags:
            st.dataframe(flags, width="stretch")
        else:
            st.write("No terminology mismatches raised. ✓")

    with st.expander(f"🏗️ Structure & ATS formatting — "
                     f"{stru.get('structure_score', 0)}/100"):
        checks = [
            ("Single-column layout", stru.get("single_column_likely")),
            ("Reverse-chronological order", stru.get("reverse_chronological_likely")),
            ("Contact info at top", stru.get("contact_info_at_top")),
            ("Appropriate length", stru.get("length_appropriate")),
            ("No images / graphics", stru.get("no_images_or_graphics")),
        ]
        st.write(" · ".join(f"{'✅' if ok else '❌'} {label}" for label, ok in checks))
        st.write(f"**Headings present:** "
                 f"{', '.join(stru.get('section_headings_present', [])) or 'none'}")
        st.write(f"**Headings missing:** "
                 f"{', '.join(stru.get('section_headings_missing', [])) or 'none'}")
        red_flags = stru.get("ats_red_flags", [])
        if red_flags:
            st.dataframe(red_flags, width="stretch")
        else:
            st.write("No ATS red flags detected. ✓")

    with st.expander(f"🎓 Background fit — {bg.get('background_fit_score', 0)}/100"):
        st.write(f"**Candidate background:** "
                 f"{bg.get('candidate_background_summary', '')}")
        st.write(f"**Role expects:** {bg.get('role_requirements_summary', '')}")
        st.write(f"**Commentary:** {bg.get('alignment_commentary', '')}")

    st.divider()
    md_report = "\n".join(_build_lines(report))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Markdown report", md_report,
                       file_name=f"match_report_{ts}.md")
    d2.download_button("⬇️ JSON report", json.dumps(report, indent=2),
                       file_name=f"match_report_{ts}.json")
