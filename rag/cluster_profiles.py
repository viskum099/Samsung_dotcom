"""Cluster indexed review evidence and export evidence-linked profile summaries."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sklearn.cluster import KMeans

from review_rag import (
    ANCHORS,
    DEFAULT_DB,
    DEFAULT_MODEL,
    PROJECT_ROOT,
    clean_text,
    get_collection,
    load_model,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "clustered_user_profiles.csv"

FEATURE_RULES = {
    "Battery endurance (candidate inferred from battery signals)": r"battery|drain|endurance",
    "Faster or more predictable charging (candidate inferred from charging signals)": r"charg(?:e|ing)",
    "Consistent camera results (candidate inferred from camera signals)": r"camera|photo|image|zoom",
    "Thermal control (candidate inferred from heat signals)": r"heat|warm|thermal|overheat",
    "Long software support (candidate inferred from longevity signals)": r"support|longevity|years of|upgrade",
    "Clear value at the target price (candidate inferred from price signals)": r"price|value|budget|cost|₹",
    "Reliable display experience (candidate inferred from display signals)": r"display|screen",
    "Reliable Bluetooth calling (candidate inferred from connectivity signals)": r"bluetooth|disconnect",
    "Clean, responsive software (candidate inferred from software/UI signals)": r"one ui|clean ui|software|smooth|lag|stutter",
}

PROFILE_RULES = {
    "Battery and charging focused": r"battery|drain|charge|endurance",
    "Camera and photography focused": r"camera|photo|image|zoom",
    "Value and price conscious": r"price|value|budget|cost|₹|overpriced",
    "Long-term ownership focused": r"support|longevity|years of|upgrade",
    "Performance and thermal focused": r"heat|warm|thermal|overheat|performance|stutter|lag",
    "Display and everyday media focused": r"display|screen|streaming|youtube|media",
}

EMOTION_RULES = {
    "Regret": r"regret|regretting|miscalculation",
    "Disappointment": r"dissatisf|unsatisf|disappoint|fell short",
    "Concern or uncertainty": r"concern|worried|worry|skeptical|uncertain|fear",
    "Frustration": r"frustrat|annoy|issue|problem|disconnect|not working",
}

OUTPUT_FIELDS = [
    "cluster_id",
    "profile_label",
    "source_chunk_count",
    "pain_points",
    "desired_features_candidate_inferred",
    "emotional_triggers_explicit_cues_only",
    "evidence_ids",
    "retrieval_anchors",
    "source_platforms",
    "source_urls",
    "cluster_confidence_and_limitations",
]


def joined_evidence(row: dict[str, Any], document: str) -> str:
    parts = [document]
    for field in ("use_case_signal", "pain_point_signal", "price_or_willingness_to_pay_signal", "reviewer_notes"):
        value = clean_text(row.get(field))
        if value:
            parts.append(value)
    return " ".join(parts).lower()


def distinct_values(rows: list[dict[str, Any]], field: str) -> list[str]:
    values = []
    seen = set()
    for row in rows:
        value = clean_text(row.get(field))
        if value and value.lower() not in seen:
            values.append(value)
            seen.add(value.lower())
    return values


def matching_labels(text: str, rules: dict[str, str]) -> list[str]:
    return [label for label, pattern in rules.items() if re.search(pattern, text, flags=re.IGNORECASE)]


def label_cluster(text: str) -> str:
    labels = matching_labels(text, PROFILE_RULES)
    if not labels:
        return "Mixed everyday-use signals"
    return " / ".join(labels[:2])


def summarize_cluster(cluster_id: int, members: list[dict[str, Any]], minimum_size: int) -> dict[str, str]:
    texts = [joined_evidence(member["metadata"], member["document"]) for member in members]
    combined = " ".join(texts)
    pain_points = distinct_values([member["metadata"] for member in members], "pain_point_signal")
    features = matching_labels(combined, FEATURE_RULES)
    emotions = matching_labels(combined, EMOTION_RULES)
    if not emotions:
        emotions = ["No explicit emotional cue found in the evidence summaries"]

    evidence_ids = distinct_values([member["metadata"] for member in members], "evidence_id")
    anchors = []
    for member in members:
        anchors.extend(clean_text(member["metadata"].get("retrieved_by_anchors")).split(" | "))
    anchors = list(dict.fromkeys(anchor for anchor in anchors if anchor))
    platforms = distinct_values([member["metadata"] for member in members], "platform")
    urls = distinct_values([member["metadata"] for member in members], "source_url")
    if len(members) < minimum_size:
        limitation = f"Low confidence: only {len(members)} source chunk(s) in this cluster. Validate with more customer evidence."
    else:
        limitation = "Exploratory cluster only; sample is small and source summaries may be paraphrased. Validate before treating as a customer segment."
    if not pain_points:
        pain_points = ["No explicit pain point field was available in these chunks."]
    if not features:
        features = ["No desired feature candidate matched the transparent keyword rules."]

    return {
        "cluster_id": str(cluster_id),
        "profile_label": label_cluster(combined),
        "source_chunk_count": str(len(members)),
        "pain_points": " | ".join(pain_points),
        "desired_features_candidate_inferred": " | ".join(features),
        "emotional_triggers_explicit_cues_only": " | ".join(emotions),
        "evidence_ids": " | ".join(evidence_ids),
        "retrieval_anchors": " | ".join(anchors),
        "source_platforms": " | ".join(platforms),
        "source_urls": " | ".join(urls),
        "cluster_confidence_and_limitations": limitation,
    }


def cluster_index(
    db_path: Path,
    model_name: str,
    dataset: str | None,
    cluster_count: int,
    top_k_per_anchor: int,
    output_path: Path,
) -> int:
    collection = get_collection(db_path)
    where = {"dataset": dataset} if dataset else None
    collection_rows = collection.get(where=where, include=["metadatas"])
    indexed_count = len(collection_rows.get("ids") or [])
    if not indexed_count:
        raise ValueError("No indexed evidence was found. Build the vector index first.")
    if top_k_per_anchor < 1:
        raise ValueError("Top-k per anchor must be at least 1.")

    model = load_model(model_name)
    selected: dict[str, dict[str, Any]] = {}
    for anchor_query in ANCHORS.values():
        query_vector = model.encode_query(anchor_query, normalize_embeddings=True)
        hits = collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=min(top_k_per_anchor, indexed_count),
            where=where,
            include=["documents", "metadatas"],
        )
        for row_id, document, metadata in zip(hits["ids"][0], hits["documents"][0], hits["metadatas"][0]):
            item = selected.setdefault(row_id, {"document": document, "metadata": dict(metadata or {}), "anchors": []})
            item["anchors"].append(anchor_query)

    rows = list(selected.values())
    documents = [row["document"] for row in rows]
    if cluster_count < 1 or cluster_count > len(documents):
        raise ValueError(f"Cluster count must be between 1 and the number of unique retrieved chunks ({len(documents)}).")
    for row in rows:
        row["metadata"]["retrieved_by_anchors"] = " | ".join(dict.fromkeys(row["anchors"]))

    vectors = model.encode_document(documents, normalize_embeddings=True, show_progress_bar=True)
    labels = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit_predict(vectors)
    groups: dict[int, list[dict[str, Any]]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(int(label), []).append(rows[index])

    summaries = [summarize_cluster(label, members, minimum_size=2) for label, members in sorted(groups.items())]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(summaries)
    return len(summaries)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cluster Chroma-indexed review chunks into evidence-linked user profile hypotheses.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Chroma database directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Sentence Transformers model used when indexing.")
    parser.add_argument("--dataset", help="Limit to a source CSV basename, e.g. india_mobile_research_findings.csv.")
    parser.add_argument("--clusters", type=int, default=3, help="Requested KMeans cluster count (default: 3).")
    parser.add_argument("--top-k-per-anchor", type=int, default=5, help="Retrieved chunks to collect for each of the four semantic anchors (default: 5).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Profile CSV output path.")
    args = parser.parse_args()
    try:
        count = cluster_index(args.db.resolve(), args.model, args.dataset, args.clusters, args.top_k_per_anchor, args.out.resolve())
        print(f"Wrote {count} exploratory profile clusters to {args.out.resolve()}")
        return 0
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
