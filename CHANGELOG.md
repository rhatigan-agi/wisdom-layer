# Changelog

All notable changes to the Wisdom Layer SDK are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.1] -- 2026-04-27

Patch release — packaging correctness, license-loading clarity, and
dashboard polish. No behavior changes to the cognitive core.

### Fixed

- **`[litellm]` extra packaging.** The extra no longer pulls in
  `sentence-transformers`. `LiteLLMAdapter` routes embeddings through
  `litellm.aembedding`, so the local embedder was never used and only
  bloated the install. Tightened to `litellm>=1.50` to match the
  shipped wheel.
- **`[dashboard]` extra now resolves.** Replaced the placeholder
  `wisdom-layer-dashboard>=1.0` dependency (no such package on PyPI)
  with the real runtime deps: `fastapi>=0.115`,
  `uvicorn[standard]>=0.30`, `websockets>=13`.
- **CLI tools no longer fall back to placeholder license literals.**
  `wisdom-layer-dashboard` and `wisdom-layer-mcp` previously defaulted
  to the strings `"wl_pro_dashboard"` / `"wl_pro_mcp"` when
  `WISDOM_LAYER_LICENSE` was unset; both now default to empty,
  yielding a clean anonymous-Free session.

### Added

- `wisdom-layer-dashboard` console script — `pip install
  "wisdom-layer[dashboard]"` now installs both the dashboard module
  and its launcher.
- New [`docs/dashboard.md`](./docs/dashboard.md) — full launch and
  configuration guide for the web dashboard.
- Quickstart "Setting Your License Key" section explaining that the
  SDK does not auto-load `.env` and showing the three supported
  patterns (shell export, sourced `.env`, `python-dotenv`).
- Troubleshooting entry for "Dashboard runs in anonymous tier even
  though I have a Pro key" (license env var not visible to the
  dashboard process).
- Pro-tier callout on the directives step of the quickstart —
  `directives.add()` and `promote()` require Pro; reading directives
  works on Free.
- LiteLLM example: explicit "`embedding_model=` is required" note,
  chat/embedder pairing table including a local Ollama row, and a
  warning about pointing `embedding_model` at a chat model
  (similarity scores compress).
- Dashboard UI: favicon, plus tier-restriction lock states on the
  cost and trajectory widgets so Free-tier users see a clear gate
  instead of silent empty panels.

### Changed

- Examples and `docs/config.md` standardized on the `backend=` keyword
  in `WisdomAgent(...)`. The legacy `storage=` alias remains
  supported and is documented in the API reference.

---

## [1.0.0] -- 2026-04-25

Initial public release.

The Wisdom Layer SDK gives LLM agents persistent, evolving memory:
multi-tier semantic recall, self-authored behavioral directives,
autonomous reflection cycles, provenance tracking, and cost
visibility. SQLite or PostgreSQL backends; Anthropic, OpenAI,
Gemini, Ollama, and LiteLLM adapters; LangGraph and MCP integrations.

See the [README](./README.md) and [docs](./docs/) for full feature
coverage, quickstarts, and the API reference.
