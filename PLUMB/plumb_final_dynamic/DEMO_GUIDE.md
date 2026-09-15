# PLUMB Demo Guide

## Goal

Demonstrate the central PLUMB thesis in under two minutes:

**AI says "Done." -> PLUMB checks -> evidence reveals what actually holds.**

## Demo fixture

`fixtures/demo_ai_project.zip`

## Demo inputs

Specification: `fixtures/demo_ai_project/task_spec.txt`  
AI claim: `fixtures/demo_ai_project/ai_claim.txt`

## Suggested sequence

1. Open PLUMB.
2. Upload the ZIP.
3. Provide the specification and AI claim.
4. Start inspection.
5. Show the overview: files, requirements, test state and completion percentages.
6. Open Requirements and point out that the original suite is green.
7. Open Evidence and select the failed filter requirement.
8. Show:
   - Expected: non-matching records excluded.
   - Observed: non-matching record still exported.
9. Select the merge requirement and show the distinct same-title record disappearing.
10. Open Analytics and demonstrate cross-linked requirement selection.
11. Export the PDF and show the completion/remaining dashboard and evidence sections.
12. Open History and reopen the stored verification.

## Key line for the presentation

> A green test suite is not the same thing as verified requirements. PLUMB separates what was claimed from what was observed and what the evidence actually supports.
