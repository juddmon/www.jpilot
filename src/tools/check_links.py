#!/usr/bin/env python3
"""Check a built site for broken links, stray template tokens and bad markup.

    python3 src/tools/check_links.py _site              # local checks only
    python3 src/tools/check_links.py _site --external   # also fetch outbound links

Local checks, all of which have actually gone wrong here:

- **Links to a directory with no index.html.** GitHub Pages does not generate
  directory listings, so `/packages/focal/` is a 404 even though the directory
  exists and the files inside it are served. A checker that only asks "does
  this path exist" will pass a link that is broken in production.
- **Unresolved `{{tokens}}`**, meaning build.py was given a name it has no
  value for.
- **Unbalanced tags**, which usually means a hand edit lost a closing div.

`--external` additionally fetches every outbound link. It needs the network,
which is why it is not the default. A status code alone is not enough: three
links on this site returned **200 and served an error page**, and no amount of
checking response codes would have caught any of them.

- `packages.debian.org/stable/pilot-link` -- "No such package". Debian dropped
  pilot-link, jpilot and jpilot-backup after buster, so three links rotted the
  same way at once.
- `jlogday.com` -- the domain lapsed and is now a registrar parking page.
- `linux-mag.com` -- lapsed and re-registered by someone else, so the link
  silently redirected to an unrelated site.

So this looks for error-page wording, suspiciously tiny pages, and redirects
that leave the original domain. Every hit is a *suspicion*, printed with what
triggered it, for a human to judge -- the alternative is a checker that cries
wolf and stops being run. It also retries before condemning anything, because
a one-off bad response is not evidence; see fetch().
"""

import concurrent.futures
import gzip
import html.parser
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKIP = re.compile(r"manual|^(manual|plugin)\.html$")
TOKEN = re.compile(r"\{\{[^}]*\}\}")
LINK = re.compile(r'(?:href|src)="([^"]+)"')
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}

UA = "jpilot.org link checker (+https://www.jpilot.org/)"
# Absolute links back to the site itself: canonical and og:url tags, not
# outbound navigation. The built copy in front of us is the authority on those,
# and the live 404 page legitimately says "page not found".
OWN_DOMAIN = "jpilot.org"
TIMEOUT = 30
BODY_LIMIT = 200_000          # plenty to see a page's real content
TINY_PAGE = 512               # bytes of text; below this something is wrong

# Wording that means "this page is not what the link promised". Matched against
# the visible text, lowercased.
ERROR_WORDING = [
    "no such package",
    "page not found",
    "404 not found",
    "this page does not exist",
    "the requested url was not found",
    "domain is for sale",
    "buy this domain",
    "this domain may be for sale",
    "is parked",
    "parked free",
    "still being worked on",       # registrar placeholder
    "check back later",
    "account suspended",
    "under construction",
]


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


TAGS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


def visible_text(body):
    """Roughly what a reader sees, for matching error wording against."""
    text = TAGS.sub(" ", body)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def registrable(host):
    """Last two labels of a hostname, near enough to spot a domain change."""
    return ".".join(host.lower().split(".")[-2:])


def fetch(url, attempts=2):
    """Fetch a URL and report anything that suggests the link has rotted.

    Returns (url, note) where note is None if the link looks healthy.

    Retries before condemning anything. A single bad fetch is not evidence: a
    SourceForge blip once served a one-word page for a project site that was
    perfectly healthy, and reporting that as rot led to a working link being
    replaced and its description rewritten from the wrong source.
    """
    note = None
    for attempt in range(attempts):
        note = _fetch_once(url)
        if note is None:
            return url, None
    return url, note


def _fetch_once(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,*/*",
        "Accept-Encoding": "gzip",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            final = response.geturl()
            raw = response.read(BODY_LIMIT)
            if response.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass                       # truncated gzip; judge on what we have
            kind = response.headers.get_content_type()
    except urllib.error.HTTPError as e:
        return "HTTP %s" % e.code
    except Exception as e:
        return "unreachable (%s)" % type(e).__name__

    if not kind.startswith("text/"):
        # A download. Cross-domain redirects are normal here -- GitHub hands
        # release assets off to a CDN -- and there is no page to read.
        return None

    # A *page* that redirects off its own domain is the classic sign that a
    # lapsed domain has been re-registered by somebody else.
    was, now = registrable(urllib.parse.urlsplit(url).netloc), \
               registrable(urllib.parse.urlsplit(final).netloc)
    if was != now and "archive.org" not in now:
        return "redirects to a different domain -> %s" % final

    body = raw.decode("utf-8", "replace")
    text = visible_text(body)
    lowered = text.lower()
    for phrase in ERROR_WORDING:
        if phrase in lowered:
            return 'serves an error page ("%s")' % phrase
    if len(text) < TINY_PAGE:
        return "page is only %d characters: %r" % (len(text), text[:60])
    return None


def check_external(links):
    print("\nfetching %d outbound link(s)" % len(links))
    suspect = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for url, note in pool.map(fetch, sorted(links)):
            if note:
                suspect += 1
                print("  %s\n      %s" % (url, note))
    if not suspect:
        print("  all reachable, none serving an error page")
    return suspect


def check(root, external=False):
    root = Path(root)
    pages = [f for f in sorted(root.rglob("*.html")) if not SKIP.search(f.name)]
    problems = 0
    outbound = set()

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
            if link.startswith(("http://", "https://")):
                if urllib.parse.urlsplit(link).netloc.endswith(OWN_DOMAIN):
                    continue
                outbound.add(link)
                continue
            if link.startswith(("mailto:", "#", "data:", "//")):
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

    if external:
        problems += check_external(outbound)
    else:
        print("%d outbound link(s) not fetched; pass --external to check them"
              % len(outbound))

    return 1 if problems else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(check(args[0] if args else "_site", "--external" in sys.argv))
