#!/usr/bin/env python3
"""Link every use of a defined symbol back to its entry in concepts.md.

A concept entry defines a symbol when its bold title starts with a code span
followed by a comma, e.g.::

    <a id="CON-001"></a>
    ### CON-001

    **`Td`, interval length**

Every standalone use of that symbol in the docs, written as inline code with
nothing else in the code span (`` `Td` ``), becomes a link to the entry:
``[`Td`](concepts.md#CON-001)``. Hovering over it in Obsidian (Page preview)
or following it in any viewer shows the definition.

The script works on the folder it lives in, so copy it into the docs folder.

Left alone:

* code spans that contain more than the symbol, e.g. a formula;
* headings, fenced code blocks, HTML comments, and text that is already a link;
* a symbol inside its own concept entry.

Usage::

    python docs/link_symbols.py           # add missing links in place
    python docs/link_symbols.py --check   # report missing links; exit 1 if any
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
CONCEPTS = DOCS / "concepts.md"

ENTRY = re.compile(r'<a id="(CON-\d{3})"></a>\s*\n#{1,6}[ \t]+\1[ \t]*\n\s*\n\*\*`([^`]+)`,')
ANCHOR = re.compile(r'<a id="([A-Z]+-\d{3})"></a>')
LINK = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
FENCE = re.compile(r"^[ \t]*```")
CODE_SPAN = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)")


def symbols() -> dict[str, str]:
    """Map each defined symbol to the ID of its concept entry."""
    return {symbol: id_ for id_, symbol in ENTRY.findall(CONCEPTS.read_text(encoding="utf-8"))}


def link_line(line: str, table: dict[str, str], prefix: str, own: str | None) -> tuple[str, int]:
    """Link the bare symbols in one line of prose; return the new line and the count."""
    count = 0

    def replace(segment: str) -> str:
        nonlocal count

        def one(match: re.Match[str]) -> str:
            nonlocal count
            fence, content = match.group(1), match.group(2)
            # Only a single-backtick span that is exactly a symbol. Spans with
            # longer fences (used to show code examples) are left alone.
            if fence != "`" or content not in table or table[content] == own:
                return match.group(0)
            count += 1
            return f"[`{content}`]({prefix}#{table[content]})"

        return CODE_SPAN.sub(one, segment)

    out, last = [], 0
    for existing in LINK.finditer(line):
        out.append(replace(line[last : existing.start()]))
        out.append(existing.group(0))
        last = existing.end()
    out.append(replace(line[last:]))
    return "".join(out), count


def link_page(page: Path, table: dict[str, str]) -> tuple[str, int]:
    prefix = "" if page == CONCEPTS else "concepts.md"
    lines = page.read_text(encoding="utf-8").split("\n")
    in_fence = in_comment = False
    own: str | None = None
    total = 0
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment or "<!--" in line:
            in_comment = "-->" not in line
            continue
        anchor = ANCHOR.search(line)
        if anchor:
            own = anchor.group(1) if page == CONCEPTS else None
        if line.lstrip().startswith("#"):
            continue
        lines[i], count = link_line(line, table, prefix, own)
        total += count
    return "\n".join(lines), total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only; exit 1 if links are missing")
    args = parser.parse_args(argv)

    table = symbols()
    if not table:
        print(f"no symbols defined in {CONCEPTS.name}")
        return 0
    missing = 0
    for page in sorted(DOCS.glob("*.md")):
        text, count = link_page(page, table)
        if count:
            missing += count
            print(f"{page.name}: {count} unlinked symbol use(s)")
            if not args.check:
                page.write_text(text, encoding="utf-8")
    symbols_list = ", ".join(f"{s} → {i}" for s, i in table.items())
    if args.check:
        print(f"{'OK' if not missing else f'{missing} unlinked'}: symbols {symbols_list}")
        return 1 if missing else 0
    print(f"linked {missing} use(s) of: {symbols_list}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
