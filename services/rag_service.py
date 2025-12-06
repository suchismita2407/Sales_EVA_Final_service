import json
from typing import List, Dict, Any
from db import query_one, execute
from services.llm_service import get_llm, get_embeddings
from vector_store import offerings_col, opportunities_col


def embed_text(text: str) -> List[float]:
    emb = get_embeddings()
    return emb.embed_query(text)


def index_offering(off):
    text = f"{off['name']} {off.get('industry','')} {off.get('description','')}"
    vec = embed_text(text)

    offerings_col.add(
        ids=[f"off-{off['id']}"],
        embeddings=[vec],
        documents=[text],
        metadatas=[{"offering_id": off["id"]}]
    )


def index_opportunity(opp):
    text = f"{opp['name']} {opp.get('industry','')} {opp.get('description','')} {opp.get('requirements','')}"
    vec = embed_text(text)

    opportunities_col.add(
        ids=[f"opp-{opp['id']}"],
        embeddings=[vec],
        documents=[text],
        metadatas=[{"opportunity_id": opp["id"]}]
    )


def match_solutions_for_opportunity(opp_id: int):
    opp = query_one("SELECT * FROM opportunities WHERE id=?", (opp_id,))
    if not opp:
        return []

    query_text = f"{opp['industry']} {opp['description']} {opp['requirements']}"
    emb = embed_text(query_text)

    res = offerings_col.query(query_embeddings=[emb], n_results=5)

    candidates = []
    for idx, meta in enumerate(res["metadatas"][0]):
        candidates.append({
            "offering_id": meta["offering_id"],
            "fit_score": float(res["distances"][0][idx])  # similarity score
        })

    llm = get_llm()

    prompt = f"""
You MUST return JSON formatted list like this:
[
  {{
    "offering_id": 12,
    "fit_score": 0-1 float,
    "explanation": "reason"
  }}
]

Rank these candidates for the opportunity:
{json.dumps(candidates)}

Opportunity Details:
{opp['description']}
"""

    reply = llm.invoke(prompt)
    raw = reply.content.strip()

    # Try direct JSON parse
    try:
        ranked = json.loads(raw)
    except:
        # fallback
        ranked = [{"offering_id": c["offering_id"],
                   "fit_score": c["fit_score"],
                   "explanation": "fallback reasoning due to parsing failure"} for c in candidates]

    enriched = []
    for item in ranked:
        off_row = query_one("SELECT name FROM offerings WHERE id=?", (item["offering_id"],))
        percentage_score = int(item["fit_score"] * 100)

        enriched.append({
            "offering_id": item["offering_id"],
            "offering_name": off_row["name"] if off_row else "Unknown",
            "score": percentage_score,
            "reason": item.get("explanation", "")
        })

        execute(
            "INSERT INTO recommendations (opportunity_id, offering_id, fit_score, explanation) VALUES (?,?,?,?)",
            (opp_id, item["offering_id"], item["fit_score"], item["explanation"])
        )

    return enriched


def analyze_gaps(opp_id: int, offering_id: int):
    opp = query_one("SELECT * FROM opportunities WHERE id=?", (opp_id,))
    off = query_one("SELECT * FROM offerings WHERE id=?", (offering_id,))

    if not opp:
        return {"covered": [], "partial": [], "missing": ["Opportunity not found"]}

    if not off:
        return {"covered": [], "partial": [], "missing": ["Offering not found"]}

    llm = get_llm()

    prompt = f"""
You MUST respond ONLY using valid JSON. Do not add ```json or comments.

Use exact structure:

{{
  "covered": ["..."],
  "partial": ["..."],
  "missing": ["..."]
}}

Opportunity:
Description: {opp.get('description','')}
Requirements: {opp.get('requirements','')}

Offering:
Description: {off.get('description','')}
"""

    reply = llm.invoke(prompt)
    raw = reply.content.strip()

    # Clean formatting errors from LLM
    raw = raw.replace("```json", "").replace("```", "").strip()

    import re, json

    # Extract JSON reliably from anywhere
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            result = json.loads(match.group(0))
        else:
            raise ValueError("JSON not found")
    except:
        result = {
            "covered": [],
            "partial": [],
            "missing": ["LLM parsing failed – fallback applied"]
        }

    # Guarantee keys exist
    for key in ["covered", "partial", "missing"]:
        if key not in result:
            result[key] = []

    return result
