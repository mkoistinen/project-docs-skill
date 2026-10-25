# {{PROJECT}}: project record

This folder is the record of the project: what we are trying to achieve, the decisions we have made, what we have tried, and what we learned. Start with the Status section below, then follow the IDs.

## Documents

| File | Contains | ID prefix |
| --- | --- | --- |
| [goals.md](goals.md) | Goals, requirements, scope, and the questions the project must answer | `GOAL-`, `REQ-`, `Q-` |
| [concepts.md](concepts.md) | Definitions of terms, parameters, components, and metrics | `CON-` |
| [decisions.md](decisions.md) | Decision log, with rationale and history | `DEC-` |
| [experiments.md](experiments.md) | Everything we ran or tried, with setup and outcome | `EXP-` |
| [findings.md](findings.md) | Facts learned, each with its confidence and evidence | `FND-` |
| [open-items.md](open-items.md) | Unresolved questions, known problems, and pending work | `OPEN-` |
{{DATAFLOW_ROW}}
`dashboard.html`, at the project root, shows every entry as a card in a dependency graph. Open it in a browser, and rebuild it with `python {{DOCS}}/build_dashboard.py` after changing the docs.

## ID rules

- Every goal, requirement, question, concept, decision, experiment, finding, and open item has an ID of the form `PREFIX-NNN`, e.g. `DEC-007`.
- IDs are **permanent**. They are never renumbered or reused, even if the entry is withdrawn.
- When an entry is replaced, it stays in place with status **Superseded by `XXX-NNN`**, and the new entry says **Supersedes `XXX-NNN`**.
- Each entry is an `<a id="DEC-007"></a>` anchor, then a heading that is **exactly the ID** (`### DEC-007`), then the title in bold on the next line. `decisions.md#DEC-007` then links straight to the entry everywhere: GitHub, VS Code and MkDocs follow the anchor, and Obsidian follows the heading.
- Cite IDs anywhere: other docs, code comments, commit messages, chat.
- New entries take the next free number in their file. Record decisions and experiments when they happen, not afterwards.
- Symbols defined in [concepts.md](concepts.md) (entries titled like **`Td`, interval length**) link back to their entry wherever they're used, so hovering shows the definition. `python {{DOCS}}/link_symbols.py` adds missing links; `--check` reports them.
- An entry that builds on others starts its body with a `- **Depends on:**` bullet linking them. Those lines are the dashboard's arrows.
- `python {{CHECKER}}` checks that IDs are unique and gap-free, that entry headings are the bare ID, and that every citation, link, and anchor resolves.

## Status

*Last updated {{DATE}}.*

**Current state:** Project record created; no entries yet.

**Next:** Record the goals ([goals.md](goals.md)).

**Waiting on:** nothing at present.

## History

| Date | Milestone |
| --- | --- |
| {{DATE}} | Project record created. |
