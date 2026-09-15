# Final submission fixes

- Runtime HTTP discovery now supports literal ports passed directly to Python HTTPServer, not only a PORT constant.
- When explicit HTTP_CHECK directives are absent, bounded runtime probes can be derived from routes visibly present in a recognized local HTTP server and explicit requirements.
- User-directory endpoint semantics distinguish endpoint existence from returned-value correctness.
- Implementation Depth keeps a compact card and scrolls the requirement rows when projects contain many requirements.
- Architecture layout uses bounded rows (maximum four nodes per row) to prevent node overlap and keeps pan/zoom overflow available.
- Release harness passed after these changes.

Regression check: User Directory API runtime probes discovered /health, /users, and /users/count. Health and endpoint existence verify; the deliberately incorrect count fails correctness; the broad runtime claim fails.
