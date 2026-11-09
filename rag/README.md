# Review Vector Search (RAG retrieval stage)

This folder adds a local vector retrieval stage over the cleaned evidence CSV. It uses a Sentence Transformers embedding model and a persistent ChromaDB collection. The index retains evidence IDs, product, platform, dates, market, source URL, and limitations as metadata.

## Setup

Use Python 3.10 or newer, then from the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r rag\requirements.txt
```

The first run downloads `sentence-transformers/all-MiniLM-L6-v2` from the model hub. The index and downloaded embedding model are stored locally by their respective libraries; no API key is needed. If model downloads are restricted, download/cache the model in an approved environment first.

## Build or refresh the vector index

```powershell
py rag\review_rag.py index
```

The default source is `india_mobile_research_findings.csv`; the persistent Chroma database is created at `rag\chroma_db`. Each source record is cleaned and embedded as one document. Coverage-gap rows and marketplace aggregate-only rows are excluded. Editorial video reviews are also excluded unless `--include-editorial` is passed because they are not customer review/comment evidence.

To index a different CSV with compatible evidence columns:

```powershell
py rag\review_rag.py index --csv path\to\your_reviews.csv
```

Re-indexing replaces that CSV's slice in the collection, so records removed from the CSV do not remain stale.

## Search the semantic anchors

Run all four supplied queries:

```powershell
py rag\review_rag.py search --anchors --top-k 5 --format context
```

Or ask one query:

```powershell
py rag\review_rag.py search "battery drain issues" --top-k 5
py rag\review_rag.py search "camera comparison" --top-k 5
py rag\review_rag.py search "price is too high" --top-k 5
py rag\review_rag.py search "switch from iOS" --top-k 5 --format json
```

`--format context` prints retrieved source excerpts and citations with a short grounding instruction. It is a retrieval result ready to pass to a future language-model generation step; this script does not call an LLM or fabricate an answer.

## Cluster retrieved evidence into profile hypotheses

After indexing, cluster the chunks and write one row per profile hypothesis:

```powershell
py rag\cluster_profiles.py --clusters 3
```

This retrieves up to five chunks for each of the four semantic anchors, deduplicates them, and writes `clustered_user_profiles.csv` in the project root. Use `--dataset india_mobile_research_findings.csv` to restrict retrieval to one source CSV. The embedding vectors determine the KMeans grouping. Pain points are taken from recorded evidence fields. Desired features are transparent keyword-based candidates and explicitly labeled as inferred. Emotional triggers are reported only when words in the collected evidence summary match the small cue list; no cue means the output says that none was explicit. Cluster names are descriptive labels, not validated personas. Choose a cluster count no larger than the unique retrieved chunks and treat small clusters as low confidence.

## Generate product-page copy drafts

After clustering, generate Markdown copy and an interactive HTML comparison page:

```powershell
py rag\copy_generator.py
```

The generator uses `clustered_user_profiles.csv` when available and otherwise falls back to `india_mobile_customer_profiles.csv`. It reads `india_mobile_trend_spec_hook_drafts.csv`, then writes `generated_product_page_copy.md` and `generated_product_page_copy.html` at the project root. The HTML table can be filtered by audience, trend category, claim status, or text. FAQ responses use only mapped specs and benefit notes; if a pain point has no relevant sourced spec, the draft explicitly says evidence is missing. Copy remains a draft regardless of output format.

## Retrieval behavior and limitations

- Documents are evidence summaries/paraphrases from the current CSV, not full review text. Retrieval quality is limited by the small, manually collected sample.
- Similarity scores rank candidate records; they are not probabilities, relevance guarantees, or sentiment scores.
- This is source-level evidence retrieval. Verify each source and its model/market/date before using it in a product page claim.
- The sample currently contains no indexed Instagram/Facebook comment text, no Amazon individual review text, and no YouTube comments. Those sources cannot be retrieved until suitable permitted review text is added to the CSV.
- Keep the local database private if future imports contain non-public or sensitive data. Do not store usernames or personal identifiers.
