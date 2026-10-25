<!-- project-docs:begin -->
## Project record ({{DOCS}}/)

> **Standing rule: keep [{{DOCS}}/]({{DOCS}}/README.md) current as you work.** Any task that makes a decision, runs something, learns something, raises or settles a question, or changes what the docs describe is **not finished** until the matching entry is written. Read [{{DOCS}}/README.md]({{DOCS}}/README.md) first for the current status.

| When this happens | Do this |
| --- | --- |
| A decision is made: by the user, proposed by you and accepted, or an implementation choice with a real trade-off | Add a `DEC-` entry with date, status, source, and rationale. If it replaces an earlier one, mark that one **Superseded by** the new one. |
| Something is run: probe, benchmark, test sizing, experiment, **including failed or stopped runs** | Add an `EXP-` entry with setup, versions, outcome numbers, and what it led to. |
| A fact is learned about the system, its dependencies, the data, or the tooling | Add an `FND-` entry with its confidence (Verified / Observed once / Inferred) and the evidence. |
| A question is raised, or an open item is settled | Add or update an `OPEN-` entry. Resolved items stay, marked **Resolved** with the date and a link to what settled them. |
| The user corrects or redirects something | Record it as a `DEC-` entry (or update the existing one) so the correction outlives this session. |
| Code changes what a doc describes | Update the affected docs and diagrams in the same task. |
| The overall state changes | Update **Status** and **History** in [{{DOCS}}/README.md]({{DOCS}}/README.md). |
| An entry is added, or what it builds on changes | Give it a `- **Depends on:**` bullet straight after its title, linking the IDs it builds on. These drive the arrows in `dashboard.html`. |

Write entries **as things happen**, while the numbers and rationale are at hand. IDs are `PREFIX-NNN`: take the next free number, and never renumber or reuse one. Every entry is an `<a id="DEC-007"></a>` anchor, then a heading that is **exactly the ID** (`### DEC-007`), then the title in bold on its own line. Obsidian only follows links to headings that match exactly, so link to entries by ID and don't link to other headings by slug (such as `#status`). Cite IDs in code comments and messages where they explain *why*.

**End-of-task checklist.** Before reporting a task as done:

1. Did this task make a decision, run anything, learn a fact, or raise or settle a question? Each one needs its entry.
2. Does anything in `{{DOCS}}/` or this file now contradict the code? Fix it.
3. Run `python {{DOCS}}/link_symbols.py` to link new uses of defined symbols to their concept entries, then run `python {{CHECKER}}` and fix anything it reports. Then run `python {{DOCS}}/build_dashboard.py` to regenerate `dashboard.html`.
4. In your reply to the user, name the IDs you added or changed.
<!-- project-docs:end -->
