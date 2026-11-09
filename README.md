# Samsung Dotcom Galaxy Mobile Product Page

A static, responsive course prototype for Galaxy S26 Ultra and Galaxy A56 5G. It preserves the earlier evidence-led product-page direction while using a restrained navy, blue, white and cool-grey visual system. The UI is an original layout; it does not reproduce Samsung’s store design or send visitors to Samsung.com.

## Open the pages

- Open `index.html` (or `public/index.html`) in a modern browser for the promotional landing page. The root file is a local shortcut to the static page inside `public/`.
- Open `public/project-detail.html` for the separate product detail page. Use `?product=galaxy-s26-ultra` or `?product=galaxy-a56-5g` to choose its model.
- Open `research.html` for the customer-profile and trend research workspace.

There is no application server, backend, database, API key, dependency install or build step. The product information and interactions run from local JavaScript files in `public/`.

## Product page anatomy

- **Model selector:** Switch between two sourced India-market Galaxy product records.
- **Trend-to-spec feature cards:** Select a customer signal to see the mapped specification and qualified draft hook.
- **Audience switcher:** Toggle Creator, Executive and Everyday Power messaging, with paraphrased evidence notes.
- **Objection FAQ:** Answers are model-specific and distinguish official specs from limited customer reports.
- **Interactive comparison:** Select either or both models to compare display, camera, battery and software-support details.
- **Sticky action:** Scrolls to the local comparison table. There is no checkout, trade-in estimator, offer feed or external purchase destination.

## Data and claim notes

`public/products.js` contains the static content for the two models. Product specifications were checked against Samsung India Galaxy S26 Ultra and Galaxy A56 5G product pages. The customer feedback summaries are paraphrased from the existing 2025–2026 project research sample; the sample is small and non-representative. The source URLs, dates and limitations remain in the research CSVs and `research_notes.md`.

The product artwork is a CSS-only neutral device illustration, not a Samsung product photograph. Previously generated fictional renders remain in `public/assets/` for reference but are not used to represent either Samsung model. Prices, exchange values, student offers, testimonials and market-wide willingness-to-pay are not fabricated or displayed.

## Research and RAG files

- `research.html`, `styles.css`, `app.js` — local customer-profile and trend-mapping workspace
- `india_mobile_research_findings.csv` — source evidence summaries
- `india_mobile_customer_profiles.csv` — early profile hypotheses
- `india_mobile_trend_spec_hook_drafts.csv` — sourced trend-to-spec hook drafts
- `customer_profiles_template.csv`, `source_evidence_template.csv`, `trend_mapping_template.csv` — blank collection templates
- `research_notes.md` — methodology and evidence limitations
- `rag/` — optional local vector retrieval, clustering and copy-generation scripts

Use the research notes to interpret the CSV evidence. The sample supports exploration and page-copy drafts, not claims about the whole Indian market.
