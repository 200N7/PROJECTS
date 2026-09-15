# Dynamic Procedural Verification

The verifier now supports bounded multi-step runtime plans in addition to single-request and value-oracle plans.

For specifications that expose a parameterized state/action endpoint and explicit state sequences, PLUMB can discover concrete entities from runtime responses, instantiate the endpoint, execute ordered transitions, observe returned state, check sequence postconditions, and exercise terminal-state rejection. Procedural evidence is authoritative and cannot be downgraded by generic route matching.

Safety invariant: when a multi-step behavior cannot be synthesized safely, the criterion remains INCONCLUSIVE rather than being inferred from endpoint reachability or passing unit tests.
