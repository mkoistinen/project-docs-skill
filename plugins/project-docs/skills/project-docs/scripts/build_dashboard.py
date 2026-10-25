#!/usr/bin/env python3
"""Build a dependency-graph dashboard (dashboard.html) from the ID-based project record.

Every entry in docs/*.md (GOAL-, REQ-, Q-, CON-, DEC-, EXP-, FND-, OPEN-) becomes a card.
An entry's ``- **Depends on:**`` bullet gives its incoming arrows. Cards are laid out
left to right by dependency depth: foundations on the left, goals on the right.

Uses only the Python standard library. The output is one self-contained HTML file
with no external requests, so it works offline in any browser.

Usage (from the project folder)::

    python docs/build_dashboard.py                  # writes dashboard.html next to docs/
    python docs/build_dashboard.py --out some/where.html
    python docs/build_dashboard.py --tz Europe/London --title "My Project Map"
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

FILES = ["goals.md", "concepts.md", "decisions.md", "experiments.md", "findings.md", "open-items.md"]
PREFIX_ORDER = ["OPEN", "FND", "EXP", "CON", "DEC", "Q", "REQ", "GOAL"]
TYPE_LABEL = {
    "GOAL": "Goal", "REQ": "Requirement", "Q": "Question", "CON": "Concept",
    "DEC": "Decision", "EXP": "Experiment", "FND": "Finding", "OPEN": "Open item",
}
ID_RE = re.compile(r"\b(?:GOAL|REQ|Q|CON|DEC|EXP|FND|OPEN)-\d{3}\b")
ENTRY_RE = re.compile(r'<a id="((?:GOAL|REQ|Q|CON|DEC|EXP|FND|OPEN)-\d{3})"></a>\s*\n#{1,6}[^\n]*\n')
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


# ---------------------------------------------------------------- Markdown (small subset)

def inline(text: str) -> str:
    out = []
    for part in re.split(r"(`[^`\n]+`)", text):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + html.escape(part[1:-1], quote=False) + "</code>")
            continue
        pieces, pos = [], 0
        for m in LINK_RE.finditer(part):
            pieces.append(_fmt(html.escape(part[pos:m.start()], quote=False)))
            label, url = _fmt(html.escape(m.group(1), quote=False)), m.group(2)
            frag = url.partition("#")[2]
            if re.match(r"https?://", url):
                pieces.append(f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{label}</a>')
            elif ID_RE.fullmatch(frag):
                pieces.append(f'<a href="#" class="idlink" data-goto="{frag}">{label}</a>')
            else:
                pieces.append(label)
            pos = m.end()
        pieces.append(_fmt(html.escape(part[pos:], quote=False)))
        out.append("".join(pieces))
    return "".join(out)


def _fmt(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*\n]+?)\*(?![*\w])", r"<em>\1</em>", s)
    return s


def render(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush(); i += 1; continue
        if line.lstrip().startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            t = ["<table>"]
            for n, r in enumerate(body):
                tag = "th" if n == 0 else "td"
                t.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in r) + "</tr>")
            t.append("</table>")
            out.append("".join(t))
            continue
        if line.startswith(">"):
            flush()
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i].lstrip(">").strip()); i += 1
            out.append("<blockquote>" + inline(" ".join(q)) + "</blockquote>")
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush()
            stack: list[list] = []  # [indent, tag]
            while i < len(lines):
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not m:
                    # continuation line of the previous item
                    if lines[i].strip() and lines[i].startswith("  ") and stack:
                        out.append(" " + inline(lines[i].strip())); i += 1; continue
                    break
                ind, tag, text = len(m.group(1)), ("ol" if m.group(2)[0].isdigit() else "ul"), m.group(3)
                while stack and ind < stack[-1][0]:
                    out.append(f"</li></{stack.pop()[1]}>")
                if not stack or ind > stack[-1][0]:
                    out.append(f"<{tag}><li>")
                    stack.append([ind, tag])
                else:
                    out.append("</li><li>")
                out.append(inline(text))
                i += 1
            while stack:
                out.append(f"</li></{stack.pop()[1]}>")
            continue
        if line.startswith("#"):
            flush()
            out.append("<h4>" + inline(line.lstrip("#").strip()) + "</h4>")
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush()
    return "".join(out)


def plain(md: str) -> str:
    return re.sub(r"[*`]", "", LINK_RE.sub(r"\1", md)).strip()


# ---------------------------------------------------------------- Parsing

def field(body: str, name: str) -> str:
    m = re.search(r"\*\*" + name + r":\*\*\s*([^·\n]+)", body)
    return plain(m.group(1)) if m else ""


def classify(prefix: str, body: str) -> tuple[str, str]:
    """Return (state, label). state is one of done, pending, muted, neutral."""
    if prefix == "GOAL":
        return "neutral", "Goal"
    if prefix == "REQ":
        return "neutral", "Requirement"
    if prefix == "CON":
        return "done", "Defined"
    if prefix == "Q":
        return "pending", "Unanswered"
    if prefix == "FND":
        conf = field(body, "Confidence")
        first = conf.split(". ")[0]
        hits = [(first.find(k), k) for k in ("Verified", "Observed once", "Inferred") if k in first]
        key = min(hits)[1] if hits else "Unrated"
        if key == "Verified" and "Inferred" in conf and not conf.startswith("Verified"):
            return "pending", "Partly verified"
        return ("done" if key == "Verified" else "pending"), key
    status = field(body, "Status")
    m = re.match(r"(\w+(?: \([^)]*\))?)", status)
    label = m.group(1) if m else (status or "No status")
    word = label.split()[0] if label else ""
    if prefix == "OPEN":
        state = {"Resolved": "done", "Dropped": "muted"}.get(word, "pending")
    elif prefix == "DEC":
        state = {"Active": "done", "Proposed": "pending"}.get(word, "muted")
    else:  # EXP
        state = {"Complete": "done", "Failed": "muted", "Stopped": "muted"}.get(word, "pending")
    return state, label


def parse(docs: Path) -> list[dict]:
    nodes = []
    for name in FILES:
        path = docs / name
        if not path.exists():
            continue
        text = COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        matches = list(ENTRY_RE.finditer(text))
        for k, m in enumerate(matches):
            end = matches[k + 1].start() if k + 1 < len(matches) else len(text)
            chunk = text[m.end():end]
            sec = re.search(r"^#{1,2} ", chunk, re.MULTILINE)  # a new ## section ends the entry
            if sec:
                chunk = chunk[:sec.start()]
            chunk = chunk.strip("\n")
            title_m = re.match(r"\*\*(.+?)\*\*\s*\n?", chunk)
            title = plain(title_m.group(1)) if title_m else m.group(1)
            body = chunk[title_m.end():] if title_m else chunk
            deps = []
            dm = re.search(r"^- \*\*Depends on:\*\*(.*)$", body, re.MULTILINE)
            if dm:
                deps = ID_RE.findall(dm.group(1))
                body = body[:dm.start()] + body[dm.end() + 1:]
            eid = m.group(1)
            prefix = eid.split("-")[0]
            state, label = classify(prefix, body)
            nodes.append({
                "id": eid, "prefix": prefix, "type": TYPE_LABEL[prefix], "num": int(eid.split("-")[1]),
                "title": title, "file": name, "state": state, "label": label,
                "deps": list(dict.fromkeys(deps)), "html": render(body.strip()),
                "text": plain(body)[:4000],
            })
    return nodes


# ---------------------------------------------------------------- Layout

def layout(nodes: list[dict]) -> list[str]:
    """Assign col (dependency depth) and row (order within column). Returns warnings."""
    warnings = []
    by_id = {n["id"]: n for n in nodes}
    for n in nodes:
        missing = [d for d in n["deps"] if d not in by_id]
        for d in missing:
            warnings.append(f"{n['id']} depends on {d}, which is not defined")
        n["deps"] = [d for d in n["deps"] if d in by_id and d != n["id"]]
    children = {n["id"]: [] for n in nodes}
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])

    col: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(i: str) -> int:
        if i in col:
            return col[i]
        if i in visiting:
            raise SystemExit(f"dependency cycle involving {i}")
        visiting.add(i)
        col[i] = 1 + max((depth(d) for d in by_id[i]["deps"]), default=-1)
        visiting.discard(i)
        return col[i]

    for n in nodes:
        depth(n["id"])
    # Pull sources rightward, next to their first consumer, so arrows stay short.
    for n in nodes:
        if not n["deps"] and children[n["id"]]:
            col[n["id"]] = max(0, min(col[c] for c in children[n["id"]]) - 1)

    def key(n):
        return (PREFIX_ORDER.index(n["prefix"]), n["num"])

    ncols = max(col.values(), default=0) + 1
    cols = [sorted([n for n in nodes if col[n["id"]] == c], key=key) for c in range(ncols)]
    for n in nodes:
        n["col"] = col[n["id"]]

    def bary(n, pos, neighbours):
        ps = [pos[x] for x in neighbours if x in pos]
        return sum(ps) / len(ps) if ps else None

    for _ in range(12):
        for direction in (1, -1):
            pos = {n["id"]: r for c in cols for r, n in enumerate(c)}
            order = range(1, ncols) if direction == 1 else range(ncols - 2, -1, -1)
            for c in order:
                scored = []
                for r, n in enumerate(cols[c]):
                    nb = n["deps"] if direction == 1 else children[n["id"]]
                    b = bary(n, pos, nb)
                    loner = not n["deps"] and not children[n["id"]]
                    scored.append((1 if loner else 0, b if b is not None else r, r, n))
                scored.sort(key=lambda s: (s[0], s[1], s[2]))
                cols[c] = [s[3] for s in scored]
                for r, n in enumerate(cols[c]):
                    pos[n["id"]] = r
    for c in cols:
        for r, n in enumerate(c):
            n["row"] = r
    return warnings


# ---------------------------------------------------------------- Status block from README

def readme_status(docs: Path) -> str:
    p = docs / "README.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    m = re.search(r"^## Status\s*\n(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    return render(m.group(1).strip()) if m else ""


# ---------------------------------------------------------------- Output

def _now(tz: str | None):
    """Build time, in the given IANA zone if any (a sandboxed shell may run in UTC)."""
    if tz:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz))
        except Exception:
            print(f"warning: unknown time zone {tz!r}; using local time", file=sys.stderr)
    return datetime.now().astimezone()


def default_title(docs: Path) -> str:
    """'<Name> Map' from the README's first heading ('# <Name>: project record')."""
    p = docs / "README.md"
    if p.exists():
        m = re.search(r"^# (.+)$", p.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            name = re.sub(r"\s*[:\u2014-]\s*project record\s*$", "", m.group(1).strip(), flags=re.I)
            return f"{name} Map"
    return "Project Map"


def build(docs: Path, out: Path, title: str | None = None, tz: str | None = None) -> int:
    nodes = parse(docs)
    warnings = layout(nodes)
    data = {
        "nodes": nodes,
        "status": readme_status(docs),
        "built": _now(tz).strftime("%Y-%m-%d %H:%M %Z"),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__TITLE__", html.escape(title or default_title(docs)))
    out.write_text(page.replace("/*__DATA__*/null", payload), encoding="utf-8")
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    edges = sum(len(n["deps"]) for n in nodes)
    print(f"wrote {out} ({len(nodes)} cards, {edges} arrows)")
    return 1 if warnings else 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --card:#ffffff; --line:#d5d9e0; --text:#1d2330; --muted:#667085;
  --edge:#9aa3b2; --edge-hl:#2f6feb; --done:#1f9d55; --pending:#c98a0c; --muted-c:#98a2b3; --neutral:#2f6feb;
  --bad:#d64545; --chip:#eef1f5; --shadow:0 1px 2px rgba(16,24,40,.06);
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#0d1117; --panel:#161b22; --card:#161b22; --line:#30363d; --text:#e6edf3; --muted:#8b949e;
  --edge:#5b636e; --edge-hl:#58a6ff; --done:#3fb950; --pending:#d29922; --muted-c:#6e7681; --neutral:#58a6ff;
  --bad:#f85149; --chip:#21262d; --shadow:none;
}}
:root[data-theme="dark"]{
  --bg:#0d1117; --panel:#161b22; --card:#161b22; --line:#30363d; --text:#e6edf3; --muted:#8b949e;
  --edge:#5b636e; --edge-hl:#58a6ff; --done:#3fb950; --pending:#d29922; --muted-c:#6e7681; --neutral:#58a6ff;
  --bad:#f85149; --chip:#21262d; --shadow:none;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);
  font:13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
  padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
header h1{font-size:15px;margin:0;font-weight:600}
.stats{display:flex;flex-wrap:wrap;gap:6px 14px;color:var(--muted)}
.stats b{color:var(--text);font-weight:600}
.tools{margin-left:auto;display:flex;gap:8px;align-items:center}
input[type=search]{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;
  padding:5px 8px;width:220px;font:inherit}
button{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:5px 9px;
  font:inherit;cursor:pointer}
.legend{display:flex;gap:12px;color:var(--muted);font-size:12px;align-items:center;flex-wrap:wrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:0}
#wrap{overflow:auto;height:calc(100% - var(--hdr,54px))}
#canvas{position:relative}
svg{position:absolute;left:0;top:0;overflow:visible}
.colhead{position:absolute;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.card{position:absolute;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--muted-c);
  border-radius:6px;padding:8px 10px;cursor:pointer;box-shadow:var(--shadow);transition:opacity .12s}
.card.done{border-left-color:var(--done)} .card.pending{border-left-color:var(--pending)}
.card.neutral{border-left-color:var(--neutral)} .card.muted{border-left-color:var(--muted-c);opacity:.75}
.card .top{display:flex;justify-content:space-between;align-items:baseline;gap:6px}
.card .id{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace}
.card .type{font-size:11px;color:var(--muted)}
.card .title{margin:3px 0 6px;font-weight:600;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;
  -webkit-box-orient:vertical;overflow:hidden}
.pills{display:flex;gap:6px;flex-wrap:wrap}
.pill{font-size:11px;padding:1px 7px;border-radius:10px;background:var(--chip);white-space:nowrap}
.pill.done{color:var(--done)} .pill.pending{color:var(--pending)} .pill.muted{color:var(--muted-c)}
.pill.neutral{color:var(--neutral)} .pill.bad{color:var(--bad)}
.pill::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;
  margin-right:5px;vertical-align:1px}
path.edge{fill:none;stroke:var(--edge);stroke-width:1.3}
path.edge.dashed{stroke-dasharray:4 4}
#canvas.focus .card:not(.hl){opacity:.22}
#canvas.focus path.edge:not(.hl){opacity:.12}
path.edge.hl{stroke:var(--edge-hl);stroke-width:2}
.card.sel{outline:2px solid var(--edge-hl);outline-offset:1px}
.card.nomatch{opacity:.2}
#panel{position:fixed;top:var(--hdr,54px);right:0;width:min(460px,100%);height:calc(100% - var(--hdr,54px));background:var(--panel);
  border-left:1px solid var(--line);z-index:10;overflow:auto;padding:16px 18px 40px;transform:translateX(100%);
  transition:transform .15s}
#panel.open{transform:none;box-shadow:-6px 0 18px -4px rgba(16,24,40,.22)}
:root[data-theme="dark"] #panel.open{box-shadow:-8px 0 24px -2px rgba(0,0,0,.85)}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]) #panel.open{box-shadow:-8px 0 24px -2px rgba(0,0,0,.85)} }
/* While the panel is open, extend the scrollable area by the panel's width so every card can be
   scrolled out from under it, and keep scrollIntoView targets clear of it. */
body.panel-open #canvas{margin-right:min(460px,100vw)}
body.panel-open #wrap{scroll-padding-right:min(460px,100vw)}
#panel h2{font-size:16px;margin:4px 0 8px}
#panel .meta{color:var(--muted);font-size:12px}
#panel table{border-collapse:collapse;margin:8px 0;font-size:12px}
#panel td,#panel th{border:1px solid var(--line);padding:3px 6px;text-align:left;vertical-align:top}
#panel blockquote{margin:8px 0;padding:4px 10px;border-left:3px solid var(--line);color:var(--muted)}
#panel code{font:12px ui-monospace,Menlo,monospace;background:var(--chip);padding:0 3px;border-radius:3px}
#panel ul,#panel ol{padding-left:20px}
#panel a{color:var(--edge-hl)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 10px}
.chip{font:12px ui-monospace,Menlo,monospace;padding:2px 7px;border-radius:5px;background:var(--chip);cursor:pointer;
  border-left:3px solid var(--muted-c)}
.chip.done{border-left-color:var(--done)} .chip.pending{border-left-color:var(--pending)}
.chip.neutral{border-left-color:var(--neutral)}
.close{float:right}
.sec{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:12px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.seg button{border:0;border-radius:0;padding:5px 9px;color:var(--muted)}
.seg button+button{border-left:1px solid var(--line)}
.seg button.on{background:var(--chip);color:var(--text);font-weight:600}
#panel .head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
#panel .x{border:0;background:none;font-size:18px;line-height:1;padding:2px 4px;color:var(--muted)}
#panel .x:hover{color:var(--text)}
.rel{display:flex;gap:8px;align-items:baseline;padding:6px 0;border-bottom:1px solid var(--line);cursor:pointer}
.rel:hover .rt{text-decoration:underline}
.rel .rid{font:600 12px ui-monospace,Menlo,monospace;white-space:nowrap}
.rel .rt{flex:1}
.rel .rs{font-size:11px;white-space:nowrap}
.rel .rs.done{color:var(--done)} .rel .rs.pending{color:var(--pending)} .rel .rs.neutral{color:var(--neutral)}
.rel .rs.muted{color:var(--muted-c)}
/* focus */
.card .fbtn{position:absolute;top:5px;right:6px;width:22px;height:22px;padding:0;border:0;border-radius:50%;
  background:var(--chip);color:var(--muted);font-size:14px;line-height:22px;display:none;cursor:pointer}
.card:hover .fbtn,.card.root .fbtn{display:block}
.card:hover .type,.card.root .type{visibility:hidden}
.card .fbtn:hover{color:var(--text)}
.card.root .fbtn{background:var(--edge-hl);color:#fff}
.card.root{box-shadow:0 0 0 1px var(--edge-hl)}
.card.ctx{opacity:.5}
path.edge.ctx{opacity:.5}
#focusbar{flex-basis:100%;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;padding-top:8px;
  border-top:1px dashed var(--line)}
#focusbar[hidden]{display:none}
#focusbar .flabel{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
#fchips{display:inline-flex;gap:6px;flex-wrap:wrap}
.fchip{display:inline-flex;align-items:center;gap:2px;background:var(--chip);border-left:3px solid var(--edge-hl);
  border-radius:5px;padding:2px 2px 2px 7px;font:600 12px ui-monospace,Menlo,monospace}
.fchip a{color:var(--text);text-decoration:none}
.fchip button{border:0;background:none;padding:0 4px;color:var(--muted);cursor:pointer}
.fchip button:hover{color:var(--text)}
#fadd{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:3px 7px;font:inherit;width:190px}
.ftoggle{display:inline-flex;gap:5px;align-items:center;cursor:pointer}
.muted{color:var(--muted)}
#panel .pbtns{display:flex;gap:6px;align-items:center}
#statusbox{display:none;position:fixed;left:16px;bottom:16px;width:min(520px,calc(100% - 32px));max-height:60%;
  overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;z-index:9}
#statusbox.open{display:block}
#statusbox a{color:var(--edge-hl)}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="stats" id="stats"></div>
  <div class="legend">
    <span><span class="dot" style="background:var(--done)"></span>done / verified</span>
    <span><span class="dot" style="background:var(--pending)"></span>waiting / inferred</span>
    <span><span class="dot" style="background:var(--neutral)"></span>goal / requirement</span>
    <span>dashed arrow = input not settled</span>
  </div>
  <div class="tools">
    <input type="search" id="q" placeholder="Search cards…">
    <button id="statusbtn">Status</button>
    <div class="seg" id="theme" role="group" aria-label="Color scheme">
      <button data-mode="system">System</button><button data-mode="light">Light</button><button data-mode="dark">Dark</button>
    </div>
  </div>
  <div id="focusbar" hidden>
    <span class="flabel">Focus</span><span id="fchips"></span>
    <span id="fcount" class="muted"></span>
    <label class="ftoggle"><input type="checkbox" id="unsettled"> Unsettled only</label>
    <input id="fadd" list="fadd-list" placeholder="Add a card…" aria-label="Add a card to the focus">
    <datalist id="fadd-list"></datalist>
    <span class="muted">or Shift-click ◎</span>
    <button id="fexit">Exit focus (Esc)</button>
  </div>
</header>
<div id="wrap"><div id="canvas"><svg id="edges"></svg></div></div>
<aside id="panel"></aside>
<div id="statusbox"></div>
<script>
const DATA = /*__DATA__*/null;
const W=262, H=92, GAP=150, ROWGAP=34, PADX=20, TOP=40;
const nodes = DATA.nodes, byId = new Map(nodes.map(n=>[n.id,n]));
nodes.forEach(n=>{ n.children=[]; });
nodes.forEach(n=>n.deps.forEach(d=>byId.get(d).children.push(n.id)));
const canvas = document.getElementById('canvas'), svg = document.getElementById('edges');
const wrap = document.getElementById('wrap'), root = document.documentElement;
const esc = s => s.replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const PREFIX_ORDER = ['OPEN','FND','EXP','CON','DEC','Q','REQ','GOAL'];
const isSettled = n => n.state==='done' || n.state==='muted';

// ---- stats
const count = (p, st) => nodes.filter(n=>n.prefix===p && (!st || n.state===st)).length;
const stats = [
  ['Open items', `${count('OPEN','pending')} waiting · ${count('OPEN','done')} resolved`],
  ['Findings', `${count('FND','done')} verified · ${count('FND','pending')} inferred/partly`],
  ['Questions', `${count('Q')} unanswered`],
  ['Decisions', `${count('DEC','done')} active · ${count('DEC','pending')} proposed`],
];
document.getElementById('stats').innerHTML = stats.map(([k,v])=>`<span>${k}: <b>${v}</b></span>`).join('')
  + `<span>Built ${esc(DATA.built)}</span>`;

// ---- cards (created once; render() positions or hides them)
const pendingDeps = n => n.deps.filter(d=>byId.get(d).state==='pending').length;
for (const n of nodes) {
  const el = document.createElement('div');
  el.className = 'card '+n.state; el.id = 'card-'+n.id;
  el.style.width=W+'px'; el.style.height=H+'px';
  const p = pendingDeps(n), total = n.deps.length;
  let extra = '';
  if (total && (n.prefix==='GOAL' || n.prefix==='Q')) {
    extra = `<span class="pill ${p? 'pending':'done'}">${total-p}/${total} inputs settled</span>`;
  } else if (p) {
    extra = `<span class="pill bad">${p} input${p>1?'s':''} pending</span>`;
  }
  el.innerHTML = `<div class="top"><span class="id">${n.id}</span><span class="type">${n.type}</span></div>
    <button class="fbtn" title="Focus on this card (Shift-click to add it to the focus)" aria-label="Focus on ${n.id}">◎</button>
    <div class="title" title="${esc(n.title)}">${esc(n.title)}</div>
    <div class="pills"><span class="pill ${n.state}" title="${esc(n.label)}">${esc(n.label.replace(/ \(.*\)$/, n.label.length>22?' *':'$&'))}</span>${extra}</div>`;
  el.addEventListener('mouseenter',()=>{ if(!selected) highlight(n.id); });
  el.addEventListener('mouseleave',()=>{ if(!selected) clearHighlight(); });
  el.addEventListener('click',e=>{ e.stopPropagation(); select(n.id); });
  el.querySelector('.fbtn').addEventListener('click', e=>{ e.stopPropagation(); focusCard(n.id, e.shiftKey); });
  canvas.appendChild(el); n.el = el;
}

// ---- layout: longest dependency path picks the column; sources sit next to their first
// consumer; barycenter sweeps order the rows. Runs on whatever subset is in view.
function layout(ids, depsOf, kidsOf){
  const col = new Map();
  const depth = i => {
    if (col.has(i)) return col.get(i);
    col.set(i, 0);  // guard; the builder already rejects cycles
    const d = 1 + Math.max(-1, ...depsOf(i).map(depth));
    col.set(i, d); return d;
  };
  ids.forEach(depth);
  ids.forEach(i=>{ const k = kidsOf(i);
    if (!depsOf(i).length && k.length) col.set(i, Math.max(0, Math.min(...k.map(c=>col.get(c))) - 1)); });
  const ncols = Math.max(0, ...ids.map(i=>col.get(i))) + 1;
  const keyCmp = (a,b) => { const A=byId.get(a), B=byId.get(b);
    return PREFIX_ORDER.indexOf(A.prefix)-PREFIX_ORDER.indexOf(B.prefix) || A.num-B.num; };
  const cols = Array.from({length:ncols}, (_,c)=>ids.filter(i=>col.get(i)===c).sort(keyCmp));
  const all = [...Array(ncols).keys()];
  for (let it=0; it<12; it++) for (const dir of [1,-1]) {
    const pos = new Map(); cols.forEach(c=>c.forEach((i,r)=>pos.set(i,r)));
    for (const c of (dir===1 ? all.slice(1) : all.slice(0,-1).reverse())) {
      const scored = cols[c].map((i,r)=>{
        const ps = (dir===1 ? depsOf(i) : kidsOf(i)).filter(x=>pos.has(x)).map(x=>pos.get(x));
        const loner = !depsOf(i).length && !kidsOf(i).length;
        return [loner?1:0, ps.length ? ps.reduce((a,b)=>a+b,0)/ps.length : r, r, i];
      });
      scored.sort((a,b)=>a[0]-b[0] || a[1]-b[1] || a[2]-b[2]);
      cols[c] = scored.map(s=>s[3]); cols[c].forEach((i,r)=>pos.set(i,r));
    }
  }
  const out = new Map(); cols.forEach((c,ci)=>c.forEach((i,r)=>out.set(i,{col:ci,row:r})));
  return {pos:out, ncols};
}

// ---- focus: focused cards, everything they depend on (all the way down), and their direct
// users faded as context. "Unsettled only" hides settled inputs and joins the arrows across them.
let focusIds = [], unsettledOnly = false, selected = null, view = null, edges = [];
function computeView(){
  if (!focusIds.length) {
    return {ids: nodes.map(n=>n.id), deps: id=>byId.get(id).deps, ctx: new Set(), roots: new Set(), core: nodes.length};
  }
  const roots = new Set(focusIds), up = new Set();
  const walk = i => byId.get(i).deps.forEach(d=>{ if (!up.has(d)) { up.add(d); walk(d); } });
  focusIds.forEach(walk);
  const core = new Set(focusIds);
  up.forEach(a=>{ if (!roots.has(a) && !(unsettledOnly && isSettled(byId.get(a)))) core.add(a); });
  const ctx = new Set();
  focusIds.forEach(r=>byId.get(r).children.forEach(c=>{ if (!core.has(c)) ctx.add(c); }));
  const memo = new Map();
  const deps = id => {
    if (ctx.has(id)) return byId.get(id).deps.filter(d=>roots.has(d));
    if (memo.has(id)) return memo.get(id);
    const res = new Set(), seen = new Set();
    const dfs = i => byId.get(i).deps.forEach(d=>{
      if (seen.has(d)) return; seen.add(d);
      if (core.has(d)) res.add(d); else dfs(d);
    });
    dfs(id);
    const arr = [...res]; memo.set(id, arr); return arr;
  };
  return {ids: [...core, ...ctx], deps, ctx, roots, core: core.size};
}

function render(){
  view = computeView();
  const vset = new Set(view.ids);
  const kids = new Map(view.ids.map(i=>[i,[]]));
  view.ids.forEach(i=>view.deps(i).forEach(d=>kids.get(d).push(i)));
  view.kids = i => kids.get(i) || [];
  const {pos, ncols} = layout(view.ids, view.deps, view.kids);
  for (const n of nodes) {
    const on = vset.has(n.id);
    n.el.style.display = on ? '' : 'none';
    n.el.classList.toggle('ctx', view.ctx.has(n.id));
    n.el.classList.toggle('root', view.roots.has(n.id));
    if (on) {
      const p = pos.get(n.id); n.col = p.col; n.row = p.row;
      n.x = PADX + n.col*(W+GAP); n.y = TOP + n.row*(H+ROWGAP);
      n.el.style.left = n.x+'px'; n.el.style.top = n.y+'px';
    }
  }
  const vnodes = view.ids.map(i=>byId.get(i));
  const cols = Array.from({length:ncols}, (_,c)=>vnodes.filter(n=>n.col===c).sort((a,b)=>a.row-b.row));
  const maxRows = Math.max(1, ...cols.map(c=>c.length));
  const width = PADX*2 + ncols*W + (ncols-1)*GAP, height = TOP + maxRows*(H+ROWGAP) + 40;
  canvas.style.width = width+'px'; canvas.style.height = height+'px';
  svg.setAttribute('width', width); svg.setAttribute('height', height);
  canvas.querySelectorAll('.colhead').forEach(h=>h.remove());
  const heads = focusIds.length ? {} : {0:'Foundations', [ncols-1]:'Goals'};
  for (const [c,label] of Object.entries(heads)) {
    const h = document.createElement('div'); h.className='colhead'; h.textContent=label;
    h.style.left = (PADX + c*(W+GAP))+'px'; h.style.top='12px'; canvas.appendChild(h);
  }
  edges = [];
  view.ids.forEach(t=>view.deps(t).forEach(s=>edges.push({s:byId.get(s), t:byId.get(t)})));
  route(cols, maxRows);
  updateFocusBar();
  if (selected && !vset.has(selected)) deselect();
  else if (selected) highlight(selected);
  else clearHighlight();
}

// ---- edge routing (orthogonal)
// Rules: (1) arrows FROM the same card share one path and split only where they diverge:
// one exit port per card, and one vertical trunk per source in each gap. Each target gets
// its own entry port and arrowhead. (2) Paths favor the middle of a gap between columns,
// or of the space between rows, and build outward from there (centre, +1, -1, +2, -2 ...).
// (3) A horizontal run that crosses another source's vertical run draws a small hop.
const NS='http://www.w3.org/2000/svg';
const dist = (a,b) => Math.hypot(a[0]-b[0], a[1]-b[1]);
const along = (a,b,t) => { const L = dist(a,b)||1; return [a[0]+(b[0]-a[0])/L*t, a[1]+(b[1]-a[1])/L*t]; };
function route(cols, maxRows){
  const PORT = H/2;
  const inPort = new Map();
  for (const id of view.ids) {
    const n = byId.get(id);
    const ins = view.deps(id).map(d=>byId.get(d)).sort((a,b)=>a.y-b.y || b.col-a.col);
    const k = ins.length;
    ins.forEach((d,i)=>inPort.set(d.id+'>'+n.id, k===1 ? n.y+PORT : n.y + H*(0.2 + 0.6*i/(k-1))));
  }
  const gapX0 = g => PADX + g*(W+GAP) + W;
  const blocked = (c,y,m=8) => cols[c].some(o => y > o.y-m && y < o.y+H+m);
  const CH_OFFS = [0,-6,6,-12,12];
  const chanUse = new Map(), srcChans = new Map(), trunks = new Map();
  function addTrunk(gap, src, a, b){
    const key = gap+'|'+src;
    let T = trunks.get(key);
    if (!T) { T = {gap, src, lo:Infinity, hi:-Infinity}; trunks.set(key, T); }
    T.lo = Math.min(T.lo, a, b); T.hi = Math.max(T.hi, a, b);
    return T;
  }
  for (const e of edges) {
    const s=e.s, t=e.t;
    e.sy = s.y + PORT; e.ty = inPort.get(s.id+'>'+t.id); e.mid = null;
    const inner = []; for (let c=s.col+1; c<t.col; c++) inner.push(c);
    if (inner.length && inner.some(c=>blocked(c,e.sy))) {
      // Needs a channel between rows. Reuse this source's existing channel if it fits.
      let best = null;
      for (const y of (srcChans.get(s.id)||[])) if (!inner.some(c=>blocked(c,y,2))) { best = y; break; }
      if (best === null) {
        const cands = new Set([TOP-18, TOP+maxRows*(H+ROWGAP)-ROWGAP/2+6]);
        inner.forEach(c=>cols[c].forEach(o=>{ cands.add(o.y-ROWGAP/2); cands.add(o.y+H+ROWGAP/2); }));
        let bc = Infinity, by = null;
        for (const y of cands) {
          if (inner.some(c=>blocked(c,y))) continue;
          const cost = Math.abs(y-e.sy) + Math.abs(y-e.ty);
          if (cost < bc) { bc = cost; by = y; }
        }
        const key = Math.round(by), k = chanUse.get(key)||0; chanUse.set(key, k+1);
        best = by + CH_OFFS[k % CH_OFFS.length];
        if (!srcChans.has(s.id)) srcChans.set(s.id, []);
        srcChans.get(s.id).push(best);
      }
      e.mid = best;
      e.T0 = addTrunk(s.col, s.id, e.sy, e.mid);
      e.T1 = addTrunk(t.col-1, s.id, e.mid, e.ty);
    } else {
      e.T1 = addTrunk(t.col-1, s.id, e.sy, e.ty);
    }
  }
  // Lanes: centre of the gap first, then alternate outward. Longest trunks claim the middle.
  const STEP = 9, maxSlots = Math.max(1, Math.floor((GAP-24)/STEP));
  const slotOrder = [0];
  for (let i=1; slotOrder.length<maxSlots; i++) { slotOrder.push(i); if (slotOrder.length<maxSlots) slotOrder.push(-i); }
  const byGap = new Map();
  for (const T of trunks.values()) { if (!byGap.has(T.gap)) byGap.set(T.gap, []); byGap.get(T.gap).push(T); }
  for (const [g, list] of byGap) {
    list.sort((a,b)=>(b.hi-b.lo)-(a.hi-a.lo));
    const used = new Map();
    for (const T of list) {
      let slot = slotOrder.find(sl => (used.get(sl)||[]).every(o => T.lo > o.hi+8 || T.hi < o.lo-8));
      if (slot === undefined) slot = slotOrder[slotOrder.length-1];
      if (!used.has(slot)) used.set(slot, []);
      used.get(slot).push(T);
      T.x = gapX0(g) + GAP/2 + slot*STEP;
    }
  }
  for (const e of edges) {
    const sx = e.s.x+W, tx = e.t.x-2;
    e.pts = e.mid==null
      ? [[sx,e.sy],[e.T1.x,e.sy],[e.T1.x,e.ty],[tx,e.ty]]
      : [[sx,e.sy],[e.T0.x,e.sy],[e.T0.x,e.mid],[e.T1.x,e.mid],[e.T1.x,e.ty],[tx,e.ty]];
  }
  // Vertical runs, for hop detection.
  const VSEGS = [];
  for (const e of edges) for (let i=0; i<e.pts.length-1; i++) {
    const [a,b] = [e.pts[i], e.pts[i+1]];
    if (Math.abs(a[0]-b[0]) < 0.5 && Math.abs(a[1]-b[1]) > 0.5)
      VSEGS.push({x:a[0], lo:Math.min(a[1],b[1]), hi:Math.max(a[1],b[1]), src:e.s.id});
  }
  function pathD(pts, src){
    const R = 5, HOP = 4, n = pts.length, rr = [];
    for (let i=1; i<n-1; i++) {
      const d1 = dist(pts[i-1],pts[i]), d2 = dist(pts[i],pts[i+1]);
      rr[i] = (d1<0.5 || d2<0.5) ? 0 : Math.min(R, d1/2, d2/2);
    }
    let cur = pts[0], d = `M${cur[0]},${cur[1]}`;
    for (let i=0; i<n-1; i++) {
      const a = pts[i], b = pts[i+1];
      const end = (i+1 < n-1) ? along(b, a, rr[i+1]) : b;
      if (Math.abs(a[1]-b[1]) < 0.5 && Math.abs(a[0]-b[0]) > 0.5) {
        const y = a[1], dir = Math.sign(b[0]-a[0]);
        const xs = [...new Set(VSEGS.filter(v => v.src!==src && y > v.lo+0.5 && y < v.hi-0.5
                     && (v.x-cur[0])*dir > HOP+1 && (end[0]-v.x)*dir > HOP+1).map(v => Math.round(v.x*10)/10))]
                   .sort((p,q) => (p-q)*dir);
        for (const x of xs) d += ` L${x-dir*HOP},${y} A${HOP},${HOP} 0 0 ${dir>0?1:0} ${x+dir*HOP},${y}`;
      }
      d += ` L${end[0]},${end[1]}`;
      if (i+1 < n-1) { const c = pts[i+1], nx = along(c, pts[i+2], rr[i+1]); d += ` Q${c[0]},${c[1]} ${nx[0]},${nx[1]}`; cur = nx; }
    }
    return d;
  }
  svg.innerHTML = `<defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="context-stroke"/></marker></defs>`;
  for (const e of edges) {
    const p = document.createElementNS(NS,'path');
    p.setAttribute('d', pathD(e.pts, e.s.id)); p.setAttribute('marker-end','url(#arr)');
    p.setAttribute('class','edge'+(e.s.state==='pending'?' dashed':'')+(view.ctx.has(e.t.id)?' ctx':''));
    svg.appendChild(p); e.el = p;
  }
}

// ---- hover / selection highlighting (within the current view)
function lineage(id){
  const up=new Set(), down=new Set();
  const walkUp=i=>view.deps(i).forEach(d=>{ if(!up.has(d)){up.add(d);walkUp(d);} });
  const walkDown=i=>view.kids(i).forEach(c=>{ if(!down.has(c)){down.add(c);walkDown(c);} });
  walkUp(id); walkDown(id); return {up,down};
}
function highlight(id){
  const {up,down} = lineage(id), all = new Set([id,...up,...down]);
  canvas.classList.add('focus');
  nodes.forEach(n=>n.el.classList.toggle('hl', all.has(n.id)));
  edges.forEach(e=>e.el.classList.toggle('hl',
    (all.has(e.s.id) && all.has(e.t.id)) && ((up.has(e.s.id)||e.s.id===id) && (up.has(e.t.id)||e.t.id===id)
     || (down.has(e.t.id) && (down.has(e.s.id)||e.s.id===id)))));
}
function clearHighlight(){
  canvas.classList.remove('focus');
  nodes.forEach(n=>n.el.classList.remove('hl')); edges.forEach(e=>e.el.classList.remove('hl'));
}

// ---- side panel
const panel = document.getElementById('panel');
function rel(id){
  const n = byId.get(id);
  return `<div class="rel" data-goto="${id}"><span class="rid">${id}</span><span class="rt">${esc(n.title)}</span>`
       + `<span class="rs ${n.state}">${esc(n.label)}</span></div>`;
}
function select(id, scroll){
  const n = byId.get(id); if(!n) return;
  if (!view.ids.includes(id)) { focusIds = []; render(); }   // jumping to a hidden card leaves focus
  if (selected && selected !== id) byId.get(selected).el.classList.remove('sel');
  selected = id; n.el.classList.add('sel'); highlight(id);
  const pend = pendingDeps(n), inFocus = focusIds.includes(id);
  panel.innerHTML = `<div class="head"><div><div class="meta">${n.type} · ${n.file}</div>
      <h2>${n.id} — ${esc(n.title)}</h2></div>
      <div class="pbtns"><button id="pfocus" title="${inFocus ? 'Remove this card from the focus' : 'Show only this card and what it depends on (Shift-click to add it to the focus)'}">${inFocus ? 'Unfocus' : '◎ Focus'}</button>
      <button class="x" id="pclose" title="Close" aria-label="Close">✕</button></div></div>
    <div class="pills"><span class="pill ${n.state}">${esc(n.label)}</span>
      ${pend? `<span class="pill bad">${pend} input${pend>1?'s':''} pending</span>`:''}</div>
    <div class="sec">Depends on (${n.deps.length})</div>
    ${n.deps.length? n.deps.map(rel).join('') : '<div class="meta">Nothing. This is a foundation.</div>'}
    <div class="sec">Used by (${n.children.length})</div>
    ${n.children.length? n.children.map(rel).join('') : '<div class="meta">Nothing yet.</div>'}
    <div class="sec">Full entry</div><div class="body">${n.html}</div>`;
  panel.scrollTop = 0;
  panel.classList.add('open'); document.body.classList.add('panel-open');
  document.getElementById('pclose').onclick = ()=>deselect();
  document.getElementById('pfocus').onclick = e=>{
    if (focusIds.includes(id)) setFocus(focusIds.filter(f=>f!==id));
    else focusCard(id, e.shiftKey);
  };
  if (scroll) n.el.scrollIntoView({behavior:'smooth', block:'center', inline:'center'});
  syncHash();
}
function deselect(){
  if (selected) byId.get(selected).el.classList.remove('sel');
  selected=null; panel.classList.remove('open'); document.body.classList.remove('panel-open'); clearHighlight();
  syncHash();
}

// ---- focus controls
function setFocus(ids){
  focusIds = ids.filter((v,i,a)=>byId.has(v) && a.indexOf(v)===i);
  render();
  wrap.scrollTo({left:0, top:0});
  if (selected) select(selected);   // refresh the panel's Focus button
  syncHash();
}
function focusCard(id, add){
  if (add) setFocus(focusIds.includes(id) ? focusIds.filter(f=>f!==id) : [...focusIds, id]);
  else setFocus(focusIds.length===1 && focusIds[0]===id ? [] : [id]);
}
const fbar = document.getElementById('focusbar');
function updateFocusBar(){
  fbar.hidden = !focusIds.length;
  if (focusIds.length) {
    document.getElementById('fchips').innerHTML = focusIds.map(id=>
      `<span class="fchip"><a href="#" data-goto="${id}" title="${esc(byId.get(id).title)}">${id}</a>`
      + `<button data-unfocus="${id}" title="Remove from focus" aria-label="Remove ${id} from focus">✕</button></span>`).join('');
    const c = view.ctx.size;
    document.getElementById('fcount').textContent =
      `${view.core} of ${nodes.length} cards` + (c ? ` + ${c} direct user${c>1?'s':''} (faded)` : '');
    document.getElementById('unsettled').checked = unsettledOnly;
  }
  setH();
}
fbar.addEventListener('click', e=>{
  const u = e.target.closest('[data-unfocus]');
  if (u) { e.stopPropagation(); setFocus(focusIds.filter(f=>f!==u.dataset.unfocus)); }
});
document.getElementById('unsettled').addEventListener('change', e=>{ unsettledOnly = e.target.checked; setFocus(focusIds); });
document.getElementById('fexit').addEventListener('click', ()=>setFocus([]));
// "Add a card…": type an ID or part of a title; picking a suggestion adds that card to the focus.
document.getElementById('fadd-list').innerHTML =
  nodes.map(n=>`<option value="${n.id} — ${esc(n.title)}"></option>`).join('');
const fadd = document.getElementById('fadd');
fadd.addEventListener('change', ()=>{
  const id = (fadd.value.match(/^\s*([A-Z]+-\d{3})/i) || [])[1];
  fadd.value = '';
  if (id && byId.has(id.toUpperCase()) && !focusIds.includes(id.toUpperCase())) setFocus([...focusIds, id.toUpperCase()]);
});

// ---- address: #focus=ID,ID&only=unsettled&card=ID survives reloads and rebuilds
function syncHash(){
  const p = new URLSearchParams();
  if (focusIds.length) p.set('focus', focusIds.join(','));
  if (focusIds.length && unsettledOnly) p.set('only', 'unsettled');
  if (selected) p.set('card', selected);
  const h = p.toString().replace(/%2C/g, ',');
  try { history.replaceState(null, '', h ? '#'+h : location.pathname + location.search); } catch(_){}
}

document.addEventListener('click', e=>{
  const g = e.target.closest('[data-goto]');
  if (g){ e.preventDefault(); select(g.dataset.goto, true); return; }
  // A control that re-rendered itself (e.g. the panel's Focus button) is no longer in the page.
  if (!e.target.isConnected) return;
  // Anything that is not a card or the panel closes the panel.
  if (!e.target.closest('#panel') && !e.target.closest('.card')) deselect();
});
document.addEventListener('keydown', e=>{
  if (e.key !== 'Escape') return;
  if (selected) deselect(); else if (focusIds.length) setFocus([]);
});

// ---- search
document.getElementById('q').addEventListener('input', e=>{
  const q = e.target.value.trim().toLowerCase();
  nodes.forEach(n=>n.el.classList.toggle('nomatch', !!q &&
    !(n.id.toLowerCase().includes(q) || n.title.toLowerCase().includes(q) || n.text.toLowerCase().includes(q))));
});

// ---- status box and theme
const sb = document.getElementById('statusbox');
sb.innerHTML = '<button class="close" id="sclose">✕</button>' + (DATA.status || '<p>No status section in README.md.</p>');
document.getElementById('statusbtn').onclick = ()=>sb.classList.toggle('open');
document.getElementById('sclose').onclick = ()=>sb.classList.remove('open');
function setMode(mode){
  if (mode === 'light' || mode === 'dark') root.dataset.theme = mode; else { delete root.dataset.theme; mode = 'system'; }
  document.querySelectorAll('#theme button').forEach(b=>b.classList.toggle('on', b.dataset.mode===mode));
  try { localStorage.setItem('rp-theme', mode); } catch(_){}
}
let savedMode = 'system';
try { savedMode = localStorage.getItem('rp-theme') || 'system'; } catch(_){}
setMode(savedMode);
document.querySelectorAll('#theme button').forEach(b=>b.addEventListener('click', ()=>setMode(b.dataset.mode)));
const hdr = document.querySelector('header');
function setH(){ root.style.setProperty('--hdr', hdr.offsetHeight+'px'); }
addEventListener('resize', setH);

// ---- start: restore focus and selection from the address
(function init(){
  const h = location.hash.slice(1);
  let card = null;
  if (byId.has(h)) card = h;   // older links: #ID
  else {
    const p = new URLSearchParams(h);
    focusIds = (p.get('focus')||'').split(',').filter(id=>byId.has(id));
    unsettledOnly = p.get('only') === 'unsettled';
    card = p.get('card');
  }
  render();
  if (card && byId.has(card)) select(card, true);
})();
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parent
    parser.add_argument("--docs", type=Path, default=here, help="docs folder (default: this script's folder)")
    parser.add_argument("--out", type=Path, default=here.parent / "dashboard.html", help="output HTML file")
    parser.add_argument("--title", default=None, help="page title (default: '<README heading> Map')")
    parser.add_argument("--tz", default=None, help="IANA time zone for the build stamp, e.g. Europe/London")
    args = parser.parse_args(argv)
    return build(args.docs, args.out, args.title, args.tz)


if __name__ == "__main__":
    sys.exit(main())
