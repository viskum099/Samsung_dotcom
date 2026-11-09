# Script and Page Guide

This project is a static product-marketing site and local research workspace. The browser pages do not require a server or build step. The optional Python tools under `rag/` support offline evidence retrieval and copy-draft generation.

## Browser pages

| File | Purpose |
|---|---|
| `index.html` | Main Galaxy product landing page: model selection, product story, comparison and FAQs. |
| `public/project-detail.html` | Separate product detail view; accepts `?product=galaxy-s26-ultra` or `?product=galaxy-a56-5g`. |
| `research.html` | Local customer-profile and trend-to-spec research workspace. |

## Browser scripts

| File | Used by | Purpose |
|---|---|---|
| `public/products.js` | Product landing and detail pages | Holds the static product records, specifications, audience messages, research summaries, FAQs and source notes for the two Galaxy models. |
| `public/promo.js` | Product landing and detail pages | Reads the product records and renders model selection, feature and audience tabs, FAQs, comparison table, sticky product label and responsive navigation. On the detail page, the selected model is encoded in the query string. |
| `app.js` | `research.html` | Loads and saves research records in browser local storage; renders profile and trend cards; handles form submission, deletion, CSV/JSON export, scroll shortcuts and clear-data confirmation. |

The product page stylesheet is `public/promo.css`; the research workspace stylesheet is `styles.css`. Both use local CSS and system fonts. The pages do not load remote fonts or product data.

## Optional Python research scripts

Run these commands from the repository root after installing `rag/requirements.txt` in a Python environment.

| File | Purpose | Typical command |
|---|---|---|
| `rag/review_rag.py` | Cleans eligible evidence rows from `india_mobile_research_findings.csv`, builds a local ChromaDB vector index, and retrieves source-linked matches for a query. Marketplace aggregates and coverage-gap rows are excluded; editorial video reviews are excluded unless explicitly enabled. | `py rag\review_rag.py index` then `py rag\review_rag.py search "battery drain issues"` |
| `rag/cluster_profiles.py` | Retrieves evidence around the built-in semantic anchors, groups the results with KMeans, and writes exploratory profile summaries to `clustered_user_profiles.csv`. Labels and inferred features are candidates, not validated customer segments. | `py rag\cluster_profiles.py --clusters 3` |
| `rag/copy_generator.py` | Reads profile and trend-mapping CSVs and generates evidence-linked product-page copy drafts in Markdown and a filterable HTML page. It prefers `clustered_user_profiles.csv` if present; otherwise it uses the supplied customer profile CSV. | `py rag\copy_generator.py` |

The Python scripts are optional and are not required to open the website. The RAG workflow creates its local vector database at `rag\chroma_db`; clustering and copy-generation commands create output files in the repository root. See `rag/README.md` for options, setup, and limitations.

## Research data and templates

- `india_mobile_research_findings.csv` contains the collected evidence summaries used by the research and optional RAG workflows.
- `india_mobile_customer_profiles.csv` contains early, low-confidence audience hypotheses.
- `india_mobile_trend_spec_hook_drafts.csv` contains sourced trend-to-specification mappings and draft hooks.
- `customer_profiles_template.csv`, `source_evidence_template.csv`, and `trend_mapping_template.csv` are blank data-entry templates.
- `research_notes.md` documents collection scope, limitations, and interpretation guidance.

All research records are directional and non-representative. Check evidence, current model-specific claims, regional terms, and approvals before publication.
