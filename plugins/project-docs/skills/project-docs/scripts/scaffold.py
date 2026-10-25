#!/usr/bin/env python3
"""Create an ID-based project record in a project, without overwriting anything.

Creates:

* ``<docs>/`` with README.md (index, ID rules, Status, History), goals.md,
  concepts.md, decisions.md, experiments.md, findings.md, open-items.md and,
  unless ``--no-dataflow``, dataflow.md;
* ``<docs>/check_docs.py``, ``<docs>/link_symbols.py`` and ``<docs>/build_dashboard.py``:
  copies of the checker, the symbol linker and the dashboard builder, so
  collaborators without the skill can run them;
* a "Project record" section in CLAUDE.md (created if missing), between
  ``<!-- project-docs:begin -->`` / ``<!-- project-docs:end -->`` markers.

Existing files are never overwritten: they are reported as skipped. The
CLAUDE.md section is only added if its markers are not already there.

Usage::

    python scaffold.py /path/to/project --project "My Project"
    python scaffold.py . --docs docs/record --no-dataflow --instructions AGENTS.md
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "assets" / "templates"
SECTION = SKILL / "assets" / "claude-md-section.md"
CHECKER = SKILL / "scripts" / "check_docs.py"
LINKER = SKILL / "scripts" / "link_symbols.py"
DASHBOARD = SKILL / "scripts" / "build_dashboard.py"
BEGIN = "<!-- project-docs:begin -->"


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="project root")
    parser.add_argument("--project", default=None, help="project name for headings")
    parser.add_argument("--docs", default="docs", help="docs folder, relative to root")
    parser.add_argument("--no-dataflow", action="store_true", help="skip dataflow.md")
    parser.add_argument(
        "--instructions", default="CLAUDE.md", help="instructions file to add the section to"
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    docs = root / args.docs
    checker = f"{args.docs}/check_docs.py"
    values = {
        "PROJECT": args.project or root.name,
        "DATE": date.today().isoformat(),
        "DOCS": args.docs,
        "CHECKER": checker,
        "DATAFLOW_ROW": ""
        if args.no_dataflow
        else "| [dataflow.md](dataflow.md) | Dataflow diagram (Mermaid) of the system | cites the IDs above |\n",
    }

    docs.mkdir(parents=True, exist_ok=True)
    created, updated, skipped = [], [], []
    for template in sorted(TEMPLATES.glob("*.md")):
        if args.no_dataflow and template.name == "dataflow.md":
            continue
        target = docs / template.name
        if target.exists():
            skipped.append(target)
            continue
        target.write_text(render(template.read_text(encoding="utf-8"), values), encoding="utf-8")
        created.append(target)

    for source, target in (
        (CHECKER, root / checker),
        (LINKER, docs / "link_symbols.py"),
        (DASHBOARD, docs / "build_dashboard.py"),
    ):
        if target.exists():
            skipped.append(target)
        else:
            shutil.copyfile(source, target)
            created.append(target)

    instructions = root / args.instructions
    section = render(SECTION.read_text(encoding="utf-8"), values)
    existing = instructions.read_text(encoding="utf-8") if instructions.exists() else ""
    if BEGIN in existing:
        skipped.append(instructions)
    else:
        separator = "\n\n" if existing.strip() else ""
        instructions.write_text(existing.rstrip("\n") + separator + section, encoding="utf-8")
        (updated if existing else created).append(instructions)

    for path in created:
        print(f"created  {path.relative_to(root)}")
    for path in updated:
        print(f"updated  {path.relative_to(root)} (added the project-record section)")
    for path in skipped:
        print(f"skipped  {path.relative_to(root)} (already exists)")
    print(f"\nNext: fill in {args.docs}/goals.md, then run: python {checker}")
    print(f"Build the dependency graph with: python {args.docs}/build_dashboard.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
