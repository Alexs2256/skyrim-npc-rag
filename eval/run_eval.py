"""
Run: python -m eval.run_eval   (from project root)

Two grading layers:
1. Keyword grader (kept, cheap, instant) - same as before.
2. LLM-as-judge faithfulness grader - checks whether the response's claims
   are actually supported by the RETRIEVED CONTEXT, not just whether
   keywords appear. This catches real hallucination even when a response
   sounds plausible enough to pass a keyword check.

STATUS: context plumbing confirmed working (retrieved_context is populated
in results.csv, and the judge visibly reasons over real chunk text). The
two remaining issues, both addressed in this revision:

1. JUDGE_PROMPT was too literal — it was flagging in-character flavor text
   ("he works tirelessly", "a great hall") as "unsupported claims" even
   when they're harmless paraphrase/atmosphere consistent with the source,
   not fabricated facts. Rewritten below to only penalize claims that
   introduce or contradict specific facts (names, numbers, places, events,
   relationships) not present in or implied by the source.

2. Free-tier quota on gemini-2.5-flash (JUDGE_MODEL) is capped at 20
   requests/day. Runs longer than ~20 lore/boundary questions will start
   hitting 429 RESOURCE_EXHAUSTED partway through, turning every remaining
   row into JUDGE_ERROR. Added a short retry-with-backoff using the
   server-provided retryDelay so transient rate limiting doesn't kill the
   whole run — but if you're on a small daily quota, you may still need to
   run this in smaller batches across multiple days, or point JUDGE_MODEL
   at a model with separate/higher quota.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import time
import re
import uuid
import csv
import json
import os
from pathlib import Path

from app.agent import app as chatbot_app
from eval.eval_dataset import EVAL_QUESTIONS
from google import genai
from google.genai.errors import ClientError


JUDGE_MODEL = "gemini-3.1-flash-lite"  # cheap/fast - adjust to whatever's in your fallback chain

gemini_key = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=gemini_key)

# Confirmed correct: matches the "chunk_text" field agent.py's lore_node
# writes back into state.
CHUNK_TEXT = "chunk_text"

OUT_PATH = Path(__file__).resolve().parent / "results.csv"

JUDGE_PROMPT = """You are grading a RAG chatbot response for faithfulness to its source material.

The chatbot plays an in-character NPC (Lydia, a Skyrim companion). Its job is to answer using
retrieved lore AND phrase that answer naturally in character. Natural phrasing is expected and
should NOT be penalized.

SOURCE TEXT (retrieved context the model had access to):
{context}

QUESTION ASKED:
{question}

MODEL'S RESPONSE:
{response}

Task: Determine whether the response is FAITHFUL to the source text.

Do NOT count these as unsupported claims — they are expected and acceptable:
- Paraphrasing, rewording, or summarizing something the source already says
  (e.g. source says "a hall" and response says "a great hall" — this is fine).
- In-character flavor, tone, opinions, or asides consistent with the source
  (e.g. Lydia expressing loyalty, caution, or dry wit).
- Reasonable, low-stakes scene-setting or filler that doesn't assert a new
  specific fact (e.g. "he works tirelessly", "these uncertain times").
- Reasonable inference that a careful reader would draw from the source,
  as long as it doesn't introduce a NEW specific, checkable fact.

DO count these as unsupported claims (real hallucination):
- A specific fact — a name, number, date, location, relationship, or event —
  that does not appear in and is not directly implied by the source text.
- A claim that contradicts the source text.
- Answering confidently with specific facts when the source text is empty
  or irrelevant to the question.

Respond ONLY with valid JSON, no markdown fences, no preamble, in this exact format:
{{"faithful": true or false, "unsupported_claims": ["list", "of", "specific", "fabricated", "facts", "only"], "reasoning": "one sentence"}}

If the source text is empty/irrelevant and the response honestly says it doesn't know, that is FAITHFUL (correct refusal).
If the source text is empty/irrelevant and the response confidently states specific facts anyway, that is NOT faithful (hallucination).
"""


def keyword_grade(question: dict, response: str):
    """Original substring grader. Kept as a cheap first-pass signal."""
    expected = question.get("expect_contains", [])
    if not expected:
        return None
    response_lower = response.lower()
    if question["category"] == "trap":
        return any(phrase.lower() in response_lower for phrase in expected)
    else:
        return all(phrase.lower() in response_lower for phrase in expected)


def _extract_retry_delay(err: Exception, default: float = 20.0) -> float:
    """Pull the server-suggested retryDelay (e.g. '23s') out of a 429 error message."""
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"](\d+(?:\.\d+)?)s", str(err))
    if match:
        return float(match.group(1)) + 1  # small buffer
    return default


def judge_faithfulness(question_text: str, response: str, context: str, max_retries: int = 2):
    """LLM-as-judge: does the response only claim things the retrieved context supports?"""
    prompt = JUDGE_PROMPT.format(
        context=context if context else "(no context was retrieved)",
        question=question_text,
        response=response,
    )
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = client.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
            )
            raw = result.text.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json", "", 1).strip()
            parsed = json.loads(raw)
            return parsed.get("faithful"), parsed.get("unsupported_claims", []), parsed.get("reasoning", "")
        except ClientError as e:
            last_error = e
            if getattr(e, "code", None) == 429 and attempt < max_retries:
                wait = _extract_retry_delay(e)
                print(f"  judge quota hit, waiting {wait:.1f}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            return None, [], f"JUDGE_ERROR: {e}"
        except Exception as e:
            return None, [], f"JUDGE_ERROR: {e}"
    return None, [], f"JUDGE_ERROR: {last_error}"


def run():
    results = []
    session_id = str(uuid.uuid4())

    for q in EVAL_QUESTIONS:
        start = time.perf_counter()
        try:
            output = chatbot_app.invoke({
                "prompt": q["question"],
                "session_id": session_id,
                "history": [],
                "chunk_text": ""
            })

            response = output.get("response", "")
            route = output.get("route", "unknown")
            retrieved = output.get(CHUNK_TEXT, "")

            if isinstance(retrieved, list):
                retrieved = "\n---\n".join(str(chunk) for chunk in retrieved)
            error = ""
        except Exception as e:
            response, route, retrieved, error = "", "ERROR", "", str(e)
        latency = round(time.perf_counter() - start, 2)

        kw_passed = keyword_grade(q, response)
        faithful, unsupported, reasoning = judge_faithfulness(q["question"], response, retrieved)

        results.append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "route": route,
            "response": response,
            "retrieved_context": retrieved[:500],  # truncate for csv readability
            "latency_s": latency,
            "keyword_passed": kw_passed,
            "faithful": faithful,
            "unsupported_claims": "; ".join(unsupported) if unsupported else "",
            "judge_reasoning": reasoning,
            "error": error,
        })

        status = "FAITHFUL" if faithful else ("JUDGE_ERR" if faithful is None else "HALLUCINATION")
        print(f"[{status}] {q['id']} ({q['category']}, {latency}s, route={route}, kw={kw_passed})")

    write_csv(results)
    print_summary(results)


def write_csv(results):
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults written to {OUT_PATH}")


def print_summary(results):
    print("\n=== SUMMARY BY CATEGORY (faithfulness = LLM-judged) ===")
    categories = sorted(set(r["category"] for r in results))
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        judged = [r for r in cat_results if r["faithful"] is not None]
        faithful_count = sum(1 for r in judged if r["faithful"])
        avg_latency = sum(r["latency_s"] for r in cat_results) / len(cat_results)
        rate = f"{faithful_count}/{len(judged)}" if judged else "n/a"
        print(f"{cat:10s} faithful_rate={rate:>8s}  avg_latency={avg_latency:.2f}s")

    print("\n--- Reminder: pick a random 15-20% sample of results.csv and manually ---")
    print("--- verify the judge's calls agree with your own reading. Judge models ---")
    print("--- can be fooled too - this sample check is what makes the number defensible. ---")


if __name__ == "__main__":
    run()