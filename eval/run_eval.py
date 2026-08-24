"""
Run: python -m eval.run_eval   (from project root)

Two grading layers now:
1. Keyword grader (kept, cheap, instant) - same as before.
2. LLM-as-judge faithfulness grader (new) - checks whether the response's
   claims are actually supported by the RETRIEVED CONTEXT, not just whether
   keywords appear. This catches real hallucination even when a response
   sounds plausible enough to pass a keyword check.

*** ACTION NEEDED (2 things) BEFORE THIS RUNS CORRECTLY ***

1. RETRIEVED_CONTEXT_KEY below: your graph state needs to expose whatever
   your retriever fetched (the chunks behind "Raw rows returned: 2" in
   your logs) as a field in the dict `chatbot_app.invoke()` returns.
   Check retriever.py / gamestate.py / agent.py for whatever key name
   holds that list (e.g. "retrieved_docs", "context", "chunks"). Update
   RETRIEVED_CONTEXT_KEY to match. If it's not currently returned in state
   at all, add it there first - the judge is useless without it.

2. JUDGE_MODEL_SETUP: this uses the modern google-genai SDK directly with
   the client instance, since I don't know how your settings.py configures
   the client. If you already have a configured client/helper (e.g. a
   `generate()` function in agent.py), swap `judge_faithfulness()` below
   to call that instead of instantiating its own model connection.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import time
import uuid
import csv
import json
import os
from pathlib import Path

from app.agent import app as chatbot_app
from eval.eval_dataset import EVAL_QUESTIONS
from google import genai


# --- ACTION NEEDED: point this at wherever your API key actually lives ---
# Make sure the GEMINI_API_KEY environment variable is set in your system.
JUDGE_MODEL = "gemini-2.5-flash"  # cheap/fast - adjust to whatever's in your fallback chain

gemini_key = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=gemini_key)

# --- ACTION NEEDED: match this to your actual state's retrieved-context key ---
CHUNK_TEXT = "chunk_text"

OUT_PATH = Path(__file__).resolve().parent / "results.csv"

JUDGE_PROMPT = """You are grading a RAG chatbot response for faithfulness to its source material.

SOURCE TEXT (retrieved context the model had access to):
{context}

QUESTION ASKED:
{question}

MODEL'S RESPONSE:
{response}

Task: Determine if every factual claim in the response is supported by the source text above.
Respond ONLY with valid JSON, no markdown fences, no preamble, in this exact format:
{{"faithful": true or false, "unsupported_claims": ["list", "of", "claims", "not", "in", "source"], "reasoning": "one sentence"}}

If the source text is empty and the response claims to not know the answer, that is FAITHFUL (correct refusal).
If the source text is empty and the response confidently answers anyway, that is NOT faithful (hallucination).
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


def judge_faithfulness(question_text: str, response: str, context: str):
    """LLM-as-judge: does the response only claim things the retrieved context supports?"""
    prompt = JUDGE_PROMPT.format(
        context=context if context else "(no context was retrieved)",
        question=question_text,
        response=response,
    )
    try:
        # Use the modern client model call structure
        result = client.models.generate_content(
            model=JUDGE_MODEL,
            contents=prompt,
        )
        raw = result.text.strip()
        # strip accidental markdown fences if the model adds them anyway
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()
        parsed = json.loads(raw)
        return parsed.get("faithful"), parsed.get("unsupported_claims", []), parsed.get("reasoning", "")
    except Exception as e:
        return None, [], f"JUDGE_ERROR: {e}"
    
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

            # ACTION NEEDED: confirm this key exists - see module docstring
            retrieved = output.get(CHUNK_TEXT, "")
            print("Retrieved_text: ", retrieved)
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
