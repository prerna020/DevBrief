# devbrief-core

Shared models, diff parsing, and code-chunking utilities for DevBrief — an automated code review tool.

This package underpins both DevBrief's AI review engine and its CLI (`devbrief-cli`), so the
`Finding`/`DevBriefConfig` schema they exchange has a single source of truth.

## What's in here

- `devbrief_core.models` — `Finding`, `ParsedFile`, `RetrievedChunk`, `Severity`.
- `devbrief_core.config` — `DevBriefConfig`, the schema for a repo's `.devbrief.yml`.
- `devbrief_core.diff` — `parse_diff()`, turning a unified diff into `ParsedFile`s.
- `devbrief_core.chunking` — `chunk_file()` / `walk_repo()`, used by DevBrief's indexing pipeline.
- `devbrief_core.sandbox` — `SandboxInput`/`SandboxOutput`/`LintResult` for the lint/SAST sidecar.

## Installation

```sh
pip install devbrief-review-core
```

