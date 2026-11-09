"""Local vector indexing and semantic retrieval for cleaned Samsung review evidence."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "india_mobile_research_findings.csv"
DEFAULT_DB = Path(__file__).resolve().parent / "chroma_db"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "samsung_mobile_review_evidence"

ANCHORS = {
    "battery": "battery drain issues",
    "camera": "camera comparison",
    "price": "price is too high",
    "ios": "switch from iOS",
}

TEXT_FIELDS = (
    ("short_excerpt_or_paraphrase", "Review evidence"),
    ("use_case_signal", "Use case"),
    ("pain_point_signal", "Pain point"),
    ("price_or_willingness_to_pay_signal", "Price signal"),
    ("trend_or_theme_code", "Theme"),
)

METADATA_FIELDS = (
    "evidence_id",
    "platform",
    "content_type",
    "product_model",
    "market_country",
    "source_url",
    "use_case_signal",
    "pain_point_signal",
    "price_or_willingness_to_pay_signal",
    "published_date",
    "collected_date",
    "star_rating_if_available",
    "verified_purchase_if_available",
    "sentiment",
    "engagement_count_if_visible",
    "source_context_or_limitations",
    "reviewer_notes",
)


def clean_text(value: str | None) -> str:
    """Normalize whitespace and remove markup before embedding."""
    text = value or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_document(row: dict[str, str]) -> str:
    parts = []
    for field, label in TEXT_FIELDS:
        value = clean_text(row.get(field))
        if value:
            parts.append(f"{label}: {value}")
    model = clean_text(row.get("product_model"))
    platform = clean_text(row.get("platform"))
    market = clean_text(row.get("market_country"))
    context = " | ".join(item for item in (model, platform, market) if item)
    if context:
        parts.insert(0, f"Product/source context: {context}")
    return "\n".join(parts)


def read_evidence(csv_path: Path, include_editorial: bool) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if clean_text(row.get("trend_or_theme_code")).upper() == "SOURCE_COVERAGE_GAP":
                continue

            content_type = clean_text(row.get("content_type"))
            kind = content_type.lower()
            is_customer_evidence = (
                any(token in kind for token in ("owner discussion", "purchase advice", "verified-purchase review", "customer review", "customer comment"))
                or ("review" in kind and "video review" not in kind)
                or "comment" in kind
            )
            is_editorial = "video review" in content_type.lower()
            if not is_customer_evidence and not (include_editorial and is_editorial):
                continue

            document = build_document(row)
            if not document or not clean_text(row.get("source_url")):
                continue

            metadata: dict[str, Any] = {
                key: clean_text(row.get(key))
                for key in METADATA_FIELDS
                if clean_text(row.get(key))
            }
            metadata["dataset"] = csv_path.name
            evidence_id = clean_text(row.get("evidence_id")) or f"row-{len(records) + 1}"
            records.append({
                "id": f"{csv_path.name}:{evidence_id}",
                "document": document,
                "metadata": metadata,
            })
    return records


def get_collection(db_path: Path):
    client = chromadb.PersistentClient(path=str(db_path))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def index_csv(csv_path: Path, db_path: Path, model_name: str, include_editorial: bool) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"Evidence CSV not found: {csv_path}")
    records = read_evidence(csv_path, include_editorial)
    if not records:
        raise ValueError("No eligible review/comment records found in the CSV.")

    model = load_model(model_name)
    documents = [record["document"] for record in records]
    vectors = model.encode_document(documents, normalize_embeddings=True, show_progress_bar=True)

    collection = get_collection(db_path)
    # Rebuild this dataset slice so deleted or changed CSV rows do not remain stale.
    collection.delete(where={"dataset": csv_path.name})
    collection.upsert(
        ids=[record["id"] for record in records],
        documents=documents,
        metadatas=[record["metadata"] for record in records],
        embeddings=vectors.tolist(),
    )
    return len(records)


def retrieve(
    query: str,
    db_path: Path,
    model_name: str,
    top_k: int,
    dataset: str | None = None,
    model: SentenceTransformer | None = None,
) -> list[dict[str, Any]]:
    collection = get_collection(db_path)
    if collection.count() == 0:
        raise ValueError("The vector index is empty. Run the index command first.")
    model = model or load_model(model_name)
    query_vector = model.encode_query(query, normalize_embeddings=True)
    where = {"dataset": dataset} if dataset else None
    result = collection.query(
        query_embeddings=[query_vector.tolist()],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append({
            "similarity": round(1.0 - float(distance), 4),
            "document": doc,
            "metadata": metadata,
        })
    return hits


def render_hits(query: str, hits: list[dict[str, Any]], output_format: str) -> str:
    if output_format == "json":
        import json
        return json.dumps({"query": query, "results": hits}, ensure_ascii=False, indent=2)

    sections = [f"## Query: {query}"]
    if not hits:
        return "\n".join(sections + ["No matching evidence was retrieved."])
    for rank, hit in enumerate(hits, start=1):
        metadata = hit["metadata"]
        source = metadata.get("source_url", "Source URL unavailable")
        label = " | ".join(filter(None, [metadata.get("product_model"), metadata.get("platform"), metadata.get("published_date")]))
        sections.append(
            f"### {rank}. {label or metadata.get('evidence_id', 'Evidence')} (similarity {hit['similarity']})\n"
            f"{hit['document']}\n\n"
            f"Evidence ID: {metadata.get('evidence_id', 'unknown')}  \n"
            f"Source: {source}  \n"
            f"Limitations: {metadata.get('source_context_or_limitations', 'See source and collection notes.')}"
        )
    if output_format == "context":
        sections.append("\nUse only the cited evidence above. Treat each record as a source-level signal, not a population estimate. If evidence is missing or mixed, say so rather than filling the gap.")
    return "\n\n".join(sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Index and retrieve cleaned Samsung mobile review evidence with ChromaDB.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Local Chroma database directory (default: rag/chroma_db).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Sentence Transformers model (default: {DEFAULT_MODEL}).")
    commands = parser.add_subparsers(dest="command", required=True)

    index_parser = commands.add_parser("index", help="Embed and store eligible review/comment records from a CSV.")
    index_parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Input evidence CSV.")
    index_parser.add_argument("--include-editorial", action="store_true", help="Also index video-review summaries; excluded by default because they are not customer comments.")

    search_parser = commands.add_parser("search", help="Retrieve semantically similar evidence for a query.")
    search_parser.add_argument("query", nargs="?", help="Natural-language query. Omit with --anchors to run the four starter queries.")
    search_parser.add_argument("--top-k", type=int, default=5, help="Maximum results to return (default: 5).")
    search_parser.add_argument("--dataset", help="Limit retrieval to a CSV basename, such as india_mobile_research_findings.csv.")
    search_parser.add_argument("--format", choices=("markdown", "context", "json"), default="markdown", help="Output format. context emits source-grounded text for a later generation step.")
    search_parser.add_argument("--anchors", action="store_true", help="Run battery, camera, price, and iOS-switching queries.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "index":
            count = index_csv(args.csv.resolve(), args.db.resolve(), args.model, args.include_editorial)
            print(f"Indexed {count} evidence records in {args.db.resolve()}")
            return 0

        if args.top_k < 1:
            parser.error("--top-k must be at least 1")
        if args.anchors:
            model = load_model(args.model)
            for query in ANCHORS.values():
                print(render_hits(query, retrieve(query, args.db.resolve(), args.model, args.top_k, args.dataset, model), args.format))
                print()
            return 0
        if not args.query:
            parser.error("Provide a query string or use --anchors")
        hits = retrieve(args.query, args.db.resolve(), args.model, args.top_k, args.dataset)
        print(render_hits(args.query, hits, args.format))
        return 0
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
