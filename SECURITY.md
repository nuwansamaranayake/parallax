# Security — Parallax

Parallax reads a team's git, calendar, chat, and CI exhaust. That is exactly the surface that
carries surveillance and injection risk, so the security posture is a design input, not an afterthought.
The baseline is the **OWASP Top 10 for LLM Applications (2025)** and the **NIST AI Risk Management
Framework — Generative AI Profile (NIST AI 600-1)**.

## OWASP LLM Top 10 — controls in Parallax

| ID | Risk | Control in this app |
|---|---|---|
| LLM01 | Prompt injection | Tickets, commit messages, transcripts, and channel text are ingested as **untrusted data, never as instructions**. Content and system instructions travel in separate channels; the Claimed and Observed model parsers treat all retrieved text as data. Red-team injection cases ship in the eval suite. |
| LLM02 | Sensitive information disclosure | Deterministic PII redaction runs before any external model call. Channels are consent-scoped, not PM-fiat; a local-model mode exists for fully private operation so raw workplace text need never leave the boundary. |
| LLM05 | Improper output handling | LLM output is a typed, span/quote-anchored **claim**, not a command or a number. Claims are validated against a schema and pass a deterministic gate before they touch drift math, the ledgers, or a brief. No LLM text is executed or auto-sent. |
| LLM06 | Excessive agency | Parallax **drafts, never sends**. No autonomous outbound messages, no self-executing writes. Anything consequential requires human approval; tools are allowlisted with argument-schema validation and idempotency keys on external writes. |
| LLM08 | Vector/embedding weaknesses | Access-control filtering happens at **retrieval time, deterministically**, before any chunk reaches model context. Post-generation redaction is not treated as an access-control mechanism. |
| LLM09 | Misinformation / overreliance | Numbers come only from deterministic code; the LLM never emits a probability. Forecasts widen priors on thin history and say "low-confidence forecast, N data points" rather than printing a crisp false percentage. Risks without an observable signature are quarantined as speculation. |
| LLM10 | Unbounded consumption | Hard budgets on tokens, tool calls, and loop depth. A runaway extraction or pre-mortem loop is treated as a security incident, not a quirk. |

## NIST AI RMF — Generative AI Profile

The four RMF functions map onto how this repo already operates. **Govern:** the doctrine, this file,
and the ADRs record decisions and rejected alternatives. **Map:** trust boundaries and failure modes
are enumerated per app (see RISKS.md). **Measure:** the replay eval suite scores drift lead time,
forecast calibration, and extraction precision/recall, with red-team injection cases included.
**Manage:** compiled tripwires and human approval keep residual risk observable and gated. Signal
collection is team-visible and aggregate-first by architecture — no individual productivity scoring,
ever — which is how Parallax manages the surveillance risk its own data sources create.

## Secrets

No provider SDK is called directly; all model access flows through the `groundwork` gateway, which
reads `OPENROUTER_API_KEY` from the environment. Secrets live in `.env` (gitignored); `.env.example`
ships with blank keys. The zero-key synthetic demo means a reviewer never needs a real credential to
see the app respond. Every LLM call is logged as a trace (model, version, prompt hash, latency, cost,
claims produced) — never the raw secret.
