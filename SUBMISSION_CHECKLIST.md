# PLUMB submission checklist

## Package

- [x] Final source package created.
- [x] No local SQLite database in submission.
- [x] No `__pycache__`, `.pyc`, `.pytest_cache` or transient render files.
- [x] README and demo guide included.
- [x] `.env.example` included; no credentials included.
- [x] Final PDF included.

## Verification

- [x] Flagship project uses intentional real defects.
- [x] Existing fixture tests remain green.
- [x] PLUMB catches functional/runtime/security failures.
- [x] Source fixture remains unchanged after verification.
- [x] Live health endpoint verified.
- [x] Server termination verified.
- [x] PDF generated from verified data.
- [x] PDF rendered and visually checked.
- [x] Release harness terminates within a bounded timeout.

## Honesty boundary

The submission does not claim universal correctness, universal project execution, perfect security, or Docker-grade isolation.
