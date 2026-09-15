# PLUMB Adaptive Verification Planner — Final Architecture

PLUMB no longer treats requirement verification as an endpoint-name rule table. The verification core follows a project-specific planning loop:

1. **Discover** executable surfaces, literal source-of-truth data, tests, build targets, static findings and runtime routes from the submitted snapshot.
2. **Interpret** each acceptance criterion as a proposition and align it with discovered project entities using domain-neutral structural/lexical similarity. Exact paths dominate semantic similarity.
3. **Synthesize an oracle** only when independent truth can be deterministically derived from the submitted snapshot. Generic mathematical primitives (count, sum, mean), categorical filters, explicit JSON key/value expectations and executable tests are supported without project/domain allowlists.
4. **Execute** the generated experiment against the submitted software.
5. **Judge from evidence**. Capability existence, value correctness and aggregate runtime claims are separate propositions. When an oracle cannot be established safely, correctness remains INCONCLUSIVE rather than being guessed.
6. **Persist provenance** through the relational evidence model so a verdict can be traced back to the exact observation that supported or contradicted it.

Deterministic security scanners, compilers and test runners remain tools in the verifier. They are intentionally deterministic checks, not the reasoning/planning layer. Removing deterministic checks would make the product less trustworthy, not more dynamic.

## Safety invariant

Dynamic planning may choose *what experiment to run*. It may never fabricate the result. VERIFIED/FAILED requires recorded deterministic evidence; otherwise PLUMB reports INCONCLUSIVE or UNSUPPORTED.

## Final adaptive-planner hardening

The planner now uses two-phase grounding: it first aligns requirements to discovered project capabilities, then uses the observed response schema only to ground ambiguous field names before independently computing expected values from submitted source data. Response values are never reused as expected truth. Boolean predicates are inferred from discovered boolean fields, adjacent capability/behavior requirements are composed structurally, and explicit route propositions cannot borrow an oracle from a merely similar neighboring requirement. Requirement-level evidence is bound to the same executed oracle used by the runtime probe, preventing contradictory VERIFIED/FAILED states.
