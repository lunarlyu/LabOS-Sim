# Cosmos Reason 2 Pending Config

Cosmos Reason 2 was requested for the model suite, with reasoning enabled and
4 fps video sampling according to the provided guidance screenshot.

I did not create a runnable JSON config because the OpenRouter catalog lookup on
2026-06-19 returned no `cosmo` or `cosmos` model IDs. Once an exact API model ID
or endpoint is available, create a config with:

- model: exact Cosmos Reason 2 ID
- reasoning: ON / vendor default reasoning flag enabled
- media sampling: 4 fps if direct video is supported
- otherwise: a Cosmos-specific official visual input format, not the generic
  contact-sheet fallback unless that is the recommended provider path
