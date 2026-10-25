---
name: "project-docs"
description: "Set up and maintain an ID-based project record in docs/ — goals, concepts, a decision log, an experiment log, findings and open items, each entry with a permanent citable ID (DEC-007, EXP-003, ...), interlinked, with a Status/History index, an optional Mermaid dataflow page, a CLAUDE.md standing rule that keeps it current, a stdlib-only checker for duplicate IDs and broken links, and a dependency-graph dashboard (dashboard.html) drawn from explicit Depends on lines. Use this whenever the user wants to \"get organized\", document goals/decisions/what was tried and its outcome, start a decision log or lab notebook or ADRs, keep notes Claude must maintain across sessions, see the record as a DAG or dashboard, or asks how to get \"docs like these\" in another project — and whenever a project already has a docs/ record with PREFIX-NNN IDs that needs a decision, experiment, finding or open item recorded. Not for API reference docs, docstrings, or end-user manuals."
---

# Project record (project-docs)

A project record is a small set of interlinked Markdown files that capture **why** a project is the way it is:

- what it's trying to achieve;
- what was decided, by whom, and why;
- what was tried and what happened;
- what was learned;
- what is still open.

Every entry has a permanent ID, so people and code can cite it ("see DEC-014"), and the record survives the end of any chat session.

It works because of four habits. Use them in every project that has a record:

1. **Typed entries with permanent IDs:** `GOAL-`, `REQ-`, `Q-`, `CON-`, `DEC-`, `EXP-`, `FND-`, `OPEN-`, never renumbered or reused. Superseded entries stay in place and point to their replacement, so history is never lost and citations never break.
2. **Write as you go.** An entry is written in the same task that produced it, while the numbers and reasoning are at hand. A task isn't done until its entries are written.
3. **A mechanical check.** `check_docs.py` catches duplicate IDs, numbering gaps, headings that aren't the bare ID, citations of undefined IDs, and broken links or anchors. It's the part that is enforced rather than remembered.
4. **Explicit dependencies.** Each entry that builds on others says so in a `- **Depends on:**` bullet. `build_dashboard.py` turns those into a left-to-right dependency graph (`dashboard.html`), so the user can see what blocks what without opening Obsidian.

## Decide which situation you're in

- **No record yet** (no `docs/README.md` with ID rules): set one up (below).
- **A record exists**: maintain it. Read its `README.md` first for Status and conventions, then follow [Maintaining the record](#maintaining-the-record). Match the project's existing prefixes and style, even if they differ from these defaults.
- **A record exists but has no dashboard, and the user wants a DAG or dashboard view**: follow [Dependency-graph dashboard](#dependency-graph-dashboard).
- **The user wants to know how this works, or wants it elsewhere**: explain it, and offer to set it up.

## Setting up a record

1. **Pick the location.** The default is `docs/`. If `docs/` already holds something else (API docs, a site), use a subfolder such as `docs/record/` and say so.
2. **Run the scaffold script.** It never overwrites existing files:

   ```bash
   python3 <skill-dir>/scripts/scaffold.py <project-root> --project "<Name>" [--docs docs] [--no-dataflow] [--instructions CLAUDE.md]
   ```

   It creates:
   - the docs files from `assets/templates/`;
   - copies of the checker, the symbol linker and the dashboard builder at `<docs>/check_docs.py`, `<docs>/link_symbols.py` and `<docs>/build_dashboard.py`, so collaborators without this skill can run them;
   - a "Project record" section in `CLAUDE.md`, between `project-docs` markers, including the `Depends on` rule and the dashboard rebuild step. It creates the file if needed. Pass `--instructions AGENTS.md` for projects that use that file.

   Use `--no-dataflow` for projects with no meaningful pipeline or architecture to draw.
3. **Seed it from what you already know.** Use the conversation, the README and the code:
   - Write the goals, requirements and scope into `goals.md`.
   - Write the decisions already made, with rationale, into `decisions.md`.
   - Write known open questions into `open-items.md`.
   - Fill in the README's Status.

   A record that starts empty tends to stay empty, so seed what you can. But don't invent history. If something's origin is unknown, say so, or ask.
4. **If there's a pipeline,** draw the dataflow page in Mermaid, labeling nodes with the IDs they implement.
5. **Give each seeded entry its `Depends on` bullet** (see [Writing `Depends on` lines](#writing-depends-on-lines)), and show the user the dependency choices for review.
6. **Link symbols, then run the checker:** `python3 <docs>/link_symbols.py`, then `python3 <docs>/check_docs.py --docs <docs>`. Fix anything the checker reports. Then build the dashboard.
7. **Optional, for Python projects with pytest:** add a test that runs the checker, so the record is checked with the test suite:

   ```python
   import subprocess, sys
   def test_project_record_is_consistent():
       result = subprocess.run([sys.executable, "docs/check_docs.py", "--docs", "docs"], capture_output=True, text=True)
       assert result.returncode == 0, result.stdout
   ```

When you report back, list the files created and the IDs you seeded, and point the user to `docs/README.md` and `dashboard.html`.

## Maintaining the record

The standing rule in CLAUDE.md is the contract. In short:

| When this happens | Write |
| --- | --- |
| A decision is made (by the user, or proposed by you and accepted), including user corrections | `DEC-` (date, status, source, decision, rationale) |
| Something is run, including failed or stopped runs | `EXP-` (purpose, setup, versions, outcome numbers, what it led to) |
| A fact is learned | `FND-` (with confidence: Verified / Observed once / Inferred, and evidence) |
| A question is raised or settled | `OPEN-` (resolved items stay, marked Resolved with a link) |
| Goals or scope change | `GOAL-` / `REQ-` / `Q-` (supersede rather than rewrite) |
| A symbol or option is introduced | a `CON-` entry; a symbol's bold title starts with it in code (`` **`N`, trainee size** ``) so `link_symbols.py` can link every use |
| An entry is added, or what it builds on changes | its `- **Depends on:**` bullet, straight after the bold title |
| Code changes what a doc describes | update the concepts and the diagrams |
| The overall state changes | README **Status** (rewrite) and **History** (append a row) |

Before writing entries, read `references/conventions.md` for the formats, good examples, and how to supersede, correct, and keep history honest. The templates also show each format in an HTML comment at the top of each file.

**Obsidian-friendly links.** Many users read the record in Obsidian. Link between files with relative `.md` links, and link to entries only through their bare-ID headings (`decisions.md#DEC-007`). Don't link to other headings by slug (`#status`, `#source-documents`): Obsidian matches heading text, not slugs, so name the section in plain text instead. Don't link out of the vault (e.g. `../documents/...`); name such files in inline code. Note that `check_docs.py` reads link syntax even inside inline code, so write example links as bare targets (`decisions.md#DEC-003`), not as `[x](y)`.

**End of every task that touched the record:** run `link_symbols.py`, then the checker, fix what it reports, then rebuild the dashboard if the project has one. Name the IDs you added or changed in your reply. That gives the user a one-line audit trail and a chance to correct you.

## Dependency-graph dashboard

`build_dashboard.py` (stdlib only) reads every entry in `<docs>/*.md` and writes one self-contained, offline `dashboard.html` at the project root: each entry is a card, placed left to right by dependency depth (foundations on the left, goals on the right), joined by orthogonal arrows.

### Installing it in a project

**New records:** `scaffold.py` already copies the builder, and its templates, README and CLAUDE.md section already include the `Depends on` convention and the rebuild step.

**Existing records without a dashboard:** run `scaffold.py` again with the same `--docs`. It only adds missing files, so it copies `build_dashboard.py` and leaves everything else alone. Then do by hand what it skips:

1. Add a placeholder line to each file's entry template (inside the HTML comment), straight after the bold title: `- **Depends on:** links to the IDs this entry builds on (optional; drives the dashboard's arrows).` For goals.md and concepts.md, whose templates are prose, add a sentence saying the body may start with a `- **Depends on:**` bullet.
2. Add to the project's CLAUDE.md section (scaffold skips it when the markers already exist):
   - a table row: "An entry is added, or what it builds on changes → give it a `- **Depends on:**` bullet straight after its title, linking the IDs it builds on. This drives the arrows in `dashboard.html`."
   - in the end-of-task checklist, after the checker: "Then run `python <docs>/build_dashboard.py` to regenerate `dashboard.html`." If the user's shell runs in UTC (for example a sandboxed VM), add `--tz <their IANA zone>` so the build stamp is in their time.
3. Mention `dashboard.html` and the rebuild command in the README's documents section, and record the dashboard as a `DEC-` entry.
4. Add `Depends on` bullets to the existing entries.

### Writing `Depends on` lines

- Format: `- **Depends on:** [OPEN-001](open-items.md#OPEN-001), [FND-005](#FND-005)`. Same-file links use `#ID`; other files use `file.md#ID`. Put it as the first bullet after the bold title. If the body that follows is a paragraph, leave a blank line after the bullet.
- Direction: list the entries this one **builds on**: the inputs that must be known or done first. A finding derived from a document depends on the open item that requested it. A question depends on the data, findings and concepts it needs. A goal depends on its questions and requirements. An open item that waits on other items depends on them.
- Plain citations are not dependencies. An entry often mentions items it *feeds* or partly answers; those are not in its `Depends on` line, because they belong in the other entry's line. Choose the direction deliberately, keep the graph acyclic (the builder stops on a cycle), and show the user the choices for review the first time.
- When adding Depends on lines to an existing record with a script, make sure the pattern can't match the entry templates inside HTML comments.

### Due dates

An entry with a deadline gets `- **Due:** YYYY-MM-DD · why` straight after its `Depends on` bullet (or after the title if it has none). Use it for real deadlines: a filing date, a payroll cutoff, a window that closes. The dashboard compares the date with the day the page is opened, so the colors stay current without a rebuild.

### What the dashboard does (keep these when changing the builder)

- **Layout:** column = longest dependency path. Entries with no dependencies are pulled right, next to their first consumer, so arrows stay short. Rows are ordered by barycenter sweeps to reduce crossings, and isolated entries sink to the bottom. The left column is labeled Foundations and the right one Goals.
- **Cards:** ID, type, title (two lines), and a status pill. The left border is colored by state: green for done (Resolved, Active, Verified, Defined), amber for pending (Waiting, Open, Proposed, Inferred, Partly verified, Unanswered), blue for goals and requirements, and grey for muted (Superseded, Dropped). Cards show "N inputs pending", and goals and questions show "x/y inputs settled". Finding confidence comes from the first sentence of its Confidence field: "Partly verified" if the field mixes Verified and Inferred without starting with Verified.
- **Arrow routing** (the user's rules):
  - Arrows FROM the same card share one path until they diverge: one exit port per card, and one vertical trunk per source in each gap. Each target card has its own entry ports and arrowheads.
  - Paths favor the middle of the gap between columns, or of the space between rows, and build outward from there (center, +1, -1, +2, -2 …). The longest trunks claim the middle first.
  - An arrow that must cross a column runs through the space between rows, reusing its source's existing channel where possible.
  - A horizontal run that crosses another source's vertical run draws a small hop.
  - Arrows from unsettled cards are faint amber, and the rest are grey. No dashed lines: they break up shared trunks and hops.
- **Interaction:**
  - Hovering a card highlights its upstream and downstream lineage and dims the rest.
  - Hovering a line highlights that connection: the line, and the two cards it joins. Every line within 5 px of the pointer counts, so a shared trunk lights all the branches that run along it. A label by the cursor reads `SRC → TGT, TGT`.
  - Clicking a card opens a panel on the right, below the header, with the type and file, status pills, "Depends on (n)" and "Used by (n)" lists (ID, title, status, each clickable), and the full entry rendered from Markdown.
  - Clicking another card replaces the panel's contents. Clicking anything that is not a card or the panel closes it, as do the panel's ✕ and Escape.
  - The open panel casts a shadow on its left edge, stronger in dark mode, and the graph gains extra scroll room equal to the panel's width, so any card the panel covers can be scrolled clear.
  - The header has summary counts (total cards, then each group's total with its breakdown, so new entries show at a glance), a legend, a search box, a Status button that shows the README's Status section, and a System / Light / Dark switch stored in localStorage.
- **Focus mode:**
  - Focusing a card shows only that card, everything it depends on (all the way down), and its direct users faded as context. The layout is recomputed for just those cards, in the page, with the same algorithm.
  - Controls: a ◎ icon on card hover; a Focus / Unfocus button in the panel; and a focus bar under the header with removable chips, an "Add a card…" box, and Exit. The header's "Unsettled only" switch also applies inside a focus: it hides settled inputs and joins the arrows across them.
  - Several cards: in the full map, Shift-click ◎ *picks* cards without filtering anything (amber ◎, and a "Picked" bar with Focus on N cards / Clear). Then "Focus on N cards" or a plain ◎ shows the union of their chains. Picking comes first because, once one card is focused, the visible cards are already in its chain and the rest are hidden. Inside a focus, Shift-click ◎ adds a visible card (useful on the faded direct users), and "Add a card…" adds any card.
  - The focus lives in the address (`#focus=ID,ID&only=unsettled&card=ID`), so it survives reloads and rebuilds.
- **Unsettled only:** a header switch, available with or without a focus. On the full map it hides every settled card (done, verified, superseded), joins the arrows across them, and shows "(N of total)". Jumping to a hidden card turns it off. It is kept in the address as `only=unsettled`.
- **Due dates:** a card with a `Due` line shows "Due Mon D" in place of its type. Unsettled cards are tinted by how close the date is: red within 30 days or overdue (with a red outline), orange within 60, amber within 90. Settled cards show "Was due" untinted. The panel shows the date, the days left, and the reason. A "Due soon (N)" header button focuses on every unsettled card due within 90 days.
  - Esc closes the panel first, then exits focus, then clears picks. Opening a card that isn't in view leaves focus.
- **Title:** `<README heading> Map` by default, or `--title`.

### Checking it

After building, open the page in a headless browser if one is available (Playwright with Chromium). Confirm there are no page errors and that the card count matches the build output. When the builder itself changed, also check: click a card (panel opens), click another (panel replaced), click empty space and the header (closed), the ✕ (closed), a related item in the panel (jumps), all three color modes, and hovering a single line and a shared trunk. For focus: ◎ (focus and toggle off), Shift-◎ picking in the full map then Focus (union), "Add a card…", Unsettled only, removing a chip, the panel's Focus button (the panel stays open), reload (focus restored), and Esc twice. Look at a full-page screenshot for overlapping or ambiguous lines.

## Why these choices

- **IDs instead of headings for links:** titles get reworded, and IDs don't. Each entry is `<a id="DEC-007"></a>`, then `### DEC-007`, then the title in bold. The anchor serves GitHub, VS Code and MkDocs. The bare-ID heading serves Obsidian, which ignores HTML anchors and matches links against heading text. The cost is that outlines show IDs without titles.
- **Typed files instead of one page per topic:** the questions people ask of a project record are typed. "Why did we decide X?" "What did we try?" "What's still open?" Typed logs answer them directly, and the History table gives the timeline.
- **Superseding instead of editing:** reversals are information. A future reader needs to see that DEC-009 was replaced by DEC-026, and why.
- **Symbols link to their definitions:** single-letter parameters (`N`, `C`, `H`) are easy to forget. A link at every use costs nothing, and a hover preview answers "what was `H` again?" in place.
- **A stdlib-only checker copied into the project:** the record stays checkable on any machine and by anyone, with or without this skill.
- **Explicit `Depends on` lines instead of inferring edges from citations:** citations don't say which way a dependency runs (a finding cites the open item it partly answers, and the open item cites the finding). An explicit line states the direction once, and the graph is only as right as those lines.
- **A generated, self-contained HTML file:** it opens offline in any browser, needs no server or libraries, and is rebuilt from the docs, so it can't drift from them.