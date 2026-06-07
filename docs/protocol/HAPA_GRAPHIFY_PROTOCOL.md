# Hapa Graphify Protocol

## Purpose

Compile Hapa ecosystem sources into a typed graph projection while preserving source owners, truth status, privacy, and update lineage.

## Required Truth Labels

- `verified_source`: explicitly present in a source file, DB row, board event, or manifest.
- `verified_runtime`: proven by a loopback endpoint, CLI command, or smoke run.
- `derived_or_inferred`: computed or semantic relationship.
- `needs_review`: ambiguous, conflicting, or human-review-required relationship.
- `blocked`: unavailable because of authority, missing source, auth, or external state.

## Ingestion Rule

Every source must be in the source registry before ingestion. Every write-capable command must run dry-run first.

## Append Rule

Incremental updates append new facts and deltas. Deletions are tombstoned until reconcile verifies them.

## Board Rule

Any implementation milestone, blocker, review handoff, validation result, or protocol change must append an event to `hapa-app-hapa-graphify`.

Graph-derived board suggestions are draft-only until a human or authorized agent appends them to the Overwatch event log. Hapa Graphify may read board logs and emit graph fragments, but it must not rewrite historical board events.
