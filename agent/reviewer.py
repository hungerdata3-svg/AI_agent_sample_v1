"""Combine the deterministic score (0-90) with Gemini's judgment (0-10).

Model failover: models are tried in order. If one is busy (503) or rate
limited (429), it is retried once, then the next model in MODELS is used.
"""
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from agent.prompts import REVIEW_PROMPT

load_dotenv()

# Tried in order. The first one that answers wins.
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]
RETRIES_PER_MODEL = 2   # attempts per model before switching
RETRYABLE = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")

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


def ask_gemini(prompt: str) -> tuple[str, str]:
    """Return (reply_text, model_name) from the first model that responds."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY not found. Check your .env file.")
    client = genai.Client(api_key=key)

    errors = []
    for model in MODELS:
        for attempt in range(1, RETRIES_PER_MODEL + 1):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text, model
            except Exception as e:
                msg = str(e)
                if not any(code in msg for code in RETRYABLE):
                    # Not a busy/quota error (e.g. 404 model removed): switch models now
                    errors.append(f"{model}: {msg[:120]}")
                    break
                errors.append(f"{model} attempt {attempt}: busy")
                if attempt < RETRIES_PER_MODEL:
                    time.sleep(2 ** attempt)
        print(f"-> {model} unavailable, switching to next model")

    raise RuntimeError("All Gemini models failed:\n  " + "\n  ".join(errors))


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
    reply_text, model_used = ask_gemini(build_prompt(code_text, spec_text, deterministic))
    reply = parse_reply(reply_text)

    total = round(deterministic["deterministic_total"] + reply["judgment"], 1)
    verdict, reason = final_verdict(total, deterministic)
    return {
        "total": total,
        "verdict": verdict,
        "verdict_reason": reason,
        "judgment": reply["judgment"],
        "model_verdict": reply["model_verdict"],
        "summary": reply["summary"],
        "model_used": model_used,
    }
