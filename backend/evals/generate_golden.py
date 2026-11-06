import json
import random
import re
from litellm import completion

from app.database import SessionLocal
from app.models import Chunk, IngestedItem

# Use a different model from the one that answers questions in the app.
MODEL = "ollama_chat/qwen2.5:7b"
N = 60
OUT = "evals/golden_candidates.jsonl"

PROMPT = """You write test questions for a personal notes search system.
Read the PASSAGE and write ONE question that the passage answers.
Rules:
- Do not copy long phrases from the passage into the question. Use different wording where you can.
- reference_answer: 1 to 3 sentences in your own words, supported only by the passage.
- evidence: one exact quote copied from the passage, 8 to 40 words, that contains the answer.
Reply with JSON only: {{"question": "...", "reference_answer": "...", "evidence": "..."}}

PASSAGE:
{passage}"""


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def parse_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def main() -> None:
    db = SessionLocal()
    chunks = db.query(Chunk).all()
    titles = {i.id: i.title for i in db.query(IngestedItem).all()} #this goes over all ingested items that is documents urls
    random.seed(42)
    sample = random.sample(chunks, min(N, len(chunks)))

    kept = 0
    with open(OUT, "w") as f:
        for c in sample:
            try:
                resp = completion(
                    model=MODEL,
                    api_base="http://localhost:11434",
                    max_tokens=500,
                    messages=[{"role": "user", "content": PROMPT.format(passage=c.text)}], #here we are passing the chunk to the model to geenrate question
                )
            except Exception as exc:
                print(f"skipping chunk {c.id}: {exc}")
                continue
            rec = parse_json(resp.choices[0].message.content)
            if not rec or not all(k in rec for k in ("question", "reference_answer", "evidence")): #to make sure the response contains questions
                continue
            evidence = rec["evidence"]
            if not 8 <= len(evidence.split()) <= 40 or norm(evidence) not in norm(c.text):
                continue  # not a verbatim quote of the chunk: drop it
            out = {
                "id": f"q{kept + 1:03d}",
                "question": rec["question"],
                "reference_answer": rec["reference_answer"],
                "evidence": [evidence],
                "source_item_id": c.ingested_item_id,
                "source_title": titles.get(c.ingested_item_id),
                "type": "factual",
                "origin": "synthetic",
                "split": "dev",
                "review": "pending",
            }
            f.write(json.dumps(out) + "\n")
            kept += 1
    print(f"kept {kept} of {len(sample)} candidates")


if __name__ == "__main__":
    main()