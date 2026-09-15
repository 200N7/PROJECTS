# PLUMB architecture

PLUMB separates verification from persistence.

1. **Verification engine** (`plumb/app/analyzer.py`) discovers project structure, executes bounded build/tests/runtime/mutation/performance probes, records deterministic observations, maps evidence to acceptance criteria, and resolves verdicts.
2. **Domain snapshot** (`plumb/app/models.py`) is the in-process representation used while a verification run is being assembled.
3. **Relational persistence** (`plumb/app/db.py`) uses SQLAlchemy 2.x over SQLite (WAL + foreign keys). Every run is stored as an immutable JSON snapshot for report/API compatibility and normalized into relational tables for requirements, criteria, evidence, evidence-to-criterion links, findings, and capability executions.
4. **Presentation** uses the stored run snapshot, so History and generated reports do not silently change when verifier rules evolve.

The database can be redirected with `PLUMB_DB_PATH`. The normalized schema is intentionally SQLite/PostgreSQL-friendly; SQLite remains the local-first default.

## Adaptive verification planner

Runtime verification is no longer driven by a list of product-specific endpoint rules. For each analysis PLUMB now:

1. discovers the submitted runtime surface (routes) and literal project data that can act as an independent oracle;
2. converts route names and requirement text into normalized semantic concepts;
3. ranks each requirement against the capabilities actually discovered in that project;
4. constructs a bounded verification plan using generic primitives such as capability existence, count, filtered count, sum, filtered sum, and mean;
5. executes the plan against the submitted application;
6. records the plan, oracle, expected value, observation, and verdict as evidence;
7. returns INCONCLUSIVE rather than guessing when an independent oracle cannot be established.

The planner may decide *what experiment to run*, but only deterministic execution can create VERIFIED or FAILED evidence. Static security/build/test rules remain deterministic tools; they are not used as a substitute for semantic requirement planning.
