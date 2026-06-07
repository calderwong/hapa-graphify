from __future__ import annotations

import argparse
import collections
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

from .core import load_registry, query_graph
from .narrative import (
    DATA_DIR,
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    PUBLIC_ENTRY_PATH,
    Period,
    _date_value,
    _iso_from_epoch,
    _keywords_for_row,
    _label_list,
    _load_evidence,
    _natural_join,
    _period_packet,
    _public_rel,
    _redact_public_payload,
    _source_roots,
    _top_articles,
    _top_turns,
    _truncate,
    _unique,
    _utc_now,
)


ENRICHMENT_LOG_PATH = DATA_DIR / "enrichment-log.ndjson"
ENRICHMENT_RUN_PATH = DATA_DIR / "enrichment-run.json"
DEFAULT_AGENT_ID = "hapa-narrative-enrichment"


def run_narrative_enrichment(
    *,
    entries_path: Path | None = PUBLIC_ENTRY_PATH,
    output: Path | None = None,
    pass_log: Path | None = ENRICHMENT_LOG_PATH,
    run_summary: Path | None = ENRICHMENT_RUN_PATH,
    agent_id: str = DEFAULT_AGENT_ID,
    max_entries: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    started = time.time()
    run_id = f"hapa_narrative_enrichment_{int(started)}"
    pass_id = run_id
    entries_path = entries_path or PUBLIC_ENTRY_PATH
    output = output or entries_path
    pass_log = pass_log or ENRICHMENT_LOG_PATH
    run_summary = run_summary or ENRICHMENT_RUN_PATH

    payload = json.loads(entries_path.read_text(encoding="utf-8"))
    date_range = payload.get("date_range", {})
    start_date = _parse_payload_date(date_range.get("start"), DEFAULT_START_DATE)
    end_date = _parse_payload_date(date_range.get("end"), DEFAULT_END_DATE)

    registry = load_registry()
    source_roots = _source_roots(registry)
    evidence = _load_evidence(source_roots, start_date=start_date, end_date=end_date)
    overall = _overall_context(payload)
    selected = []
    total_queries = 0
    warnings = list(evidence.get("warnings", []))

    entries = payload.get("entries", [])
    for entry in entries:
        if max_entries is not None and len(selected) >= max_entries:
            continue
        period = _entry_period(entry)
        packet = _period_packet(period, evidence)
        neighbors = _entry_neighbors(entry, payload)
        terms = _candidate_terms(entry, packet, overall, neighbors)
        graph_queries = [_query_graph_for_enrichment(term) for term in terms[:5]]
        source_cards = _source_context_cards(packet, terms, limit=8)
        facts = _enrichment_facts(entry, packet, graph_queries, source_cards, overall)
        insights = _enrichment_insights(entry, packet, graph_queries, overall, neighbors)
        connections = _enrichment_connections(entry, graph_queries, overall, neighbors)
        bundle = _enrichment_bundle(
            entry=entry,
            pass_id=pass_id,
            run_id=run_id,
            agent_id=agent_id,
            terms=terms,
            facts=facts,
            insights=insights,
            connections=connections,
            graph_queries=graph_queries,
            source_cards=source_cards,
        )
        _merge_entry_enrichment(entry, bundle)
        selected.append(entry["id"])
        total_queries += len(graph_queries)

    payload["generated_at"] = _utc_now()
    payload["enrichment"] = {
        "schema": "hapa.narrative.enrichment_index.v1",
        "latest_pass_id": pass_id,
        "agent_id": agent_id,
        "updated_at": _utc_now(),
        "entry_count": len(entries),
        "enriched_entry_count": len(selected),
        "log": _public_rel(pass_log),
    }
    payload = _redact_public_payload(payload)

    finished = time.time()
    run_event = _redact_public_payload({
        "schema": "hapa.narrative.enrichment_run.v1",
        "pass_id": pass_id,
        "run_id": run_id,
        "agent_id": agent_id,
        "started_at": _iso_from_epoch(started),
        "finished_at": _iso_from_epoch(finished),
        "duration_ms": int((finished - started) * 1000),
        "entries_seen": len(entries),
        "entries_enriched": len(selected),
        "graphify_query_count": total_queries,
        "source_counts": evidence.get("source_counts", {}),
        "output": _public_rel(output),
        "pass_log": _public_rel(pass_log),
        "dry_run": dry_run,
        "warnings": warnings,
        "ok": True,
    })

    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        run_summary.parent.mkdir(parents=True, exist_ok=True)
        run_summary.write_text(json.dumps(run_event, indent=2, sort_keys=True), encoding="utf-8")
        pass_log.parent.mkdir(parents=True, exist_ok=True)
        with pass_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run_event, sort_keys=True) + "\n")

    return {
        "ok": True,
        "dry_run": dry_run,
        "pass_id": pass_id,
        "agent_id": agent_id,
        "entries_seen": len(entries),
        "entries_enriched": len(selected),
        "graphify_query_count": total_queries,
        "output": str(output),
        "pass_log": str(pass_log),
        "run": run_event,
    }


def _parse_payload_date(value: Any, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return fallback


def _entry_period(entry: dict[str, Any]) -> Period:
    period = entry.get("period", {})
    end = date.fromisoformat(str(period.get("end"))[:10])
    if entry.get("kind") == "summary_so_far":
        return Period("summary_so_far", None, end)
    start = date.fromisoformat(str(period.get("start"))[:10])
    return Period("weekly", start, end)


def _overall_context(payload: dict[str, Any]) -> dict[str, Any]:
    topic_counts: collections.Counter[str] = collections.Counter()
    keyword_counts: collections.Counter[str] = collections.Counter()
    topic_entries: dict[str, list[str]] = collections.defaultdict(list)
    entry_ids = []
    for entry in payload.get("entries", []):
        entry_ids.append(entry.get("id"))
        for item in entry.get("evidence", {}).get("top_topics", []):
            key = str(item.get("key") or "")
            if key:
                topic_counts[key] += int(item.get("count") or 1)
                topic_entries[key].append(entry["id"])
        for item in entry.get("evidence", {}).get("top_keywords", []):
            key = str(item.get("key") or "")
            if key:
                keyword_counts[key] += int(item.get("count") or 1)
    return {
        "topic_counts": topic_counts,
        "keyword_counts": keyword_counts,
        "topic_entries": {key: values for key, values in topic_entries.items()},
        "entry_ids": entry_ids,
    }


def _entry_neighbors(entry: dict[str, Any], payload: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    entries = payload.get("entries", [])
    index = next((idx for idx, item in enumerate(entries) if item.get("id") == entry.get("id")), -1)
    previous_entry = entries[index - 1] if index > 0 else None
    next_entry = entries[index + 1] if 0 <= index < len(entries) - 1 else None
    return {"previous": previous_entry, "next": next_entry}


def _candidate_terms(
    entry: dict[str, Any],
    packet: dict[str, Any],
    overall: dict[str, Any],
    neighbors: dict[str, dict[str, Any] | None],
) -> list[str]:
    evidence = entry.get("evidence", {})
    topics = [str(item.get("key")) for item in evidence.get("top_topics", [])[:5] if item.get("key")]
    keywords = [str(item.get("key")) for item in evidence.get("top_keywords", [])[:5] if item.get("key")]
    packet_keywords = [str(item.get("key")) for item in packet.get("keyword_counts", [])[:5] if item.get("key")]
    recurring_topics = [
        key for key, _count in overall.get("topic_counts", collections.Counter()).most_common(8)
        if key in set(topics)
    ]
    neighbor_terms = []
    for neighbor in (neighbors.get("previous"), neighbors.get("next")):
        if neighbor:
            neighbor_terms.extend(
                str(item.get("key"))
                for item in neighbor.get("evidence", {}).get("top_topics", [])[:2]
                if item.get("key")
            )
    title_terms = [
        term for term in re.split(r"[:/|,]", str(entry.get("title") or ""))
        if len(term.strip()) > 3 and not term.strip().lower().startswith("week of")
    ]
    terms = _unique([
        *keywords,
        *packet_keywords,
        *topics,
        *recurring_topics,
        *neighbor_terms,
        *title_terms,
        "Hapa Protocol",
        "Hapa canon",
    ])
    return [_truncate(term, 72) for term in terms if term]


def _query_graph_for_enrichment(term: str) -> dict[str, Any]:
    try:
        result = query_graph(term, source_id="all", limit=8, limit_per_source=100)
    except Exception as exc:  # pragma: no cover - local source variance
        return {"query": term, "ok": False, "error": str(exc), "match_count": 0, "top_matches": []}
    return {
        "query": term,
        "ok": bool(result.get("ok")),
        "match_count": int(result.get("match_count") or 0),
        "top_matches": [
            {
                "id": item.get("node", {}).get("id"),
                "label": item.get("node", {}).get("label"),
                "source_id": item.get("node", {}).get("source_id"),
                "type": item.get("node", {}).get("type"),
                "truth_status": item.get("node", {}).get("truth_status"),
                "score": item.get("score"),
            }
            for item in result.get("matches", [])[:5]
        ],
    }


def _source_context_cards(packet: dict[str, Any], terms: list[str], *, limit: int) -> list[dict[str, Any]]:
    terms_lower = [term.lower() for term in terms]
    cards: list[dict[str, Any]] = []
    for row in _rank_rows(packet.get("turns", []), terms_lower)[:limit]:
        cards.append({
            "kind": "second-brain-turn",
            "label": _truncate(row.get("objective") or row.get("turn_id"), 120),
            "detail": _truncate(row.get("work_summary") or row.get("reusable_insight") or row.get("decision_summary"), 260),
            "started_at": row.get("turn_started_at"),
            "turn_type": row.get("turn_type"),
            "link": f"hapa://second-brain/turn/{row.get('turn_id')}",
            "truth_status": "verified_source",
        })
    for row in _top_articles(packet.get("wiki_articles", []), 4):
        cards.append({
            "kind": "second-brain-wiki-article",
            "label": _truncate(row.get("title") or row.get("slug"), 120),
            "detail": _truncate(row.get("summary"), 260),
            "updated_at": row.get("updated_at"),
            "link": row.get("link"),
            "truth_status": "verified_source",
        })
    for row in packet.get("wiki_files", [])[:4]:
        cards.append({
            "kind": "wiki-file",
            "label": _truncate(row.get("title") or row.get("relpath"), 120),
            "detail": _truncate(row.get("relpath"), 160),
            "updated_at": row.get("modified_at"),
            "link": row.get("link"),
            "truth_status": "verified_source",
        })
    return cards[:limit]


def _rank_rows(rows: list[dict[str, Any]], terms_lower: list[str]) -> list[dict[str, Any]]:
    def score(row: dict[str, Any]) -> tuple[int, int, str]:
        text = " ".join(str(row.get(field) or "") for field in (
            "objective", "work_summary", "reusable_insight", "decision_summary", "topic_labels_json"
        )).lower()
        hits = sum(1 for term in terms_lower if term and term in text)
        keyword_hits = len(_keywords_for_row(row))
        return (hits, keyword_hits, str(row.get("turn_started_at") or ""))

    return sorted(rows, key=score, reverse=True)


def _enrichment_facts(
    entry: dict[str, Any],
    packet: dict[str, Any],
    graph_queries: list[dict[str, Any]],
    source_cards: list[dict[str, Any]],
    overall: dict[str, Any],
) -> list[dict[str, Any]]:
    counts = packet.get("evidence_counts", {})
    facts = [{
        "label": "Observed activity",
        "detail": (
            f"{counts.get('turns', 0):,} Second Brain turns, "
            f"{counts.get('wiki_articles', 0):,} wiki article updates, and "
            f"{counts.get('wiki_files', 0):,} wiki/doc file changes are in the selected period."
        ),
        "truth_status": "verified_source",
    }]
    if packet.get("turn_type_counts"):
        facts.append({
            "label": "Dominant work modes",
            "detail": _label_list(packet["turn_type_counts"], 4),
            "truth_status": "derived_or_inferred",
        })
    if source_cards:
        card = source_cards[0]
        facts.append({
            "label": "Strong source card",
            "detail": f"{card['kind']}: {card['label']}",
            "truth_status": card.get("truth_status", "verified_source"),
            "link": card.get("link"),
        })
    best_query = max(graph_queries, key=lambda item: int(item.get("match_count") or 0), default=None)
    if best_query:
        facts.append({
            "label": "Graphify expansion",
            "detail": f"`{best_query['query']}` returned {best_query.get('match_count', 0):,} atlas matches.",
            "truth_status": "derived_or_inferred",
        })
    recurring = [
        topic for topic in (item.get("key") for item in entry.get("evidence", {}).get("top_topics", [])[:5])
        if topic and len(overall.get("topic_entries", {}).get(topic, [])) > 1
    ]
    if recurring:
        facts.append({
            "label": "Recurring canon themes",
            "detail": _natural_join(recurring[:4]),
            "truth_status": "derived_or_inferred",
        })
    return facts[:6]


def _enrichment_insights(
    entry: dict[str, Any],
    packet: dict[str, Any],
    graph_queries: list[dict[str, Any]],
    overall: dict[str, Any],
    neighbors: dict[str, dict[str, Any] | None],
) -> list[dict[str, str]]:
    topics = _label_list(packet.get("topic_counts", []), 4)
    counts = packet.get("evidence_counts", {})
    best_query = max(graph_queries, key=lambda item: int(item.get("match_count") or 0), default=None)
    previous = neighbors.get("previous")
    next_entry = neighbors.get("next")
    continuity = []
    if previous:
        continuity.append(f"back to `{previous['id']}`")
    if next_entry:
        continuity.append(f"forward to `{next_entry['id']}`")
    continuity_text = " and ".join(continuity) if continuity else "inside the standing Hapa atlas"
    technical = (
        f"The enrichment pass reads this period as a cluster centered on {topics}, with "
        f"{counts.get('turns', 0):,} observed turns. Its strongest graph expansion is "
        f"`{best_query['query']}` with {best_query.get('match_count', 0):,} matches."
        if best_query else
        f"The enrichment pass reads this period as a cluster centered on {topics}, with bounded source evidence and no successful graph expansion."
    )
    lore = (
        f"Lore lens: this card binds {continuity_text}; its archive light is strongest around {topics}, "
        "so any future retelling should treat those motifs as witnessed runes, not invented scenery."
    )
    return [
        {"track": "technical", "text": technical},
        {"track": "lore_card", "text": lore},
    ]


def _enrichment_connections(
    entry: dict[str, Any],
    graph_queries: list[dict[str, Any]],
    overall: dict[str, Any],
    neighbors: dict[str, dict[str, Any] | None],
) -> list[dict[str, Any]]:
    connections: list[dict[str, Any]] = []
    for kind, neighbor in (("previous_entry", neighbors.get("previous")), ("next_entry", neighbors.get("next"))):
        if neighbor:
            shared = _shared_entry_topics(entry, neighbor)
            connections.append({
                "kind": kind,
                "target_entry_id": neighbor["id"],
                "label": neighbor.get("title"),
                "shared_topics": shared,
                "truth_status": "derived_or_inferred",
            })
    for topic in [item.get("key") for item in entry.get("evidence", {}).get("top_topics", [])[:4] if item.get("key")]:
        targets = [item for item in overall.get("topic_entries", {}).get(topic, []) if item != entry.get("id")]
        if targets:
            connections.append({
                "kind": "recurring_topic",
                "label": topic,
                "target_entry_ids": targets[:6],
                "truth_status": "derived_or_inferred",
            })
    for query in graph_queries:
        for match in query.get("top_matches", [])[:2]:
            if match.get("id"):
                connections.append({
                    "kind": "graphify_node",
                    "query": query.get("query"),
                    "target_node_id": match.get("id"),
                    "label": match.get("label"),
                    "source_id": match.get("source_id"),
                    "node_type": match.get("type"),
                    "truth_status": match.get("truth_status") or "derived_or_inferred",
                })
    return connections[:12]


def _shared_entry_topics(entry: dict[str, Any], other: dict[str, Any]) -> list[str]:
    current = {item.get("key") for item in entry.get("evidence", {}).get("top_topics", []) if item.get("key")}
    candidate = {item.get("key") for item in other.get("evidence", {}).get("top_topics", []) if item.get("key")}
    return sorted(current & candidate)[:6]


def _enrichment_bundle(
    *,
    entry: dict[str, Any],
    pass_id: str,
    run_id: str,
    agent_id: str,
    terms: list[str],
    facts: list[dict[str, Any]],
    insights: list[dict[str, str]],
    connections: list[dict[str, Any]],
    graph_queries: list[dict[str, Any]],
    source_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = _enrichment_summary(entry, facts, insights, connections)
    pass_record = {
        "pass_id": pass_id,
        "run_id": run_id,
        "agent_id": agent_id,
        "created_at": _utc_now(),
        "query_count": len(graph_queries),
        "fact_count": len(facts),
        "connection_count": len(connections),
        "source_card_count": len(source_cards),
    }
    return {
        "schema": "hapa.narrative.entry_enrichment.v1",
        "latest_pass_id": pass_id,
        "updated_at": _utc_now(),
        "summary": summary,
        "selection": {
            "reason": "Selected bounded week/context terms from topics, keywords, adjacent entries, and standing Hapa protocol terms.",
            "terms": terms[:8],
        },
        "facts": facts,
        "insights": insights,
        "connections": connections,
        "graphify_queries": graph_queries,
        "source_cards": source_cards,
        "passes": [pass_record],
    }


def _enrichment_summary(
    entry: dict[str, Any],
    facts: list[dict[str, Any]],
    insights: list[dict[str, str]],
    connections: list[dict[str, Any]],
) -> str:
    fact = facts[0]["detail"] if facts else "No new bounded facts were selected."
    technical = next((item["text"] for item in insights if item.get("track") == "technical"), "")
    return _truncate(f"{fact} {technical} Connections selected: {len(connections)}.", 420)


def _merge_entry_enrichment(entry: dict[str, Any], bundle: dict[str, Any]) -> None:
    prior = entry.get("enrichment") or {}
    prior_passes = list(prior.get("passes") or [])
    merged = dict(bundle)
    merged["passes"] = (prior_passes + bundle.get("passes", []))[-12:]
    merged["pass_count"] = len(merged["passes"])
    entry["enrichment"] = merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Hapa narrative enrichment pass.")
    parser.add_argument("--entries", default=str(PUBLIC_ENTRY_PATH))
    parser.add_argument("--output")
    parser.add_argument("--pass-log", default=str(ENRICHMENT_LOG_PATH))
    parser.add_argument("--run-summary", default=str(ENRICHMENT_RUN_PATH))
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    parser.add_argument("--max-entries", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_narrative_enrichment(
        entries_path=Path(args.entries),
        output=Path(args.output) if args.output else None,
        pass_log=Path(args.pass_log),
        run_summary=Path(args.run_summary),
        agent_id=args.agent_id,
        max_entries=args.max_entries,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Enriched {result['entries_enriched']} Hapa narrative entries in {result['output']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
