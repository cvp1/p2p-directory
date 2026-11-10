"""spec_html — render SPEC.md to a standalone index.html (stdlib only).

Handles what SPEC.md uses: YAML front matter (title), headings, paragraphs,
bullet and numbered lists (with indented continuation and fenced code inside an
item), fenced code, pipe tables, and inline code, bold and links. Text is
HTML-escaped before any markup is added.
"""
import html
import re
import sys

STYLE = """body{font:16px/1.5 system-ui,sans-serif;max-width:52rem;margin:0 auto;padding:1rem;color:#1b1b1b}
code,pre{font:14px/1.4 ui-monospace,Menlo,monospace;background:#f3f3f3}code{padding:0 .2em}
pre{padding:.7rem;overflow-x:auto}table{border-collapse:collapse;margin:.5rem 0}
td,th{border:1px solid #ddd;padding:.25rem .5rem;text-align:left;vertical-align:top}th{background:#f6f6f6}"""

LIST_RE = re.compile(r"^([-*]|\d+\.)\s+")


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline(text):
    """Links first (their text may hold code), then code spans, then bold."""
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(_spans(text[pos:m.start()]))
        out.append(f'<a href="{html.escape(m.group(2))}">{_spans(m.group(1))}</a>')
        pos = m.end()
    out.append(_spans(text[pos:]))
    return "".join(out)


def _spans(text):
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
        else:
            out.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(part, quote=False)))
    return "".join(out)


def dedent(block):
    indent = min((len(b) - len(b.lstrip()) for b in block if b.strip()), default=0)
    return "\n".join(b[indent:] for b in block)


def fence(lines, i):
    """lines[i] opens a fence; return (code, index after the closing fence)."""
    i += 1
    block = []
    while i < len(lines) and not lines[i].strip().startswith("```"):
        block.append(lines[i])
        i += 1
    return dedent(block), i + 1


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    body = [r for r in cells[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    return ("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            + "</table>")


def render(md):
    title = "Spec"
    if md.startswith("---\n"):
        front, _, md = md[4:].partition("\n---\n")
        m = re.search(r"^title:\s*(.+)$", front, re.M)
        title = m.group(1).strip() if m else title
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            code, i = fence(lines, i)
            out.append("<pre><code>" + html.escape(code) + "</code></pre>")
        elif re.match(r"^#{1,4}\s", line):
            n = len(line) - len(line.lstrip("#"))
            out.append(f"<h{n}>{inline(line[n:].strip())}</h{n}>")
            i += 1
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(table(rows))
        elif LIST_RE.match(line):
            tag = "ol" if re.match(r"^\d+\.", line) else "ul"
            items = []  # [text, [code blocks]]
            while i < len(lines):
                cur = lines[i]
                if LIST_RE.match(cur):
                    items.append([LIST_RE.sub("", cur), []])
                    i += 1
                elif cur.startswith("  ") and cur.strip().startswith("```"):
                    code, i = fence(lines, i)
                    items[-1][1].append(code)
                elif cur.startswith("  ") and cur.strip():
                    items[-1][0] += " " + cur.strip()
                    i += 1
                elif not cur.strip() and i + 1 < len(lines) and (
                        lines[i + 1].startswith("  ") or LIST_RE.match(lines[i + 1])):
                    i += 1
                else:
                    break
            lis = ["<li>" + inline(t) + "".join(f"<pre><code>{html.escape(c)}</code></pre>" for c in codes) + "</li>"
                   for t, codes in items]
            out.append(f"<{tag}>" + "".join(lis) + f"</{tag}>")
        elif not s:
            i += 1
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not (
                    lines[i].startswith("#") or lines[i].strip().startswith(("|", "```")) or LIST_RE.match(lines[i])):
                para.append(lines[i].strip())
                i += 1
            out.append("<p>" + inline(" ".join(para)) + "</p>")
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>\n"
            + "\n".join(out) + "\n</body></html>\n")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        page = render(fh.read())
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(page)
