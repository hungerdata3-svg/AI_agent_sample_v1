"""Combine the deterministic score (0-90) with Gemini's judgment (0-10)."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from agent.prompts import REVIEW_PROMPT

load_dotenv()
MODEL = "gemini-3.8-flash"

# Checks that can corrupt data. A failure here caps the verdict at APPROVE WITH CHANGES.
CRITICAL_CHECKS = ("granularity", "no duplicate order_id", "clean + rejects equals input rows")


def build_prompt(code_text: str, spec_text: str, deterministic: dict) -> str:
    lines = []
    for name, area in deterministic["areas"].items():
        lines.append(f"{name}: {area['points']}/{area['max']}")
        for desc, ok in area["checks"]:
            lines.append(f"  [{'PASS' if ok else 'FAIL'}] {desc}")
    return (
        f"{REVIEW_PROMPT}\n\n"
        f"DESTINATION SPEC:\n{spec_text}\n\n"
        f"DETERMINISTIC CHECKS:\n" + "\n".join(lines) + "\n\n"
        f"CODE UNDER REVIEW:\n{code_text}\n"
    )


def ask_gemini(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY not found. Check your .env file.")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


def parse_reply(text: str) -> dict:
    score = re.search(r"JUDGMENT_SCORE:\s*(\d+)", text)
    verdict = re.search(r"VERDICT:\s*(APPROVE WITH CHANGES|APPROVE|REJECT)", text)
    summary = re.search(r"SUMMARY:\s*(.+)", text)
    return {
        "judgment": min(10, int(score.group(1))) if score else 0,
        "model_verdict": verdict.group(1) if verdict else "UNKNOWN",
        "summary": summary.group(1).strip() if summary else "",
        "raw": text,
    }


def final_verdict(total: float, deterministic: dict) -> tuple[str, str]:
    """Return (verdict, reason). Score bands first, then the critical-check cap."""
    if total >= 85:
        verdict = "APPROVE"
    elif total >= 60:
        verdict = "APPROVE WITH CHANGES"
    else:
        verdict = "REJECT"

    reason = "score band"
    failed_critical = [
        desc
        for area in deterministic["areas"].values()
        for desc, ok in area["checks"]
        if not ok and desc.startswith(CRITICAL_CHECKS)
    ]
    if failed_critical and verdict == "APPROVE":
        verdict = "APPROVE WITH CHANGES"
        reason = "capped: critical check failed: " + "; ".join(failed_critical)
    return verdict, reason


def review(code_path: str, deterministic: dict, spec_path: str = "specs/orders_target.yaml") -> dict:
    code_text = Path(code_path).read_text()
    spec_text = Path(spec_path).read_text()
    reply = parse_reply(ask_gemini(build_prompt(code_text, spec_text, deterministic)))

    total = round(deterministic["deterministic_total"] + reply["judgment"], 1)
    verdict, reason = final_verdict(total, deterministic)
    return {
        "total": total,
        "verdict": verdict,
        "verdict_reason": reason,
        "judgment": reply["judgment"],
        "model_verdict": reply["model_verdict"],
        "summary": reply["summary"],
    }
