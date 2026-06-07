# ADR 0001: Wrap Upstream Graphify Before Forking

Status: accepted
Date: 2026-06-06

## Context

Upstream Graphify is an active Python package published as `graphifyy`. The reviewed upstream version is `v0.8.33` at commit `4b06fd7bf7e1e407d8acb4dd9a1404e21cf34bce`.

Graphify already provides a strong generic graph compiler:

- tree-sitter code extraction;
- semantic extraction for docs, PDFs, images, media transcripts, and converted formats;
- NetworkX graph building, clustering, analysis, reports, and exports;
- query/path/explain/MCP surfaces;
- multi-assistant skill install behavior.

Hapa needs additional behavior that is outside upstream's product contract:

- source registry and Hapa record owners;
- truth status mapping and provenance;
- private/public boundary enforcement;
- Overwatch board writeback;
- Second Brain and Lance projections;
- Hapa UI/API/CLI/Desktop parity.

## Decision

Start with a wrapper strategy:

1. Pin upstream Graphify as optional dependency `graphifyy==0.8.33`.
2. Keep Hapa-specific code in `hapa_graphify`.
3. Treat upstream modules as an engine adapter behind Hapa interfaces.
4. Do not fork until a concrete upstream change is required and cannot be represented as a wrapper or adapter.
5. Preserve the reviewed commit in docs and source registry metadata.

## Consequences

Benefits:

- Faster start.
- Lower maintenance burden.
- Upstream improvements can be adopted deliberately.
- Hapa privacy/provenance rules stay separate from generic Graphify logic.

Costs:

- Some graph decoration may need conversion from Graphify node-link output.
- Hapa-specific performance constraints may require adapter-level caching.
- API drift must be watched when upgrading `graphifyy`.

## Upgrade Rule

Before upgrading:

1. Clone or fetch the new upstream commit.
2. Run upstream tests or at least compile/import checks.
3. Re-run Hapa fixture tests.
4. Update the source registry reviewed commit.
5. Append an Overwatch checkpoint with old/new versions and validation evidence.
