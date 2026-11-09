"""Generate evidence-linked product-page copy drafts from profile and trend CSVs."""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


CLUSTER_PROFILES = PROJECT_ROOT / "clustered_user_profiles.csv"
SYNTHESIZED_PROFILES = PROJECT_ROOT / "india_mobile_customer_profiles.csv"
DEFAULT_MAPPINGS = PROJECT_ROOT / "india_mobile_trend_spec_hook_drafts.csv"
DEFAULT_MARKDOWN = PROJECT_ROOT / "generated_product_page_copy.md"
DEFAULT_HTML = PROJECT_ROOT / "generated_product_page_copy.html"

PROFILE_ID_FIELDS = ("profile_id", "cluster_id")
EVIDENCE_ID_PATTERN = re.compile(r"\b[A-Z]{2,5}-\d{2,}\b")


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def first_value(row: dict[str, str], *keys: str, fallback: str = "") -> str:
    for key in keys:
        value = clean_text(row.get(key))
        if value:
            return value
    return fallback


def normalize_profiles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    profiles = []
    for row in rows:
        profile_id = first_value(row, *PROFILE_ID_FIELDS, fallback="PROFILE-UNASSIGNED")
        profiles.append({
            "id": profile_id,
            "label": first_value(row, "profile_label", "segment_label", fallback=f"Profile {profile_id}"),
            "use_case": first_value(row, "primary_use_case", "use_case", fallback="Use case not captured in the profile CSV."),
            "pain_points": first_value(row, "pain_points", "pain_point", fallback="No specific pain point recorded."),
            "desired_features": first_value(row, "desired_features_candidate_inferred", "other_buying_factors", fallback="No desired features recorded."),
            "emotional_triggers": first_value(row, "emotional_triggers_explicit_cues_only", fallback="Not explicitly captured in the profile CSV."),
            "evidence_ids": first_value(row, "evidence_ids"),
            "source_urls": first_value(row, "source_urls", "evidence_sources"),
        })
    return profiles


def profile_evidence_ids(profile: dict[str, str]) -> set[str]:
    return set(EVIDENCE_ID_PATTERN.findall(profile.get("evidence_ids", "")))


def mapping_profile_labels(mapping: dict[str, str], profiles: list[dict[str, str]]) -> list[str]:
    related_id = first_value(mapping, "related_profile_id")
    mapping_ids = set(EVIDENCE_ID_PATTERN.findall(" ".join(mapping.values())))
    labels = []
    for profile in profiles:
        direct_match = related_id and related_id == profile["id"]
        evidence_match = bool(mapping_ids & profile_evidence_ids(profile))
        if direct_match or evidence_match:
            labels.append(profile["label"])
    return labels


def sources_for(mapping: dict[str, str]) -> list[str]:
    values = [first_value(mapping, "trend_source_url"), first_value(mapping, "specification_source_url")]
    return list(dict.fromkeys(value for value in values if value))


def markdown_link_list(urls: list[str]) -> str:
    return "; ".join(f"[{url}]({url})" for url in urls) if urls else "No source URL supplied."


def faq_mapping(pain_point: str, mappings: list[dict[str, str]]) -> dict[str, str] | None:
    text = pain_point.lower()
    aliases = {
        "battery": ("battery", "drain", "endurance"),
        "charging": ("charge", "charging"),
        "camera": ("camera", "photo", "image", "zoom"),
        "price": ("price", "value", "budget", "cost", "overpriced"),
        "heat": ("heat", "warm", "thermal", "overheat"),
        "support": ("support", "upgrade", "longevity", "years"),
        "software": ("software", "ui", "lag", "stutter"),
        "display": ("display", "screen"),
        "connectivity": ("bluetooth", "disconnect", "connection"),
    }
    matching_terms = {term for group in aliases.values() if any(term in text for term in group) for term in group}
    if not matching_terms:
        return None
    for mapping in mappings:
        searchable = " ".join(mapping.values()).lower()
        if any(term in searchable for term in matching_terms) and first_value(mapping, "exact_product_specification"):
            return mapping
    return None


def split_items(value: str) -> list[str]:
    return [clean_text(part) for part in re.split(r"\s*\|\s*", value) if clean_text(part)]


def expand_pain_point_topics(pain_point: str) -> list[str]:
    text = pain_point.lower()
    topics = []
    topic_rules = (
        ("battery life or battery drain", r"battery|drain|endurance"),
        ("charging speed", r"charg(?:e|ing)"),
        ("camera quality", r"camera|photo|image|zoom"),
        ("price or value", r"price|value|budget|cost|overpriced|₹"),
        ("device heat", r"heat|warm|thermal|overheat"),
        ("software support and longevity", r"support|upgrade|longevity|years"),
        ("software experience", r"software|one ui|clean ui|lag|stutter"),
        ("display experience", r"display|screen"),
        ("Bluetooth or connection reliability", r"bluetooth|disconnect|connection"),
    )
    for label, pattern in topic_rules:
        if re.search(pattern, text, flags=re.IGNORECASE):
            topics.append(label)
    return topics or [pain_point]


def build_markdown(profiles: list[dict[str, str]], mappings: list[dict[str, str]]) -> str:
    lines = [
        "# Product Page Copy Draft",
        "",
        "> Working draft generated from the supplied profile and trend-mapping CSVs. Check every spec, source, regional claim, and approval status before publication.",
        "",
        "## Headline anchors",
        "",
    ]
    if not profiles:
        lines.append("No customer profiles were supplied; no audience headline anchors were generated.")
    for profile in profiles:
        lines.extend([
            f"### {profile['label']}",
            f"- **Headline anchor:** {profile['label']}: compare the features behind your priorities.",
            f"- **Supporting line:** Explore verified product specifications related to {profile['use_case']}",
            f"- **Pain point evidence:** {profile['pain_points']}",
            f"- **Desired feature candidates:** {profile['desired_features']}",
            f"- **Emotional cues:** {profile['emotional_triggers']}",
            f"- **Evidence:** {profile['evidence_ids'] or 'Evidence IDs not supplied.'} {profile['source_urls']}",
            "",
        ])

    lines.extend(["## Feature sections", ""])
    usable_mappings = [mapping for mapping in mappings if first_value(mapping, "exact_product_specification")]
    if not usable_mappings:
        lines.append("No sourced product specifications were supplied; no feature copy was generated.")
    for mapping in usable_mappings:
        profiles_for_mapping = mapping_profile_labels(mapping, profiles)
        audience = ", ".join(profiles_for_mapping) if profiles_for_mapping else "General audience; no profile link was supplied"
        lines.extend([
            f"### {first_value(mapping, 'trend_label', fallback='Mapped feature')}",
            f"- **Audience connection:** {audience}",
            f"- **Feature copy draft:** {first_value(mapping, 'customer_benefit', fallback='Customer benefit not supplied.')}",
            f"- **Verified specification:** {first_value(mapping, 'exact_product_specification')}",
            f"- **Hook option:** {first_value(mapping, 'marketing_hook_draft', fallback='No hook draft supplied.')}",
            f"- **Claim status:** {first_value(mapping, 'claim_review_status', fallback='Status not supplied.')}",
            f"- **Sources:** {markdown_link_list(sources_for(mapping))}",
            "",
        ])

    lines.extend(["## Objection-handling FAQs", ""])
    faq_count = 0
    for profile in profiles:
        for raw_pain_point in split_items(profile["pain_points"]):
            if raw_pain_point.lower().startswith(("no specific pain point", "no explicit pain point")):
                continue
            for pain_point in expand_pain_point_topics(raw_pain_point):
                match = faq_mapping(pain_point, mappings)
                faq_count += 1
                lines.append(f"### Q: What should {profile['label']} know about {pain_point.rstrip('.')}?")
                if match:
                    hook = first_value(match, "marketing_hook_draft", fallback="No hook supplied.")
                    lines.append(
                        f"**Draft answer:** The mapped specification is {first_value(match, 'exact_product_specification')}. "
                        f"The current benefit note says: {first_value(match, 'customer_benefit', fallback='No benefit note supplied.')}. "
                        f"Suggested page wording: {hook}"
                    )
                    lines.append(f"**Review status:** {first_value(match, 'claim_review_status', fallback='Needs review.')}")
                    lines.append(f"**Source:** {markdown_link_list(sources_for(match))}")
                else:
                    lines.append("**Draft answer:** A verified specification linked to this concern is not present in the supplied mapping. Add an approved product specification and source before answering this objection on the page.")
                lines.append("")
    if not faq_count:
        lines.append("No pain points were supplied; no objection handlers were generated.")
    lines.extend([
        "## Review checklist",
        "",
        "- Confirm the generated profile-to-feature links against the evidence IDs.",
        "- Replace inferred feature candidates with approved product language where required.",
        "- Publish only claims whose status is approved and whose specification source matches the launch model and market.",
        "- Keep unresolved objections open instead of inventing a product answer.",
        "",
    ])
    return "\n".join(lines)


def safe_json_for_script(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build_html(profiles: list[dict[str, str]], mappings: list[dict[str, str]]) -> str:
    table_rows = []
    usable_mappings = [mapping for mapping in mappings if first_value(mapping, "exact_product_specification")]
    categories = sorted({first_value(mapping, "trend_category", fallback="Uncategorized") for mapping in mappings})
    profile_names = sorted({label for mapping in mappings for label in mapping_profile_labels(mapping, profiles)})
    for mapping in mappings:
        audience = ", ".join(mapping_profile_labels(mapping, profiles)) or "General audience / unlinked"
        category = first_value(mapping, "trend_category", fallback="Uncategorized")
        status = first_value(mapping, "claim_review_status", fallback="Needs review")
        row = {
            "trend": first_value(mapping, "trend_label", fallback="Unlabeled trend"),
            "category": category,
            "audience": audience,
            "benefit": first_value(mapping, "customer_benefit", fallback="Not supplied"),
            "specification": first_value(mapping, "exact_product_specification", fallback="Not supplied"),
            "hook": first_value(mapping, "marketing_hook_draft", fallback="Not supplied"),
            "status": status,
            "sources": sources_for(mapping),
        }
        table_rows.append(row)
    data_json = safe_json_for_script(table_rows)
    profile_options = "".join(f'<option value="{html.escape(name, quote=True)}">{html.escape(name)}</option>' for name in profile_names)
    category_options = "".join(f'<option value="{html.escape(name, quote=True)}">{html.escape(name)}</option>' for name in categories)

    headline_cards = []
    for profile in profiles:
        headline_cards.append(
            "<article class='profile-card'>"
            f"<p class='eyebrow'>AUDIENCE ANCHOR</p><h2>{html.escape(profile['label'])}</h2>"
            f"<h3>{html.escape(profile['label'])}: compare the features behind your priorities.</h3>"
            f"<p>Explore verified product specifications related to {html.escape(profile['use_case'])}</p>"
            f"<p><b>Pain points</b><br>{html.escape(profile['pain_points'])}</p>"
            f"<p><b>Desired feature candidates (inferred)</b><br>{html.escape(profile['desired_features'])}</p>"
            f"<p><b>Emotional cues</b><br>{html.escape(profile['emotional_triggers'])}</p></article>"
        )

    faq_blocks = []
    for profile in profiles:
        for raw_pain_point in split_items(profile["pain_points"]):
            if raw_pain_point.lower().startswith(("no specific pain point", "no explicit pain point")):
                continue
            for pain_point in expand_pain_point_topics(raw_pain_point):
                match = faq_mapping(pain_point, mappings)
                question = f"What should {profile['label']} know about {pain_point.rstrip('.')}?"
                if match:
                    answer = (
                        f"The mapped specification is {first_value(match, 'exact_product_specification')}. "
                        f"The supplied benefit note says: {first_value(match, 'customer_benefit', fallback='No benefit note supplied.')}. "
                        f"Suggested page wording: {first_value(match, 'marketing_hook_draft', fallback='No hook supplied.')} "
                        f"Claim status: {first_value(match, 'claim_review_status', fallback='Needs review.')}"
                    )
                    source = " ".join(sources_for(match))
                else:
                    answer = "A verified specification linked to this concern is not present in the supplied mapping. Add an approved specification and source before publishing an answer."
                    source = ""
                source_block = f"<p class='source'>Source: {html.escape(source)}</p>" if source else ""
                faq_blocks.append(f"<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p>{source_block}</details>")

    feature_cards = []
    for mapping in usable_mappings:
        feature_cards.append(
            "<article class='feature'>"
            f"<span class='tag'>{html.escape(first_value(mapping, 'claim_review_status', fallback='Needs review'))}</span>"
            f"<h3>{html.escape(first_value(mapping, 'trend_label', fallback='Mapped feature'))}</h3>"
            f"<p>{html.escape(first_value(mapping, 'customer_benefit', fallback='Customer benefit not supplied.'))}</p>"
            f"<p><b>Specification:</b> {html.escape(first_value(mapping, 'exact_product_specification', fallback='Not supplied.'))}</p>"
            f"<p><b>Hook draft:</b> {html.escape(first_value(mapping, 'marketing_hook_draft', fallback='Not supplied.'))}</p>"
            f"<p class='source'>Sources: {html.escape('; '.join(sources_for(mapping)) or 'Not supplied')}</p></article>"
        )
    feature_html = "".join(feature_cards) or '<p class="muted">No sourced specifications supplied.</p>'
    profile_html = "".join(headline_cards) or '<p class="muted">No profile data supplied.</p>'
    faq_html = "".join(faq_blocks) or '<p class="muted">No pain points supplied.</p>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Page Copy Draft</title><style>
:root{{font-family:Arial,sans-serif;color:#151824;background:#f7f8fb}}body{{margin:0}}header{{background:#1428a0;color:#fff;padding:34px max(24px,calc((100% - 1160px)/2))}}main{{max-width:1160px;margin:28px auto;padding:0 24px}}h1{{font-size:34px;margin:0 0 9px}}header p{{color:#d9defe;margin:0;max-width:850px;line-height:1.5}}h2{{font-size:21px;margin:5px 0}}h3{{font-size:17px}}.eyebrow{{font-size:10px;letter-spacing:.15em;color:#4c61cf;font-weight:bold}}.notice{{background:#fff5de;border:1px solid #f0dfb6;border-radius:10px;padding:14px;margin-bottom:24px;font-size:13px;line-height:1.5}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}.profile-card,.panel{{background:white;border:1px solid #e4e7ef;border-radius:14px;padding:20px;margin-bottom:16px;box-shadow:0 4px 14px #18203b08}}.profile-card p,.panel p{{font-size:13px;line-height:1.55;color:#555d6b}}.feature-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}}.feature{{background:white;border:1px solid #e4e7ef;border-left:4px solid #435de1;border-radius:12px;padding:17px}}.feature h3{{margin:4px 0 10px}}.tag{{display:inline-block;background:#eef0ff;color:#3349b2;border-radius:20px;padding:5px 8px;font-size:10px;font-weight:bold}}.filters{{display:flex;flex-wrap:wrap;gap:9px;margin:12px 0}}input,select{{border:1px solid #dfe3ec;border-radius:7px;padding:10px;font:inherit;background:white}}input{{min-width:220px;flex:1}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;background:#fff;font-size:12px;min-width:900px}}th,td{{text-align:left;vertical-align:top;padding:11px;border-bottom:1px solid #eaecf2;line-height:1.45}}th{{position:sticky;top:0;background:#f0f2ff;color:#26378f}}a{{color:#243fb3}}details{{background:white;border:1px solid #e4e7ef;border-radius:10px;padding:14px 16px;margin:9px 0}}summary{{cursor:pointer;font-weight:bold;font-size:13px}}.source{{font-size:11px;overflow-wrap:anywhere}}.muted{{color:#747b88;font-size:12px}}footer{{text-align:center;color:#767d89;padding:24px;font-size:11px}}@media(max-width:640px){{h1{{font-size:27px}}main{{padding:0 14px}}header{{padding:26px 18px}}}}
</style></head><body>
<header><h1>Product Page Copy Draft</h1><p>Audience-led headline anchors, sourced feature copy, a filterable trend/spec comparison, and objection FAQ drafts.</p></header>
<main><div class="notice"><b>Draft only.</b> Copy is assembled from the supplied CSVs. Candidate features are labeled inferred; unapproved or unsupported claims require review before publication.</div>
<section><h2>Headline anchors</h2><div class="cards">{profile_html}</div></section>
<section class="panel"><h2>Feature sections</h2><div class="feature-grid">{feature_html}</div></section>
<section class="panel"><h2>Interactive trend/spec comparison</h2><p class="muted">Search the mapped evidence, then filter by profile, trend category, or claim status.</p><div class="filters"><input id="search" placeholder="Search trends, specs, or hooks"><select id="profile"><option value="">All profiles</option>{profile_options}</select><select id="category"><option value="">All categories</option>{category_options}</select><select id="status"><option value="">All claim statuses</option></select></div><div class="table-wrap"><table><thead><tr><th>Trend</th><th>Audience</th><th>Customer benefit</th><th>Product spec</th><th>Hook draft</th><th>Status</th><th>Source</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section class="panel"><h2>FAQ objection handlers</h2>{faq_html}</section>
<footer>Generated from source-linked CSV records. Similarity or profile grouping does not establish market prevalence.</footer></main>
<script>
const data={data_json};const statusSelect=document.getElementById('status');[...new Set(data.map(row=>row.status))].sort().forEach(value=>{{const option=document.createElement('option');option.value=value;option.textContent=value;statusSelect.appendChild(option)}});
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,ch=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
function draw(){{const term=document.getElementById('search').value.toLowerCase();const profile=document.getElementById('profile').value;const category=document.getElementById('category').value;const status=document.getElementById('status').value;const filtered=data.filter(row=>JSON.stringify(row).toLowerCase().includes(term)&&(!profile||row.audience.includes(profile))&&(!category||row.category===category)&&(!status||row.status===status));document.getElementById('rows').innerHTML=filtered.map(row=>`<tr><td>${{escapeHtml(row.trend)}}<br><span class="muted">${{escapeHtml(row.category)}}</span></td><td>${{escapeHtml(row.audience)}}</td><td>${{escapeHtml(row.benefit)}}</td><td>${{escapeHtml(row.specification)}}</td><td>${{escapeHtml(row.hook)}}</td><td>${{escapeHtml(row.status)}}</td><td>${{row.sources.map(url=>`<a href="${{escapeHtml(url)}}" target="_blank" rel="noopener">Open source</a>`).join('<br>')||'—'}}</td></tr>`).join('')||'<tr><td colspan="7">No matching mapped features.</td></tr>'}}
['search','profile','category','status'].forEach(id=>document.getElementById(id).addEventListener('input',draw));draw();
</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a structured, source-linked product page copy draft.")
    parser.add_argument("--profiles", type=Path, help="Profile CSV. Defaults to clustered_user_profiles.csv when present; otherwise uses the synthesized profile CSV.")
    parser.add_argument("--mappings", type=Path, default=DEFAULT_MAPPINGS, help="Trend-to-spec mapping CSV.")
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN, help="Markdown copy draft output.")
    parser.add_argument("--html-out", type=Path, default=DEFAULT_HTML, help="Interactive HTML copy draft output.")
    args = parser.parse_args()

    profiles_path = args.profiles or (CLUSTER_PROFILES if CLUSTER_PROFILES.exists() else SYNTHESIZED_PROFILES)
    try:
        profiles = normalize_profiles(read_rows(profiles_path))
        mappings = read_rows(args.mappings)
        if not profiles and not mappings:
            raise ValueError("Both inputs are empty; provide at least one profile or trend mapping.")
        markdown = build_markdown(profiles, mappings)
        interactive_html = build_html(profiles, mappings)
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.html_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
        args.html_out.write_text(interactive_html, encoding="utf-8")
        print(f"Loaded profiles from {profiles_path}")
        print(f"Wrote copy draft: {args.markdown_out}")
        print(f"Wrote interactive comparison: {args.html_out}")
        return 0
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
