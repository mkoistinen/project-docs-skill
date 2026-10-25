# Writing entries

How to write good entries in each file of the project record. Read this when adding entries; the file templates also show each format in an HTML comment.

## Contents

- [Common rules](#common-rules)
- [goals.md: GOAL-, REQ-, Q-](#goalsmd-goal--req--q-)
- [concepts.md: CON-](#conceptsmd-con-)
- [decisions.md: DEC-](#decisionsmd-dec-)
- [experiments.md: EXP-](#experimentsmd-exp-)
- [findings.md: FND-](#findingsmd-fnd-)
- [open-items.md: OPEN-](#open-itemsmd-open-)
- [README.md: Status and History](#readmemd-status-and-history)
- [Superseding and correcting](#superseding-and-correcting)
- [Diagrams](#diagrams)

## Common rules

- **An anchor line, a heading that is exactly the ID, then the title in bold:**

  ```markdown
  <a id="DEC-012"></a>
  ### DEC-012

  **Detection uses the previous day's model**
  ```

  Both are needed. GitHub, VS Code and MkDocs follow the `<a id>` anchor, but Obsidian ignores HTML anchors and matches `#DEC-012` against heading text (case-insensitively), so the heading must be the bare ID. The checker enforces this. Write the title as a statement, not a topic: "Use half-life to parameterize decay", not "Decay".
- **Next free number.** Never reuse or renumber an ID, even for a withdrawn entry. Gaps break the checker on purpose, so nothing is silently deleted.
- **Link generously.** Within a file, use `[DEC-004](#DEC-004)`. Across files, use `[FND-007](findings.md#FND-007)`. Every entry should link to whatever caused it or depends on it.
- **Be concrete.** Give numbers, versions, file and function names, dates (absolute, never "yesterday"), and who decided. Someone reading this in six months without the chat history must be able to follow it.
- **Record at the moment it happens.** Write the entry in the same task that made the decision or ran the experiment, while the details are at hand. Batching entries for later is how records rot.

## goals.md: GOAL-, REQ-, Q-

- `GOAL-`: an outcome the project must demonstrate or deliver.
- `REQ-`: a constraint any solution must satisfy (latency, size, compatibility, scope).
- `Q-`: an open research or design question the project exists to answer. Unlike an `OPEN-` item, it may take the whole project to answer.

Goals change. When the user restates them, supersede the old entry rather than editing it silently, and add an *Amended YYYY-MM-DD* note with the decision that caused it.

## concepts.md: CON-

A definition: a parameter (symbol, meaning, units, flag), a component, a strategy, a label, or a metric. When the code implements a concept differently from the plan, say so in the entry ("Current code: …"), so readers know which is which.

**Symbols.** When a concept has a short symbol, start its bold title with the symbol in code, followed by a comma:

```markdown
<a id="CON-001"></a>
### CON-001

**`Td`, interval length**
```

`python <docs>/link_symbols.py` then turns every standalone `` `Td` `` in the docs into `` [`Td`](concepts.md#CON-001) ``. Hovering over it in Obsidian (Page preview), or following it anywhere else, shows the definition, which matters most for single-letter symbols that are easy to forget. It leaves alone formulas and other code spans that contain more than the symbol, headings, code blocks, existing links, and a symbol inside its own entry. Run it after writing; `--check` reports missing links without changing anything.

**Interfaces.** If the project has a command line or config file, give it one concept entry with a table of every option, what it sets (linking the concept), its default, and the decision behind the default. Link mentions of "the CLI" to that entry. A project test that compares the table with the real options keeps it honest.

## decisions.md: DEC-

```markdown
<a id="DEC-012"></a>
### DEC-012

**Detection uses the previous day's model**

- **Date:** 2026-10-08 · **Status:** Active · **Source:** project lead
- **Decision:** Each day's data goes to training and detection in parallel; detection scores with yesterday's model.
- **Rationale:** Detection no longer waits for training, and the two can run on separate machines. Supersedes [DEC-009](#DEC-009).
```

- **Source** says who decided: a person ("project lead", a name), or "proposed by Claude" with whether it was accepted. Proposals that still need confirmation get **Status: Proposed**. Flip them to Active when confirmed, and note the date.
- Record decisions that *you* make when they involve a real trade-off (a library choice, a data format, a default value), not trivial ones.
- User corrections are decisions. "No, use X instead" becomes a `DEC-` entry, so the correction outlives the session.

## experiments.md: EXP-

Record **every** run that taught something: benchmarks, probes, test-suite sizing, spikes, and especially failed or stopped runs. These are the most often lost and the most useful later.

- **Setup** must allow a rerun: data sizes, parameters, versions, machine, load (e.g. "run at low priority on a busy machine, so timings are pessimistic").
- **Outcome** gives numbers. Tables work well. State what was surprising.
- **Led to** links the findings, decisions, and open items it produced.

## findings.md: FND-

A fact about the system, a dependency, the data, or the tooling, stated as a sentence in the heading.

- **Confidence:** *Verified* (observed directly or read in source; say where), *Observed once* (a single run), or *Inferred* (reasoned, not tested). Be honest. Upgrade the confidence later, with a link to the experiment that confirmed it.
- When a later experiment refines a finding, add a dated bullet to the existing entry rather than rewriting it.

## open-items.md: OPEN-

Unresolved questions, known problems, missing pieces, and pending work, including questions waiting on the user.

- **Status:** Open, Waiting (say on whom), In progress, Resolved, Dropped.
- When resolving one, keep the entry, set *Resolved YYYY-MM-DD*, and link what settled it.
- Questions you asked the user and are waiting on belong here, so they aren't forgotten when the chat ends.

## README.md: Status and History

- **Status** is a short, current snapshot: what's built, what's next, what's waiting on whom, and the biggest risk. Rewrite it (don't append) whenever the overall state changes, and update its "Last updated" date.
- **History** is an append-only table with one row per milestone or session, linking the IDs involved.

## Superseding and correcting

- **Superseding:** the old entry keeps its text. Its status becomes "Superseded by [DEC-020](#DEC-020)", and the new entry says "Supersedes [DEC-014](#DEC-014)". Current-state pages (Status, concepts, diagrams) should cite the *new* ID.
- **Correcting a mistake** in an entry: fix it, and add a dated note saying what changed if anyone may have relied on the old text.
- **Historical entries stay true to their time.** An experiment run on an old version keeps the old version's numbers. Don't "update" history to match the present.

## Diagrams

If the project has a dataflow or architecture page, keep it in Mermaid inside Markdown (it renders on GitHub, and in VS Code with a Mermaid extension). Label nodes with the IDs they implement. When the code and the plan differ, show both: a "current code" diagram and a "planned" diagram, each labeled as such. After editing, check that the diagram still parses: render it with `npx -y @mermaid-js/mermaid-cli -i in.mmd -o out.png`, writing the output outside the repo.
