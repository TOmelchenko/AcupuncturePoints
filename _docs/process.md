# Development Process

- Tasks are GitHub issues, one at a time.
- Read the acceptance criteria before starting and before closing.
- Commit regularly.

## Orchestration

The orchestrator (the main agent session, supervised by the project owner) moves one issue through the roles in `_docs/roles/`. Each role starts from the issue and the repository, not from the other roles' conversations.

1. **Pick** the next open issue (lowest number whose prerequisites are done) and read it with `gh issue view <n>`.
2. **Develop** — hand the issue to the Developer (`developer.md`). The Developer implements it, commits regularly and reports what changed.
3. **Review** — hand the diff to the Reviewer (`reviewer.md`). If changes are needed, return the findings to the Developer and review again.
4. **Verify** — hand the issue to QA (`qa.md`), who checks each acceptance criterion with evidence. Failing items go back to the Developer, then through Review and QA again.
5. **Close** — when QA passes, push the commits, post the QA checklist as an issue comment and close the issue.
6. **Repeat** with the next issue.

### Rules

- Only one issue is in progress at a time.
- Handoffs carry the issue number and a short summary; the receiving role reads the issue and code itself.
- Stop and ask the project owner when an issue is unclear, conflicts with the specification, or cannot pass review/QA after two rounds.
- The project owner reviews security-sensitive changes and decides on anything the specification leaves open.
