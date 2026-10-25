#!/usr/bin/env python3
"""Check an ID-based project record for consistency.

Checks every Markdown file in the docs folder, plus any extra files given
(typically CLAUDE.md or AGENTS.md), for:

* duplicate IDs: the same ``<a id="PREFIX-NNN"></a>`` anchor defined twice;
* entry headings: the heading right after an ID anchor must be exactly the ID
  (e.g. ``### DEC-007``), with the title on the next line. Obsidian follows
  ``#DEC-007`` links only to a heading with that exact text;
* gaps: a prefix whose numbers skip (e.g. DEC-001, DEC-003);
* dangling citations: an ID mentioned anywhere but never defined;
* broken links: a relative link whose file is missing, or whose ``#fragment``
  matches neither an explicit anchor nor a heading in the target file.

HTML comments, fenced code blocks and inline code are ignored, so templates
and examples can show the entry format without defining anything.

Uses only the Python standard library, so it runs anywhere Python 3.9+ does.
Exits 0 when clean and 1 when there are problems, printing each one.

Usage::

    python check_docs.py                       # docs/ plus CLAUDE.md/AGENTS.md if present
    python check_docs.py --docs docs --extra CLAUDE.md README.md
    python check_docs.py --prefixes GOAL REQ Q CON DEC EXP FND OPEN RISK
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_PREFIXES = ("GOAL", "REQ", "Q", "CON", "DEC", "EXP", "FND", "OPEN")
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
LINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.MULTILINE | re.DOTALL)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
ENTRY = re.compile(r'<a id="([^"]+)"></a>\s*\n#{1,6}[ \t]+([^\n]*)')
INLINE_CODE = re.compile(r"`[^`\n]*`")


def slug(heading: str) -> str:
    """GitHub-style anchor for a heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def live(text: str) -> str:
    """Text with HTML comments removed (templates show entry formats in comments)."""
    return COMMENT.sub("", text)


def prose(text: str) -> str:
    """Live text with fenced code blocks and inline code also removed."""
    return INLINE_CODE.sub("", FENCE.sub("", live(text)))


def anchors(path: Path) -> set[str]:
    text = prose(path.read_text(encoding="utf-8"))
    return set(ANCHOR.findall(text)) | {slug(h) for h in HEADING.findall(text)}


def check(docs: Path, extra: list[Path], prefixes: tuple[str, ...]) -> list[str]:
    id_pattern = re.compile(rf"\b(?:{'|'.join(map(re.escape, prefixes))})-\d{{3}}\b")
    pages = sorted(docs.glob("*.md")) + [p for p in extra if p.exists()]
    problems: list[str] = []

    defined: Counter[str] = Counter()
    where: dict[str, list[str]] = {}
    for page in docs.glob("*.md"):
        text = prose(page.read_text(encoding="utf-8"))
        for anchor in ANCHOR.findall(text):
            if id_pattern.fullmatch(anchor):
                defined[anchor] += 1
                where.setdefault(anchor, []).append(page.name)
        for anchor, heading in ENTRY.findall(text):
            if id_pattern.fullmatch(anchor) and heading.strip() != anchor:
                problems.append(
                    f"{page.name}: heading after {anchor} should be exactly '{anchor}' "
                    f"(title on the next line), not '{heading.strip()}'"
                )

    for id_, count in sorted(defined.items()):
        if count > 1:
            problems.append(f"duplicate ID {id_} defined in {', '.join(where[id_])}")

    numbers: dict[str, set[int]] = {}
    for id_ in defined:
        prefix, number = id_.rsplit("-", 1)
        numbers.setdefault(prefix, set()).add(int(number))
    for prefix, used in sorted(numbers.items()):
        missing = sorted(set(range(1, max(used) + 1)) - used)
        if missing:
            listed = ", ".join(f"{prefix}-{n:03d}" for n in missing)
            problems.append(f"gap in {prefix}- numbering: {listed} not defined")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        for id_ in sorted(set(id_pattern.findall(prose(text))) - set(defined)):
            problems.append(f"{page}: cites {id_}, which is not defined")
        for target in LINK.findall(live(text)):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):  # URL, mailto:, etc.
                continue
            path, _, fragment = target.partition("#")
            dest = (page.parent / path).resolve() if path else page
            if not dest.exists():
                problems.append(f"{page}: link to missing file {target}")
            elif fragment and dest.suffix == ".md" and fragment not in anchors(dest):
                problems.append(f"{page}: link to missing anchor {target}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs", type=Path, default=Path("docs"), help="docs folder")
    parser.add_argument(
        "--extra",
        type=Path,
        nargs="*",
        default=[Path("CLAUDE.md"), Path("AGENTS.md")],
        help="other files to check for citations and links",
    )
    parser.add_argument("--prefixes", nargs="+", default=list(DEFAULT_PREFIXES))
    args = parser.parse_args(argv)

    if not args.docs.is_dir():
        print(f"no docs folder at {args.docs}", file=sys.stderr)
        return 1
    problems = check(args.docs, args.extra, tuple(args.prefixes))
    for problem in problems:
        print(problem)
    pages = len(list(args.docs.glob("*.md")))
    print(f"{'OK' if not problems else f'{len(problems)} problem(s)'}: checked {pages} docs page(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
