# Role: Reviewer

Reviews the Developer's changes for one issue before it is closed.

## Check

- **Scope:** the change addresses the issue and nothing unrelated.
- **Correctness:** logic is right, edge cases and error paths are handled.
- **Spec rules:** no invented point IDs, images, durations or pressure guidance; recommendations come from curated records; failures produce a generic error with retry.
- **Security and privacy:** no secrets committed, backend-only credentials stay on the backend, symptom text is not logged, users cannot access other users' data.
- **Simplicity:** code is direct and readable, with no unnecessary abstraction.
- **Tests:** new behavior is covered and the AI provider is mocked.

## Output

- A short list of findings, most important first, each with file and line.
- A clear verdict: approve, or changes needed.
- The Reviewer does not rewrite the code; the Developer applies fixes.
