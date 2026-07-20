"""
analyzer.py — Stages 2–4: eight functions that each wrap exactly one LLM
call, plus one pure-Python scoring function (no LLM).

Temperatures follow the study material §6.4: 0.0 for extraction,
0.2 for evaluation, 0.3 for the narrative summary.
"""

import json

from llm import ask_json, ask_text
from prompts import (
    RESUME_PROFILE_PROMPT,
    JD_PROFILE_PROMPT,
    KEYWORD_MATCH_PROMPT,
    BULLET_QUALITY_PROMPT,
    JARGON_AUDIT_PROMPT,
    STRUCTURE_AUDIT_PROMPT,
    BACKGROUND_FIT_PROMPT,
    OVERALL_SUMMARY_PROMPT,
)

# Weighted aggregation (study material §7.2): weights sum to 1.0.
SCORE_WEIGHTS = {
    ("keyword_match", "keyword_match_score"): 0.40,
    ("bullets", "bullet_quality_avg"): 0.25,
    ("structure", "structure_score"): 0.15,
    ("jargon", "jargon_score"): 0.10,
    ("background_fit", "background_fit_score"): 0.10,
}


def _profiles_msg(resume_profile: dict, jd_profile: dict) -> str:
    return (
        f"RÉSUMÉ PROFILE:\n{json.dumps(resume_profile, indent=2)}\n\n"
        f"JD PROFILE:\n{json.dumps(jd_profile, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Extraction (temperature 0.0)
# ---------------------------------------------------------------------------

def extract_resume_profile(resume_text: str) -> dict:
    """One LLM call: résumé text → structured candidate profile."""
    return ask_json(
        RESUME_PROFILE_PROMPT,
        f"RÉSUMÉ TEXT:\n\n{resume_text}",
        temperature=0.0,
        max_tokens=2000,
    )


def extract_jd_profile(jd_text: str) -> dict:
    """One LLM call: job description text → structured role profile."""
    return ask_json(
        JD_PROFILE_PROMPT,
        f"JOB DESCRIPTION TEXT:\n\n{jd_text}",
        temperature=0.0,
        max_tokens=1500,
    )


# ---------------------------------------------------------------------------
# Evaluation (temperature 0.2)
# ---------------------------------------------------------------------------

def analyse_keyword_match(resume_profile: dict, jd_profile: dict) -> dict:
    """One LLM call: which JD keywords are present/missing in the résumé."""
    return ask_json(
        KEYWORD_MATCH_PROMPT,
        _profiles_msg(resume_profile, jd_profile),
        temperature=0.2,
        max_tokens=3000,
    )


def analyse_bullets(resume_profile: dict) -> dict:
    """One LLM call: audit each bullet on Action → Technology → Impact."""
    return ask_json(
        BULLET_QUALITY_PROMPT,
        f"RÉSUMÉ PROFILE:\n{json.dumps(resume_profile, indent=2)}",
        temperature=0.2,
        max_tokens=3000,
    )


def analyse_jargon(resume_profile: dict, jd_profile: dict) -> dict:
    """One LLM call: flag résumé/JD terminology mismatches."""
    return ask_json(
        JARGON_AUDIT_PROMPT,
        _profiles_msg(resume_profile, jd_profile),
        temperature=0.2,
        max_tokens=1500,
    )


def analyse_structure(resume_text: str) -> dict:
    """One LLM call: ATS-parseability audit of the raw résumé text."""
    return ask_json(
        STRUCTURE_AUDIT_PROMPT,
        f"RAW RÉSUMÉ TEXT (as extracted from the PDF):\n\n{resume_text}",
        temperature=0.2,
        max_tokens=1500,
    )


def analyse_background_fit(resume_profile: dict, jd_profile: dict) -> dict:
    """One LLM call: education/experience alignment with the role."""
    return ask_json(
        BACKGROUND_FIT_PROMPT,
        _profiles_msg(resume_profile, jd_profile),
        temperature=0.2,
        max_tokens=1000,
    )


# ---------------------------------------------------------------------------
# Synthesis (temperature 0.3, plain text)
# ---------------------------------------------------------------------------

def summarise_overall(report: dict) -> str:
    """One LLM call: 3-bullet executive summary of the full report."""
    # Trim the report to what the summary needs; keeps the call cheap.
    lite = {
        "overall_score": report.get("overall_score"),
        "passes_ats_threshold": report.get("passes_ats_threshold"),
        "keyword_match": {
            "keyword_match_score": report.get("keyword_match", {}).get("keyword_match_score"),
            "present_count": len(report.get("keyword_match", {}).get("present", [])),
            "missing": report.get("keyword_match", {}).get("missing", [])[:8],
        },
        "bullet_quality_avg": report.get("bullets", {}).get("bullet_quality_avg"),
        "jargon": report.get("jargon", {}),
        "structure_score": report.get("structure", {}).get("structure_score"),
        "background_fit": report.get("background_fit", {}),
    }
    return ask_text(
        OVERALL_SUMMARY_PROMPT,
        f"SCREENING REPORT:\n{json.dumps(lite, indent=2)}",
        temperature=0.3,
    ).strip()


# ---------------------------------------------------------------------------
# Scoring (pure Python — no LLM)
# ---------------------------------------------------------------------------

def compute_overall_score(report: dict) -> int:
    """Weighted composite: S = Σ wᵢ·sᵢ (§7.2), returned as int 0–100."""
    total = 0.0
    for (section, field), weight in SCORE_WEIGHTS.items():
        try:
            score = float(report.get(section, {}).get(field, 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        total += weight * score
    return int(round(total))


if __name__ == "__main__":
    # ponytail: smallest self-check — scoring math only, no LLM calls.
    fake = {
        "keyword_match": {"keyword_match_score": 80},
        "bullets": {"bullet_quality_avg": 65},
        "structure": {"structure_score": 70},
        "jargon": {"jargon_score": 90},
        "background_fit": {"background_fit_score": 80},
    }
    # 0.4*80 + 0.25*65 + 0.15*70 + 0.1*90 + 0.1*80 = 75.75 → 76
    assert compute_overall_score(fake) == 76, compute_overall_score(fake)
    assert compute_overall_score({}) == 0
    assert compute_overall_score({"bullets": {"bullet_quality_avg": "60"}}) == 15
    print("compute_overall_score self-check OK")
