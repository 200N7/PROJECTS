# PLUMB
## How deep does "done" really go?

PLUMB is an evidence-first verification platform for AI-built software. It treats AI completion messages as claims, not proof, and connects verification conclusions to observable evidence.

### What is included
- Secure multi-file ZIP ingestion
- Project/language/framework/dependency discovery
- Requirement + acceptance-criteria extraction
- Requirement-to-implementation mapping
- Implementation-depth model: DETECTED -> IMPLEMENTED -> TESTED -> MEASURED -> VERIFIED
- Deterministic static checks and security checks
- Real Python build/test execution where supported
- Real Node/JS test execution where supported
- Adversarial probes (duplicate, ordering, empty input, type confusion)
- Mutation testing for Python
- Runtime/HTTP worker for a safe local subprocess
- Performance/scaling measurements
- Evidence-first deterministic verdicts
- Session-isolated history with delete/clear
- Interactive analytics: heatmaps, Sankey, treemap, sunburst, force graph, claim/reality, mutation, performance, security, evidence coverage
- Graph-rich professional PDF report

### Honest execution boundary
This build is local-first. Submitted code executes in a subprocess-based worker with timeouts, temporary directories, environment restrictions and resource limits where supported. It is **not Docker-grade isolation**. The report explicitly discloses this.

### Run

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000

### Demo project
A deliberately flawed multi-file Python project is included in `fixtures/flagship_project/` and zipped for convenience at `fixtures/flagship_project.zip`.

### Notes
No paid API is required. AI assistance is optional and not authoritative. The core verifier works without an AI key.

### Release verification
Run `python release_check.py` for a bounded, deterministic release smoke test. It runs the flagship verification on a disposable copy, checks fixture immutability, compiles the application, probes the live health endpoint, verifies server termination, canonicalizes the final PDF, and cleans release artifacts. Run `python verify.py` when you want the flagship analysis/report only.
