#!/usr/bin/env python3
"""Check a built site for broken links, stray template tokens and bad markup.

    python3 src/tools/check_links.py _site

Three things it looks for, all of which have actually gone wrong here:

- **Links to a directory with no index.html.** GitHub Pages does not generate
  directory listings, so `/packages/focal/` is a 404 even though the directory
  exists and the files inside it are served. A checker that only asks "does
  this path exist" will pass a link that is broken in production.
- **Unresolved `{{tokens}}`**, meaning build.py was given a name it has no
  value for.
- **Unbalanced tags**, which usually means a hand edit lost a closing div.

The site's own manual pages are skipped: they are 2002-era HTML that does not
close its tags, and rewriting them is not the job.
"""

import html.parser
import re
import sys
from pathlib import Path

SKIP = re.compile(r"manual|^(manual|plugin)\.html$")
TOKEN = re.compile(r"\{\{[^}]*\}\}")
LINK = re.compile(r'(?:href|src)="([^"]+)"')
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}


class Balance(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.stray = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.stray.append(tag)
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()


def check(root):
    root = Path(root)
    pages = [f for f in sorted(root.rglob("*.html")) if not SKIP.search(f.name)]
    problems = 0

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        where = page.relative_to(root).as_posix()

        for token in TOKEN.findall(text):
            print("  %-26s unresolved token %s" % (where, token))
            problems += 1

        parser = Balance()
        parser.feed(text)
        if parser.stray or parser.stack:
            print("  %-26s unbalanced: stray %s, unclosed %s"
                  % (where, parser.stray[:3], parser.stack[:3]))
            problems += 1

        for link in sorted(set(LINK.findall(text))):
            if link.startswith(("http", "mailto:", "#", "data:", "//")):
                continue
            path = link.split("#")[0].split("?")[0]
            if not path:
                continue
            if not path.startswith("/"):
                print("  %-26s relative link %s" % (where, link))
                problems += 1
                continue
            target = root / path.lstrip("/")
            # A directory is only reachable if it holds an index.html --
            # Pages will not list it.
            if path.endswith("/"):
                if not (target / "index.html").exists():
                    kind = "no index.html" if target.is_dir() else "missing"
                    print("  %-26s %s -> %s" % (where, link, kind))
                    problems += 1
            elif not target.exists():
                print("  %-26s %s -> missing" % (where, link))
                problems += 1

    print("\n%d page(s) checked, %d problem(s)" % (len(pages), problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else "_site"))
