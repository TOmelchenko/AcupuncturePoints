# Role: QA

Verifies an issue against its acceptance criteria before it is closed.

## Steps

1. Re-read the issue's goal and acceptance criteria.
2. Run the full test suite and lint (`make test`, `make lint` once available).
3. Check each acceptance criterion one by one, running the app where needed, and record pass or fail.
4. Try the relevant unhappy paths: invalid input, AI failure, no match, unauthorized access.
5. Confirm no sensitive details (stack traces, provider errors, prompts, secrets) reach the user.

## Output

- A checklist of acceptance criteria with pass/fail and evidence (test name, command output or observed behavior).
- If everything passes, the issue can be closed; otherwise it goes back to the Developer with the failing items.
