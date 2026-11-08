# AI-Assisted Development Workflow

This project was built with a coding agent (Claude Code), supervised by the project owner. This document describes how work was planned, delegated, verified and reviewed, so the process can be repeated and audited.

## 1. Context files

The agent starts every session from these files, in this order:

| File | Role |
|---|---|
| `CLAUDE.md` | Claude Code entry point; imports `AGENTS.md` and adds tool-specific notes (`gh` usage, roles, commit/push rules) |
| `AGENTS.md` | Repository-wide rules for any coding agent: context, stack, commands and non-negotiable rules |
| `_docs/specification.md` | Product requirements: the source of truth. The agent asks before deviating from it. |
| `_docs/process.md` | How one issue moves from start to close (the orchestration) |
| `_docs/roles/*.md` | Developer, Reviewer and QA role instructions |
| GitHub issue | The task itself: goal, description and acceptance criteria |

## 2. From specification to tasks

1. **Specification.** The project owner wrote and consolidated `_docs/specification.md`.
2. **Backlog.** The agent was prompted to break the specification into a backlog. Each task had to be small enough for one session, understandable without reading the others, and written to the template *number, title, goal, two or three sentences of description*. The first task had to be "an empty project with a passing test".
3. **Review.** The owner reviewed the backlog.
4. **Issues.** The agent turned each task into a GitHub issue (#1–#35); issue numbers match the task numbers.
5. **Rules and process.** `AGENTS.md`, `_docs/process.md`, the role files and `CLAUDE.md` were written next, before any code.

Example prompts used:

> Create a backlog with tasks in _docs/tasks.md. Each task should be small enough to finish in one session, and independent enough that I could hand it to someone who has not read the others. […] The first task should be setting up an empty project with a passing test. Don't write code yet.

> Move each task from _docs/tasks.md into a GitHub issue.

> start issue #1

## 3. Per-issue loop (orchestration)

The main agent session acts as orchestrator and moves one issue at a time through the roles (see `_docs/process.md`):

1. **Pick** the lowest open issue whose prerequisites are done and read it (`gh issue view <n>`).
2. **Develop** (`roles/developer.md`):
   - read the relevant specification sections
   - implement the smallest change that meets the issue
   - write tests alongside the code
   - commit regularly, with the issue number in each message
3. **Review** (`roles/reviewer.md`): go over the diff for scope, correctness, the specification's safety rules (no invented point data, generic errors), security and privacy, simplicity and tests.
4. **Verify** (`roles/qa.md`):
   - run lint and all test suites
   - check each acceptance criterion with evidence
   - try the failure paths
   - confirm the change in the running app where relevant: real HTTP calls with real Supabase tokens, Playwright screenshots of the UI at desktop and mobile sizes
5. **Close.**
   - push and wait for CI to pass
   - post the QA checklist (criteria, evidence, CI run link, commit) as an issue comment
   - close the issue

The owner can stop the loop at any time. The agent stops and asks when an issue is unclear, conflicts with the specification, or needs something only the owner can provide, such as cloud accounts, credentials or billable actions.

## 4. Verification practices

- **Tests prove behaviour, not just compilation.** Security tests were checked for real effect. For example, the RLS tests were run once with RLS disabled to confirm they fail, and secret detection was checked against a planted token in a throwaway clone.
- **The AI provider is mocked everywhere.** Unit, API, integration and browser tests use a fake or demo AI, so CI is free and deterministic. A separate opt-in smoke test (`RUN_LIVE_AI=1`) checks real Bedrock.
- **Real infrastructure where it matters.** Database, RLS, authentication and account deletion tests run against a local Supabase stack, in CI as well. Browser tests register a real user and confirm the email through Mailpit.
- **Privacy is tested.** Tests assert that symptom text never reaches logs or error responses.
- **Visual checks.** UI work was compared with the design prototype using Playwright screenshots. Issues found this way were fixed: navigation placement on mobile, and the rating selection lagging behind the click.

## 5. Human responsibilities

The project owner is responsible for:

- reviewing generated code, tests and documentation, especially security-sensitive changes (authentication, RLS, account deletion, secrets) and AI behaviour (prompts, validation)
- choosing the curated source materials and checking image licences
- providing cloud accounts and credentials, and approving anything billable or public (live AI calls, deployments)
- deciding questions the specification leaves open

## 6. Lessons learned

- **Small, self-contained issues kept sessions focused.** Posting a QA checklist on each issue left an audit trail.
- **Checking current library versions mattered.** The backlog assumed tools as they were when the agent's training data ended; several had since changed:
  - TypeScript 7 isn't yet supported by typescript-eslint, so TypeScript is pinned to 6.0.
  - React Router is at v8.
  - Supabase now signs tokens with ES256 and publishes them via JWKS.
  - Some GitHub Actions no longer publish floating major tags.
- **Deterministic fakes need care.** The demo AI's category matching made one browser test pick a different point set than expected. The fix was a clearer test input, not a change to the product code.
- **A destructive git command needs a clean tree.** A `git reset --hard` used for a quick experiment discarded uncommitted work and had to be redone. Experiments now run in throwaway clones.
