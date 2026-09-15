# PLUMB - final release status

Product: PLUMB
Tagline: How deep does "done" really go?

## Release state

Submission-ready candidate for the declared local-first hackathon scope.

## Final release verification

- Deterministic bounded release harness: PASS.
- Flagship verification runs on a disposable copy so the shipped fixture is not modified: PASS.
- Flagship verdict: FAILED (expected because the demonstration project intentionally contains defects).
- Acceptance criteria: 7/12 verified (58.3%).
- Implementation depth: 58.1%.
- Submitted fixture tests: 4 passed, 0 failed.
- Security findings: 3 HIGH findings.
- Runtime `/health`: VERIFIED.
- Runtime `/items/count`: FAILED (expected 3, observed 99).
- Scaling: real repeated measurements; reported as observed growth, not a formal Big-O proof.
- Live application health endpoint: PASS.
- Server termination after release smoke test: PASS.
- Final PDF: 10 pages, openable/rendered; page-level visual inspection completed for clipping/overflow and text-integrity checks.
- Final release tree: cleaned of local database, Python caches, pytest caches and bytecode.

## Core capabilities

- Secure multi-file ZIP ingestion with traversal, size, entry-count and symlink protections.
- Project/language/framework/dependency discovery.
- Python AST symbol discovery and JavaScript/TypeScript source discovery.
- Requirement and acceptance-criteria extraction.
- Requirement-to-implementation mapping with multiple implementation items.
- Evidence-backed implementation-depth scoring.
- CLAIMED / DETECTED / OBSERVED / MEASURED / VERIFIED distinction.
- Deterministic verdict generation.
- Real Python compile/test execution where supported.
- Behavioral/adversarial probes.
- Bounded Python mutation testing.
- Deterministic security checks.
- Build/runtime/scaling measurements where supported.
- Local HTTP runtime verification for detected server conventions.
- Session-isolated history with delete and clear.
- Interactive analytics and evidence drill-down.
- Graph-rich professional PDF reporting.
- Optional AI-provider abstraction; AI is not authoritative for verification.

## Known scope boundaries

- Local subprocess execution is not Docker-grade isolation.
- JavaScript/TypeScript execution and mutation depth is less complete than Python.
- Security scanning is a focused deterministic ruleset, not a commercial full-SAST replacement.
- Browser-level visual-regression automation is not part of the reference build.
- Universal arbitrary-project execution and unrestricted dependency installation are outside the reference worker scope.
- AI assistance is optional; the deterministic core works without a paid AI API.

These are documented limitations, not hidden capabilities.

## Release command

```bash
python release_check.py
```

The harness is bounded and deterministic. It verifies a disposable-copy flagship run, fixture immutability, product compilation, live health, server termination and final PDF creation, then cleans release artifacts.
