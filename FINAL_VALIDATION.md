# PLUMB Final Validation

Final deadline-safe verification pass.

## Critical logic fixes
- Runtime HTTP discovery supports supported local Python HTTP servers with deterministic literal ports.
- Endpoint existence/capability is separated from response/value correctness.
- Generic list endpoints can verify endpoint-existence requirements from an observed reachable route.
- Count expectations are derived from literal submitted collections when safely possible.
- Monetary aggregate expectations are derived only from literal submitted records when safely possible.
- Status-qualified aggregates such as "revenue from paid orders" are supported when the literal records expose a status field.
- If a business-value expectation cannot be independently derived, a successful HTTP 200 cannot promote a correctness requirement to VERIFIED; it remains INCONCLUSIVE.
- Broad runtime-success requirements cannot be VERIFIED when a required runtime check fails or when exercised business correctness remains unresolved.
- Verifier capability state remains separate from target observation status.

## Fresh generalization check
Order Summary API (not a flagship fixture):
- health endpoint: VERIFIED
- health correctness: VERIFIED
- orders list endpoint: VERIFIED
- orders count endpoint: VERIFIED
- count=4: VERIFIED
- paid-revenue endpoint: VERIFIED
- paid revenue correctness: FAILED (expected 350.5, observed 400.0)
- compile: VERIFIED
- tests: VERIFIED
- supported secret scan: VERIFIED
- broad runtime correctness: FAILED

## Release validation
- `python -m pytest -q plumb/tests`: passed (4 tests).
- `python release_check.py`: PASSED.
- Flagship fixture immutable.
- Flagship assertions passed.
- Project compilation passed.
- Live health API passed.
- Server termination passed.
- Canonical final PDF generated.
- Release tree cleanup passed.

## Known limitations
PLUMB is intentionally conservative. It does not claim arbitrary business correctness when an expected value cannot be deterministically derived from the submitted specification/source or an explicit executable check. Such cases remain INCONCLUSIVE rather than becoming false positives.

## Final relational persistence upgrade
- Replaced the single-table sqlite persistence implementation with SQLAlchemy 2.x ORM persistence.
- Added normalized tables for analyses, requirements, acceptance criteria, evidence records, evidence links, findings, and capability executions.
- Enabled SQLite WAL, busy timeout, and foreign-key enforcement.
- Kept an immutable JSON analysis snapshot as the canonical historical/report payload so older UI/report contracts remain compatible while normalized records enable reliable querying and provenance.
- Evidence-to-requirement/criterion links are now persisted explicitly, including SUPPORTS vs CONTRADICTS relationship semantics.
- Verified a fresh Order Summary API run persists 12 requirements, 12 criteria, 14 evidence records and 12 evidence links while retaining REQ-008 FAILED and REQ-012 FAILED.
- Added pytest.ini so `python -m pytest` validates PLUMB itself rather than accidentally collecting target fixture test suites outside their intended project roots.
