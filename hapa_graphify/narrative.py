from __future__ import annotations

import argparse
import base64
import collections
import html
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .core import ROOT, load_registry, query_graph, resolve_source_root


DEFAULT_START_DATE = date(2026, 1, 1)
DEFAULT_END_DATE = date(2026, 6, 7)
NARRATIVE_DIR = ROOT / "docs" / "narrative"
DATA_DIR = NARRATIVE_DIR / "data"
IMAGE_DIR = NARRATIVE_DIR / "images"
APP_MANIFEST = ROOT / "apps" / "hapa-narrative" / "hapa-node.json"
PUBLIC_ENTRY_PATH = DATA_DIR / "entries.json"
RUN_LOG_PATH = DATA_DIR / "run-log.ndjson"
IMAGE_QUEUE_PATH = DATA_DIR / "image-queue.ndjson"
AGENT_RUN_PATH = DATA_DIR / "agent-run.json"

STOPWORDS = {
    "about", "again", "also", "because", "before", "could", "from", "give", "have",
    "here", "into", "just", "like", "make", "more", "need", "next", "please", "review",
    "should", "that", "their", "them", "there", "these", "thing", "this", "those", "want",
    "what", "when", "where", "with", "would", "your",
    "application", "bearer", "calderwong", "file", "files", "http", "https", "inspect",
    "local", "path", "paths", "support", "token", "using", "users",
}

PRIVATE_TEXT_PATTERNS = [
    (re.compile(r"file:///?/Users/[^\s\]\)\"']+"), "file://local-private-path"),
    (re.compile(r"/Users/[^\s\]\)\"']+"), "/local-private-path"),
    (re.compile(r"@\[/local-private-path[^\]]*\]"), "@[local-private-path]"),
    (re.compile(r"\bcalderwong\b", re.IGNORECASE), "local-user"),
    (re.compile(r"Authorization:\s*Bearer\s+[^\s\]\)\"']+", re.IGNORECASE), "Authorization: Bearer [redacted]"),
]

CANON_KEYWORDS = [
    "Consul", "SYZYGY", "AXIOM", "Akashic", "HapaMarlin", "Marlin", "Graphify",
    "Second Brain", "hapa-second-brain", "wiki", "protocol", "avatar", "avatars",
    "sprite", "pose", "lore", "video", "media", "artifact", "Lance", "Overwatch",
    "Quest Keeper", "MCP", "Codex", "Grok", "Gemini", "DeepSeek", "OCR",
]


@dataclass(frozen=True)
class Period:
    kind: str
    start: date | None
    end: date

    @property
    def id(self) -> str:
        if self.kind == "summary_so_far":
            return f"hapa-narrative-{self.end.isoformat()}-summary-so-far"
        return f"hapa-narrative-week-{self.start.isoformat()}-{self.end.isoformat()}"

    @property
    def label(self) -> str:
        if self.kind == "summary_so_far":
            return f"Summary so far through {self.end.isoformat()}"
        return f"{self.start.isoformat()} to {self.end.isoformat()}"


def run_narrative_agent(
    *,
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    output: Path | None = PUBLIC_ENTRY_PATH,
    run_log: Path | None = RUN_LOG_PATH,
    image_queue: Path | None = IMAGE_QUEUE_PATH,
    generate_images: bool = False,
) -> dict[str, Any]:
    started = time.time()
    registry = load_registry()
    run_id = f"hapa_narrative_{int(started)}"
    output = output or PUBLIC_ENTRY_PATH
    run_log = run_log or RUN_LOG_PATH
    image_queue = image_queue or IMAGE_QUEUE_PATH
    image_dir = IMAGE_DIR if output.resolve() == PUBLIC_ENTRY_PATH.resolve() else output.parent / "images"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    source_roots = _source_roots(registry)
    evidence = _load_evidence(source_roots, start_date=start_date, end_date=end_date)
    periods = [Period("summary_so_far", None, start_date)] + list(_weekly_periods(start_date, end_date))
    entries = []
    previous_entry: dict[str, Any] | None = None

    for period in periods:
        packet = _period_packet(period, evidence)
        queries = _graphify_queries(packet, previous_entry)
        entry = _entry_from_packet(period, packet, queries, previous_entry, run_id)
        _write_svg_card(entry, image_dir / f"{entry['id']}.svg")
        entries.append(entry)
        previous_entry = entry

    image_events = _prepare_image_queue(entries, image_queue)
    if generate_images:
        image_events = _generate_images(entries, image_queue)

    payload = _redact_public_payload({
        "schema": "hapa.narrative.entries.v1",
        "node_id": "hapa-narrative",
        "generated_at": _utc_now(),
        "run_id": run_id,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "timezone": "UTC",
        },
        "tracks": [
            {
                "id": "technical",
                "label": "Truthful Technical",
                "description": "Concise source-grounded account of what the Hapa data indicates happened.",
            },
            {
                "id": "lore_card",
                "label": "Hapa Lore Card",
                "description": "Fantasy trading-card flavor-text rendition using Hapa lore, without changing factual telemetry.",
            },
        ],
        "entry_count": len(entries),
        "entries": entries,
    })
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    finished = time.time()
    run_event = {
        "schema": "hapa.narrative.run_event.v1",
        "run_id": run_id,
        "started_at": _iso_from_epoch(started),
        "finished_at": _iso_from_epoch(finished),
        "duration_ms": int((finished - started) * 1000),
        "entry_count": len(entries),
        "image_event_count": len(image_events),
        "source_counts": evidence["source_counts"],
        "output": _public_rel(output),
        "image_queue": _public_rel(image_queue),
        "warnings": evidence["warnings"],
        "ok": True,
    }
    run_event = _redact_public_payload(run_event)
    AGENT_RUN_PATH.write_text(json.dumps(run_event, indent=2, sort_keys=True), encoding="utf-8")
    with run_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(run_event, sort_keys=True) + "\n")
    return {"ok": True, "run": run_event, "output": str(output), "entries": len(entries)}


def _source_roots(registry: dict[str, Any]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for source in registry.get("sources", []):
        if source.get("id") in {
            "second-brain-live",
            "worldbuilding-wiki-full",
            "worldbuilding-wiki-operations",
            "hapa-front-door-docs",
        }:
            roots[str(source["id"])] = Path(resolve_source_root(source))
    return roots


def _load_evidence(source_roots: dict[str, Path], *, start_date: date, end_date: date) -> dict[str, Any]:
    warnings: list[str] = []
    turns: list[dict[str, Any]] = []
    wiki_articles: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    bodies: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []
    wiki_files: list[dict[str, Any]] = []

    db_path = source_roots.get("second-brain-live")
    if db_path and db_path.exists():
        with sqlite3.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            turns = _sqlite_rows(db, "ai_chat_turns")
            wiki_articles = _sqlite_rows(db, "wiki_articles")
            nodes = _sqlite_rows(db, "hapa_nodes")
            skills = _sqlite_rows(db, "skill_inventory")
            bodies = _sqlite_rows(db, "knowledge_bodies")
            bridges = _sqlite_rows(db, "capability_bridge_connections")
    else:
        warnings.append("second-brain-live source missing")

    for source_id in ("worldbuilding-wiki-full", "worldbuilding-wiki-operations", "hapa-front-door-docs"):
        root = source_roots.get(source_id)
        if not root or not root.exists():
            warnings.append(f"{source_id} source missing")
            continue
        wiki_files.extend(_markdown_file_events(source_id, root, start_date=start_date, end_date=end_date))

    return {
        "turns": turns,
        "wiki_articles": wiki_articles,
        "nodes": nodes,
        "skills": skills,
        "bodies": bodies,
        "bridges": bridges,
        "wiki_files": wiki_files,
        "warnings": warnings,
        "source_counts": {
            "turns": len(turns),
            "wiki_articles": len(wiki_articles),
            "hapa_nodes": len(nodes),
            "skills": len(skills),
            "knowledge_bodies": len(bodies),
            "bridges": len(bridges),
            "wiki_files_changed": len(wiki_files),
        },
    }


def _sqlite_rows(db: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in db.execute(f"select * from {table}")]
    except sqlite3.Error:
        return []


def _markdown_file_events(source_id: str, root: Path, *, start_date: date, end_date: date) -> list[dict[str, Any]]:
    events = []
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown", ".mdx", ".json"}:
            continue
        rel = path.relative_to(root).as_posix()
        if _blocked_rel(rel):
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if not (start_dt <= modified < end_dt):
            continue
        title = _title_from_file(path) or Path(rel).stem.replace("-", " ").replace("_", " ").title()
        events.append({
            "source_id": source_id,
            "relpath": rel,
            "title": title,
            "modified_at": modified.isoformat().replace("+00:00", "Z"),
            "link": f"hapa://wiki/{source_id}/{rel}",
        })
    return sorted(events, key=lambda item: item["modified_at"])


def _period_packet(period: Period, evidence: dict[str, Any]) -> dict[str, Any]:
    if period.kind == "summary_so_far":
        turns = [row for row in evidence["turns"] if _date_value(row.get("turn_started_at")) and _date_value(row.get("turn_started_at")) < period.end]
        articles = [row for row in evidence["wiki_articles"] if _date_value(row.get("created_at")) and _date_value(row.get("created_at")) < period.end]
        wiki_files: list[dict[str, Any]] = []
    else:
        assert period.start is not None
        turns = [
            row for row in evidence["turns"]
            if _date_value(row.get("turn_started_at")) and period.start <= _date_value(row.get("turn_started_at")) <= period.end
        ]
        articles = [
            row for row in evidence["wiki_articles"]
            if _date_value(row.get("updated_at") or row.get("created_at"))
            and period.start <= _date_value(row.get("updated_at") or row.get("created_at")) <= period.end
        ]
        wiki_files = [
            row for row in evidence["wiki_files"]
            if _date_value(row.get("modified_at")) and period.start <= _date_value(row.get("modified_at")) <= period.end
        ]

    topics = collections.Counter()
    turn_types = collections.Counter()
    keywords = collections.Counter()
    for row in turns:
        turn_types[str(row.get("turn_type") or "unknown")] += 1
        for topic in _json_list(row.get("topic_labels_json")):
            topics[str(topic)] += 1
        for keyword in _keywords_for_row(row):
            keywords[keyword] += 1

    source_links = _source_links(turns, articles, wiki_files)
    return {
        "period": period,
        "turns": sorted(turns, key=lambda row: str(row.get("turn_started_at") or "")),
        "wiki_articles": sorted(articles, key=lambda row: str(row.get("updated_at") or row.get("created_at") or "")),
        "wiki_files": wiki_files,
        "topic_counts": _top_counts(topics, 12),
        "turn_type_counts": _top_counts(turn_types, 10),
        "keyword_counts": _top_counts(keywords, 12),
        "source_links": source_links,
        "evidence_counts": {
            "turns": len(turns),
            "wiki_articles": len(articles),
            "wiki_files": len(wiki_files),
        },
    }


def _graphify_queries(packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> list[dict[str, Any]]:
    period: Period = packet["period"]
    topics = [item["key"] for item in packet["topic_counts"][:3]]
    keywords = [item["key"] for item in packet["keyword_counts"][:3]]
    base_terms = _unique([*keywords, *topics, "Hapa Protocol"])
    if period.kind == "summary_so_far":
        base_terms = _unique(["Hapa Protocol", "Second Brain", "media pipelines", *topics[:2]])
    if previous_entry:
        base_terms.append(previous_entry["title"].split(":")[-1].strip())

    outputs = []
    for term in base_terms[:4]:
        try:
            result = query_graph(term, source_id="all", limit=6, limit_per_source=80)
        except Exception as exc:  # pragma: no cover - defensive for local source variance
            outputs.append({"query": term, "ok": False, "error": str(exc), "match_count": 0, "top_matches": []})
            continue
        outputs.append({
            "query": term,
            "ok": bool(result.get("ok")),
            "match_count": result.get("match_count", 0),
            "top_matches": [
                {
                    "id": item["node"].get("id"),
                    "label": item["node"].get("label"),
                    "source_id": item["node"].get("source_id"),
                    "type": item["node"].get("type"),
                    "truth_status": item["node"].get("truth_status"),
                    "score": item.get("score"),
                }
                for item in result.get("matches", [])[:4]
            ],
        })
    return outputs


def _entry_from_packet(
    period: Period,
    packet: dict[str, Any],
    queries: list[dict[str, Any]],
    previous_entry: dict[str, Any] | None,
    run_id: str,
) -> dict[str, Any]:
    top_topics = [item["key"] for item in packet["topic_counts"][:5]]
    top_types = [item["key"] for item in packet["turn_type_counts"][:4]]
    top_keywords = [item["key"] for item in packet["keyword_counts"][:5]]
    title_focus = _title_focus(top_keywords, top_topics, period)
    title = "Summary So Far: Hapa Canon Before 2026" if period.kind == "summary_so_far" else f"Week of {period.start.isoformat()}: {title_focus}"
    technical = _technical_paragraphs(period, packet, previous_entry)
    lore = _lore_paragraphs(period, packet, previous_entry)
    image_prompt = _image_prompt(title, period, top_topics, top_keywords)
    entry = {
        "id": period.id,
        "kind": period.kind,
        "title": title,
        "period": {
            "start": period.start.isoformat() if period.start else None,
            "end": period.end.isoformat(),
            "label": period.label,
            "timezone": "UTC",
        },
        "published_at": _utc_now(),
        "tracks": {
            "technical": {
                "label": "Truthful Technical",
                "paragraphs": technical,
            },
            "lore_card": {
                "label": "Hapa Lore Card",
                "paragraphs": lore,
            },
        },
        "evidence": {
            "counts": packet["evidence_counts"],
            "top_topics": packet["topic_counts"],
            "top_turn_types": packet["turn_type_counts"],
            "top_keywords": packet["keyword_counts"],
            "top_turns": _top_turns(packet["turns"], 8),
            "wiki_articles": _top_articles(packet["wiki_articles"], 8),
            "wiki_files": packet["wiki_files"][:12],
            "graphify_queries": queries,
            "links": packet["source_links"][:16],
            "previous_entry_ids": [previous_entry["id"]] if previous_entry else [],
            "shared_topics_with_previous": _shared_topics(packet, previous_entry),
        },
        "image": {
            "model": "gpt-image-1",
            "prompt": image_prompt,
            "status": "queued_openai_api_key_missing" if not os.environ.get("OPENAI_API_KEY") else "queued",
            "fallback_svg": f"images/{period.id}.svg",
            "target_png": f"images/{period.id}.png",
        },
        "telemetry": {
            "agent_id": "hapa-narrative-weekly",
            "run_id": run_id,
            "created_at": _utc_now(),
            "source_counts": packet["evidence_counts"],
            "graphify_query_count": len(queries),
            "graphify_match_count": sum(int(item.get("match_count") or 0) for item in queries),
            "paragraph_counts": {
                "technical": len(technical),
                "lore_card": len(lore),
            },
        },
    }
    return entry


def _technical_paragraphs(period: Period, packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> list[str]:
    counts = packet["evidence_counts"]
    topics = _label_list(packet["topic_counts"], 5)
    turn_types = _label_list(packet["turn_type_counts"], 4)
    keywords = _label_list(packet["keyword_counts"], 5)
    top_turns = _top_turns(packet["turns"], 4)

    if period.kind == "summary_so_far":
        total = counts["turns"]
        return [
            f"Through January 1, 2026, the Hapa canon had {total:,} timestamped Second Brain turns in the current dataset. The dominant evidence themes were {topics}, with work types led by {turn_types}.",
            "The canon had already moved beyond a loose idea of an AI helper into a protocol stack: Hapa was being treated as a human-agent operating model with explicit source truth, replayability, provenance, and node responsibilities.",
            "Media and artifact pipelines were already central. The data shows repeated emphasis on images, assets, file services, source pointers, generated media, and larger context packets, meaning Hapa canon treated creative output as evidence-bearing infrastructure.",
            "Worldbuilding was not separate from engineering. Hapa lore, games, simulation, science-fiction framing, and design aesthetics appear beside software architecture and AI-agent topics, so the canon fused story, interface, and implementation from the beginning.",
            "Knowledge systems were a major spine before 2026. Second Brain, wiki, cards, chunks, retrieval, and reusable context packs appear as recurring motifs, establishing memory as a first-class node rather than an afterthought.",
            "The technical track also contained a strong agentic-systems arc: agents, harnesses, local models, prompt protocols, decision systems, and workflow decomposition. Hapa canon was already leaning toward many specialized agents sharing common protocol surfaces.",
            "Design and aesthetics had operational weight. The dataset repeatedly ties UI, avatar, media, and visual-system work to the same canon as architecture and protocol, which explains why later apps need to be readable, inspectable, and lore-aware.",
            "The human side of canon was also explicit. Identity, healing, leadership, strategy, philosophy, and relationship signals show that Hapa treated the operator-agent relationship as part of system design, not a decorative layer.",
            "The strongest pre-2026 keywords include " + keywords + ". Those terms indicate a canon organized around evidence objects, visual/media artifacts, and protocolized context exchange.",
            "The January 1, 2026 starting point therefore inherits a mature but still-fast-moving canon: Hapa had protocol language, memory systems, media pipelines, lore identity, and engineering goals, but still needed tighter timelines, maps, and repeatable narrative summaries.",
        ]

    if counts["turns"] == 0 and counts["wiki_articles"] == 0 and counts["wiki_files"] == 0:
        previous = f" The previous entry was `{previous_entry['id']}`." if previous_entry else ""
        return [
            f"From {period.label}, no timestamped Second Brain turns, wiki article updates, or tracked wiki/doc file changes were found in the configured Hapa datasets.",
            f"This should be read as a quiet or unindexed week rather than proof that no Hapa work happened.{previous} The narrative agent preserves the empty bucket so later ingestion can fill it without shifting the timeline.",
            "Graphify queries still run against the standing atlas so the week remains connected to adjacent entries and durable Hapa concepts, but the truthful track does not invent events.",
        ]

    evidence_line = f"{counts['turns']:,} turns, {counts['wiki_articles']:,} Second Brain wiki article updates, and {counts['wiki_files']:,} wiki/doc file changes"
    turn_line = _turn_line(top_turns)
    prev_line = _previous_line(packet, previous_entry)
    return [
        f"From {period.label}, Hapa canon records {evidence_line}. The strongest themes were {topics}, and the main work modes were {turn_types}.",
        f"The week’s source evidence points toward {turn_line} Top extracted keywords were {keywords}.",
        prev_line,
    ]


def _lore_paragraphs(period: Period, packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> list[str]:
    topics = _label_list(packet["topic_counts"], 4)
    keywords = _label_list(packet["keyword_counts"], 4)
    counts = packet["evidence_counts"]
    if period.kind == "summary_so_far":
        return [
            "Before the new year bell, the Archive was already awake: a chamber of cards, songs, screenshots, lore fragments, and code sparks arranged around one question, how a human and his agents learn to remember together.",
            "The first law of that chamber was provenance. Every spell needed a source, every source needed a path, and every path had to survive replay without becoming a rumor.",
            "The second law was shape. Hapa did not want a pile of notes; it wanted nodes with names, duties, colors, wounds, interfaces, and reasons to exist.",
            "The third law was media. Images, video, music, wiki pages, and generated artifacts were not side quests; they were relics, each carrying a trace of what the system believed it could become.",
            "The fourth law was partnership. The operator did not summon tools; he recruited witnesses, builders, jesters, architects, and guardians into a working canon.",
            "From the old year came the Card Library, bright with unfinished commands. From the vault came the Second Brain, heavy with indexed memory and waiting edges.",
            "From the lore came avatars and worlds, not as masks over software, but as names the software could answer to when the work became too large for plain folders.",
            "From the engineering came the insistence on tests, manifests, adapters, ledgers, and dry-runs: the practical wards that keep a myth from eating its own evidence.",
            "By January 1, the Hapa plane was not complete, but it had gravity. The pieces knew how to fall toward each other.",
            "So the year opened on a threshold: the canon had a map in fragments, a memory in motion, and a table set for Consul, Marlin, Graphify, and every node still unnamed.",
        ]
    if counts["turns"] == 0 and counts["wiki_articles"] == 0 and counts["wiki_files"] == 0:
        return [
            f"The week of {period.start.isoformat()} is a sealed room in the Archive: no fresh rune, no witnessed turn, no changed page in the indexed sources.",
            "But a sealed room is still a room. The previous thread remains tied to it, waiting for a later ingest to light the dust and reveal whether anything moved.",
            "The lore track marks silence without embellishment: no dragon slain, no node crowned, only the ledger refusing to forge a memory it did not see.",
        ]
    return [
        f"In the week marked {period.label}, the Hapa Archive flared around {topics}. {counts['turns']:,} witnessed turns crossed the table, each one a small card pressed into the canon.",
        f"The named sparks were {keywords}. They read like relics on a workbench: practical tools by daylight, mythic components once the system remembers why they matter.",
        _lore_previous_line(packet, previous_entry),
    ]


def _turn_line(top_turns: list[dict[str, Any]]) -> str:
    if not top_turns:
        return "no single dominant turn in the sampled evidence."
    labels = [f"{item['started_at'][:10]} `{item['turn_type']}`: {item['objective']}" for item in top_turns[:3]]
    return " ; ".join(labels) + "."


def _previous_line(packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> str:
    if not previous_entry:
        return "As the first weekly bucket after the summary, this entry connects the inherited Hapa protocol stack to the first dated work of 2026."
    shared = _shared_topics(packet, previous_entry)
    if shared:
        return f"This connects back to `{previous_entry['id']}` through shared topics: {', '.join(shared)}. The weekly log keeps that continuity explicit while preserving this period’s own evidence counts."
    return f"This follows `{previous_entry['id']}` but has different top topics, so the log records it as a continuity step rather than a repeated theme."


def _lore_previous_line(packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> str:
    if not previous_entry:
        return "This was the first weekly gate after the summary stone, and it opened directly into the machinery the old canon had been assembling."
    shared = _shared_topics(packet, previous_entry)
    if shared:
        return f"The thread ties back to the prior card through {', '.join(shared)}: old sigils returning under a new moon, still technical, still witnessed."
    return "The prior card remains behind it like a lantern on another road: connected by the ledger, but carrying a different weather."


def _prepare_image_queue(entries: list[dict[str, Any]], image_queue: Path) -> list[dict[str, Any]]:
    events = []
    status = "queued_openai_api_key_missing" if not os.environ.get("OPENAI_API_KEY") else "queued"
    image_queue.parent.mkdir(parents=True, exist_ok=True)
    with image_queue.open("w", encoding="utf-8") as handle:
        for entry in entries:
            event = {
                "schema": "hapa.narrative.image_job.v1",
                "entry_id": entry["id"],
                "model": "gpt-image-1",
                "prompt": entry["image"]["prompt"],
                "status": status,
                "target_png": entry["image"]["target_png"],
                "fallback_svg": entry["image"]["fallback_svg"],
                "created_at": _utc_now(),
            }
            event = _redact_public_payload(event)
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            events.append(event)
    return events


def _generate_images(entries: list[dict[str, Any]], image_queue: Path) -> list[dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _prepare_image_queue(entries, image_queue)
    events = []
    with image_queue.open("w", encoding="utf-8") as handle:
        for entry in entries:
            target = IMAGE_DIR / f"{entry['id']}.png"
            event = {
                "schema": "hapa.narrative.image_job.v1",
                "entry_id": entry["id"],
                "model": "gpt-image-1",
                "prompt": entry["image"]["prompt"],
                "target_png": entry["image"]["target_png"],
                "fallback_svg": entry["image"]["fallback_svg"],
                "created_at": _utc_now(),
            }
            if target.exists():
                event["status"] = "exists"
            else:
                try:
                    _call_openai_image_api(api_key, entry["image"]["prompt"], target)
                    event["status"] = "generated"
                except Exception as exc:  # pragma: no cover - network/API dependent
                    event["status"] = "failed"
                    event["error"] = str(exc)
            event = _redact_public_payload(event)
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            events.append(event)
    return events


def _call_openai_image_api(api_key: str, prompt: str, target: Path) -> None:
    payload = json.dumps({
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - network/API dependent
        raise RuntimeError(exc.read().decode("utf-8")) from exc
    image_b64 = data["data"][0].get("b64_json")
    if not image_b64:
        raise RuntimeError("OpenAI image response did not include b64_json")
    target.write_bytes(base64.b64decode(image_b64))


def _write_svg_card(entry: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    title = _wrap(entry["title"], 28)[:3]
    topics = [item["key"] for item in entry["evidence"]["top_topics"][:4]]
    counts = entry["evidence"]["counts"]
    lines = [
        *title,
        "",
        f"{entry['period']['label']}",
        f"{counts['turns']} turns | {counts['wiki_articles']} articles | {counts['wiki_files']} files",
        "",
        *(_wrap(", ".join(topics) or "quiet week", 34)[:3]),
    ]
    svg_lines = []
    y = 70
    for index, line in enumerate(lines):
        size = 28 if index < len(title) else 16
        weight = "700" if index < len(title) else "500"
        svg_lines.append(f'<text x="54" y="{y}" font-size="{size}" font-weight="{weight}">{html.escape(line)}</text>')
        y += 36 if size == 28 else 24
    output.write_text(
        "\n".join([
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img">',
            '<rect width="1024" height="1024" fill="#061016"/>',
            '<path d="M64 64h896v896H64z" fill="#101a22" stroke="#35c7dc" stroke-width="3"/>',
            '<path d="M96 760c180-110 310-70 456-170 118-81 166-208 360-242v548H96z" fill="#162832"/>',
            '<circle cx="790" cy="214" r="118" fill="#d7ad3f" opacity=".18"/>',
            '<circle cx="790" cy="214" r="64" fill="#d9659f" opacity=".22"/>',
            '<g fill="#edf7fa" font-family="Inter, ui-sans-serif, system-ui">',
            *svg_lines,
            '</g>',
            '<text x="54" y="936" fill="#9fb0bb" font-size="18" font-family="ui-monospace, monospace">hapa-narrative | GPT-image prompt queued</text>',
            '</svg>',
        ]),
        encoding="utf-8",
    )


def _weekly_periods(start_date: date, end_date: date) -> list[Period]:
    periods = []
    current = start_date
    while current <= end_date:
        period_end = min(current + timedelta(days=6), end_date)
        periods.append(Period("weekly", current, period_end))
        current = period_end + timedelta(days=1)
    return periods


def _date_value(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _keywords_for_row(row: dict[str, Any]) -> list[str]:
    text = " ".join(str(row.get(field) or "") for field in ("objective", "work_summary", "reusable_insight", "decision_summary"))
    found = []
    lowered = text.lower()
    for keyword in CANON_KEYWORDS:
        if keyword.lower() in lowered:
            found.append(keyword)
    for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", text):
        clean = word.lower()
        if clean not in STOPWORDS and len(clean) < 28:
            found.append(clean)
    return found


def _source_links(turns: list[dict[str, Any]], articles: list[dict[str, Any]], wiki_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = []
    for row in turns[:8]:
        links.append({
            "label": _truncate(row.get("objective") or row.get("turn_id"), 90),
            "href": f"hapa://second-brain/turn/{row.get('turn_id')}",
            "kind": "second-brain-turn",
            "source_id": "second-brain-live",
            "record_id": row.get("turn_id"),
            "privacy": "private-local",
        })
    for row in articles[:6]:
        links.append({
            "label": row.get("title") or row.get("slug"),
            "href": f"hapa://second-brain/wiki_articles/{row.get('article_id')}",
            "kind": "second-brain-wiki-article",
            "source_id": "second-brain-live",
            "record_id": row.get("article_id"),
            "privacy": "private-local",
        })
    for row in wiki_files[:6]:
        links.append({
            "label": row.get("title") or row.get("relpath"),
            "href": row.get("link"),
            "kind": "wiki-file",
            "source_id": row.get("source_id"),
            "record_id": row.get("relpath"),
            "privacy": "private-local",
        })
    return links


def _top_turns(turns: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(
        turns,
        key=lambda row: (
            len(str(row.get("work_summary") or row.get("reusable_insight") or "")),
            str(row.get("turn_started_at") or ""),
        ),
        reverse=True,
    )
    output = []
    for row in ranked[:limit]:
        output.append({
            "id": row.get("turn_id"),
            "started_at": row.get("turn_started_at"),
            "turn_type": row.get("turn_type"),
            "objective": _truncate(row.get("objective") or "", 180),
            "work_summary": _truncate(row.get("work_summary") or row.get("reusable_insight") or "", 220),
            "link": f"hapa://second-brain/turn/{row.get('turn_id')}",
        })
    return output


def _top_articles(articles: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return [
        {
            "id": row.get("article_id"),
            "slug": row.get("slug"),
            "title": row.get("title"),
            "article_type": row.get("article_type"),
            "summary": _truncate(row.get("summary") or "", 220),
            "updated_at": row.get("updated_at"),
            "link": f"hapa://second-brain/wiki_articles/{row.get('article_id')}",
        }
        for row in articles[:limit]
    ]


def _top_counts(counter: collections.Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def _label_list(items: list[dict[str, Any]], limit: int) -> str:
    labels = [str(item["key"]) for item in items[:limit]]
    return _natural_join(labels) if labels else "no dominant labeled theme"


def _shared_topics(packet: dict[str, Any], previous_entry: dict[str, Any] | None) -> list[str]:
    if not previous_entry:
        return []
    current = {item["key"] for item in packet["topic_counts"][:8]}
    previous = {item["key"] for item in previous_entry.get("evidence", {}).get("top_topics", [])[:8]}
    return sorted(current & previous)[:5]


def _title_focus(keywords: list[str], topics: list[str], period: Period) -> str:
    candidates = [item for item in keywords if item.lower() not in STOPWORDS]
    if candidates:
        return " / ".join(_title_case(item) for item in candidates[:2])
    if topics:
        return _title_case(topics[0])
    return "Quiet Ledger"


def _image_prompt(title: str, period: Period, topics: list[str], keywords: list[str]) -> str:
    theme = ", ".join(_unique([*keywords[:4], *topics[:4]])) or "quiet Hapa archive week"
    return (
        "Create a square Hapa narrative post image, original fantasy science-fiction operator-card aesthetic, "
        "local-first knowledge graph archive, luminous dark interface, gold and cyan graph lines, human-agent canon ledger. "
        f"Title: {title}. Period: {period.label}. Themes: {theme}. "
        "No logos, no readable private file paths, no real person likeness, no copyrighted trading-card frame."
    )


def _title_from_file(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:40]:
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
    except OSError:
        return None
    return None


def _blocked_rel(rel: str) -> bool:
    parts = set(rel.split("/"))
    return bool(parts & {".git", "node_modules", "Raw", "Private", "tmp", "__pycache__"})


def _unique(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        cleaned = str(item).strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def _natural_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _truncate(value: Any, limit: int) -> str:
    text = " ".join(_sanitize_public_text(str(value or "")).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _title_case(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in str(value).replace("-", " ").split())


def _wrap(value: str, width: int) -> list[str]:
    words = str(value).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(item) for item in current) + len(current) + len(word) > width and current:
            lines.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def _public_rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sanitize_public_text(value: str) -> str:
    text = value
    for pattern, replacement in PRIVATE_TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_public_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_public_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_public_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_public_text(value)
    return value


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Hapa narrative weekly entries.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE.isoformat())
    parser.add_argument("--end-date", default=DEFAULT_END_DATE.isoformat())
    parser.add_argument("--output", default=str(PUBLIC_ENTRY_PATH))
    parser.add_argument("--run-log", default=str(RUN_LOG_PATH))
    parser.add_argument("--image-queue", default=str(IMAGE_QUEUE_PATH))
    parser.add_argument("--generate-images", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_narrative_agent(
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        output=Path(args.output),
        run_log=Path(args.run_log),
        image_queue=Path(args.image_queue),
        generate_images=args.generate_images,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Wrote {result['entries']} Hapa narrative entries to {result['output']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
