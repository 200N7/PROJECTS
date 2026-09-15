# Last-minute runtime verification fix

This build generalizes runtime verification beyond the demo fixtures.

- Discovered HTTP routes are probed only when their route/semantic noun is represented in the specification.
- Endpoint existence/capability is evaluated separately from returned-value correctness.
- Literal in-memory collection counts are derived with Python AST and compared to count endpoints.
- Literal monetary record collections are aggregated deterministically from conventional numeric fields (price/amount/value/cost) for explicit total-value correctness requirements.
- A failed value check fails the specific correctness requirement and broad runtime-success requirement without falsely failing endpoint existence.
- Regression check on the independent Product Metrics API produced the intended split: count correct, total-value incorrect, broad runtime claim failed.
- `python release_check.py` passes after the change.
