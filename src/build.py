#!/usr/bin/env python3
"""Build www.jpilot.org.

Takes the shared template in ``templates/base.html`` plus one content fragment
per page in ``pages/`` and writes plain static HTML into the repo root, keeping
the site's pretty URLs (``download/index.html`` is served as ``/download/``).

    python3 src/build.py              # build into the repo root
    python3 src/build.py --out _site  # build into a scratch dir instead
    python3 src/build.py --serve      # build, then serve it on localhost:8000

Python 3 standard library only -- no npm, no Jekyll.
"""

import argparse
import base64
import http.server
import functools
import re
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

# --------------------------------------------------------------------------
# Site-wide values.  These are substituted into templates and page fragments
# as {{version}}, {{github}}, and so on -- update the release here, not in
# eight different HTML files.
# --------------------------------------------------------------------------
SITE = {
    "name": "J-Pilot",
    "url": "https://www.jpilot.org",
    "version": "2.1.0",
    "released": "August 8, 2026",
    "pilot_link": "0.15.0",
    "github": "https://github.com/juddmon/jpilot",
    "releases": "https://github.com/juddmon/jpilot/releases",
    "packagecloud": "https://packagecloud.io/judd/jpilot",
    "list_archive": "https://lists.jpilot.org/empathy/list/jpilot.lists.jpilot.org",
    "years": "1999&ndash;2026",
}

# Page order here is also the nav order.  slug "" is the home page.
PAGES = [
    ("index.html", ""),
    ("features.html", "features"),
    ("screenshots.html", "screenshots"),
    ("download.html", "download"),
    ("documentation.html", "documentation"),
    ("plugins.html", "plugins"),
    ("lists.html", "lists"),
    ("links.html", "links"),
]

# Pages that use the template but are not part of the nav, and are written to
# an exact path rather than a pretty URL. GitHub Pages serves /404.html for
# any address it cannot find, so the name has to be exactly that.
STANDALONE = [
    ("404.html", "404.html"),
]

# Old URLs that no longer have a page of their own.
REDIRECTS = {
    "requirements": "/download/#requirements",
}

# Files the pages link to but the build does not generate. They live beside
# src/ in the repo, and are copied across for any build that is not writing
# into the repo root. Order matters only in that pages are written afterwards,
# so a generated index.html always wins over a copied one.
EXTRAS = [
    "documentation",  # screenshots, and the user and plugin manuals
    "images",         # the apple-touch icons
    "packages",       # the .deb archive linked from the download page
    "tarballs",       # the source archive, likewise
    "ChangeLog",
    "favicon.png",
    "favicon.ico",
]

# Display font, built by src/tools/subset_font.py and inlined here as a data
# URI so the site makes no external requests at all.  Only headings use it,
# and only at bold, so one face is enough.  If the woff2 is missing the build
# still works -- @font-face falls back to a locally installed Ubuntu, then to
# the system sans stack, and the site just looks slightly plainer.
#
# The name is the Ubuntu Font Licence's required form for a subset; see
# src/tools/subset_font.py.  It must match the font's own name table and the
# --display stack in site.css.
FONT_FACES = [
    ("Ubuntu derivative jpilot.org", 700, "normal", "ubuntu-700.woff2"),
]

TOKEN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def render(text, values):
    """Replace {{key}} with values[key].  Unknown keys are left alone."""
    return TOKEN.sub(lambda m: str(values.get(m.group(1), m.group(0))), text)


def parse_page(path):
    """Split a page fragment into its metadata header and its body.

    The header is a leading HTML comment of ``key: value`` lines, which keeps
    the fragments valid HTML that a browser will render on its own.
    """
    text = path.read_text(encoding="utf-8")
    meta = {}
    match = re.match(r"\s*<!--(.*?)-->\s*", text, re.S)
    if match:
        for line in match.group(1).strip().splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        text = text[match.end():]
    return meta, text


def font_css():
    """@font-face rules for the display font, with the woff2 inlined if built."""
    rules = []
    for family, weight, style, filename in FONT_FACES:
        path = SRC / "static" / "fonts" / filename
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            src = 'url("data:font/woff2;base64,%s") format("woff2")' % data
            note = "%.1f KB inlined" % (path.stat().st_size / 1024)
        else:
            src = 'local("%s")' % family
            note = "not built, falling back to a locally installed %s" % family
        print("  font  %-16s %-4s  %s" % (family, weight, note))
        rules.append(
            "@font-face {\n"
            '  font-family: "%s";\n'
            "  font-weight: %s;\n"
            "  font-style: %s;\n"
            "  font-display: swap;\n"
            "  src: %s;\n"
            "}" % (family, weight, style, src)
        )
    return "\n".join(rules)


def nav_html(pages, current):
    """The shared nav, with the current page marked for styling and a11y."""
    items = []
    for meta, slug in pages:
        if slug == "":
            continue
        here = slug == current
        items.append(
            '        <a href="/%s/"%s>%s</a>'
            % (slug, ' aria-current="page"' if here else "", meta.get("nav", meta["title"]))
        )
    return "\n".join(items)


def sitemap(pages):
    urls = "\n".join(
        "  <url><loc>%s/%s</loc></url>" % (SITE["url"], slug + "/" if slug else "")
        for _, slug in pages
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "%s\n</urlset>\n" % urls
    )


def redirect_html(target):
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta http-equiv="refresh" content="0; url=%s">\n'
        '<link rel="canonical" href="%s">\n<title>Moved</title>\n</head>\n'
        '<body><p>This page has moved to <a href="%s">%s</a>.</p></body>\n</html>\n'
        % (target, target, target, target)
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def mirror(source, target, skip=()):
    """Copy source into target, skipping files that are already identical.

    Only the first build pays for this; afterwards it is a stat() per file.
    Paths in `skip` are left alone entirely -- they are the old rendered pages
    that this build replaces. Returns the number of files actually copied.
    """
    copied = 0
    if source.is_file():
        if target.name in skip:
            return 0
        if not target.exists() or target.stat().st_mtime != source.stat().st_mtime \
                or target.stat().st_size != source.stat().st_size:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        return copied
    for item in source.rglob("*"):
        if item.is_file():
            copied += mirror(item, target / item.relative_to(source), skip)
    return copied


def copy_extras(out):
    """Bring across the parts of the site the build does not generate.

    Screenshots, the manuals, the package archive, and the icons all live
    beside src/ rather than inside it. Building into the repo root finds them
    already in place; building anywhere else -- a preview directory, or a
    checkout of just src/ on another machine -- needs them copied over, or
    every screenshot on the site is a broken image.

    Anything missing is skipped without complaint, so a copy of src/ on its
    own still builds; you just get the pages without the pictures.
    """
    if out == ROOT:
        return

    print("extras")
    for name in EXTRAS:
        source = ROOT / name
        if not source.exists():
            continue
        # Never bring across an index.html -- every one of those is either a
        # page this build generates, or an old rendered page being replaced.
        copied = mirror(source, out / name, skip={"index.html"})
        print("  %-40s %s" % ("/" + name, "%d file(s)" % copied if copied else "up to date"))


def build(out):
    copy_extras(out)

    base = (SRC / "templates" / "base.html").read_text(encoding="utf-8")

    loaded = []
    for filename, slug in PAGES:
        meta, body = parse_page(SRC / "pages" / filename)
        loaded.append((meta, slug, body))

    nav_source = [(meta, slug) for meta, slug, _ in loaded]

    print("pages")
    for meta, slug, body in loaded:
        url = "/%s" % (slug + "/" if slug else "")
        values = dict(SITE)
        values.update(
            {
                "title": meta["title"],
                "page_title": meta["title"]
                if slug == ""
                else "%s &mdash; %s" % (meta["title"], SITE["name"]),
                "description": meta.get("description", ""),
                "canonical": SITE["url"] + url,
                "nav": nav_html(nav_source, slug),
                "body_class": meta.get("class", "page"),
                "head_extra": "",
                "content": render(body, dict(SITE)),
            }
        )
        page = render(base, values)
        # A second pass lets values that themselves contain tokens resolve.
        page = render(page, dict(SITE))
        target = out / "index.html" if slug == "" else out / slug / "index.html"
        write(target, page)
        print("  %-40s %6.1f KB" % (url, len(page.encode()) / 1024))

    print("standalone")
    for filename, path in STANDALONE:
        meta, body = parse_page(SRC / "pages" / filename)
        values = dict(SITE)
        values.update(
            {
                "title": meta["title"],
                "page_title": "%s &mdash; %s" % (meta["title"], SITE["name"]),
                "description": meta.get("description", ""),
                "canonical": "%s/%s" % (SITE["url"], path),
                "nav": nav_html(nav_source, None),
                "body_class": meta.get("class", "page"),
                # This one page stands in for every address that does not
                # exist, so it should never be the result of a search.
                "head_extra": '<meta name="robots" content="noindex">',
                "content": render(body, dict(SITE)),
            }
        )
        page = render(render(base, values), dict(SITE))
        write(out / path, page)
        print("  %-40s %6.1f KB" % ("/" + path, len(page.encode()) / 1024))

    print("redirects")
    for slug, target in REDIRECTS.items():
        write(out / slug / "index.html", redirect_html(target))
        print("  /%s/ -> %s" % (slug, target))

    print("assets")
    css = (SRC / "static" / "site.css").read_text(encoding="utf-8")
    css = css.replace("/*{{font-face}}*/", font_css())
    write(out / "static" / "site.css", css)
    print("  %-40s %6.1f KB" % ("/static/site.css", len(css.encode()) / 1024))

    js = (SRC / "static" / "site.js").read_text(encoding="utf-8")
    write(out / "static" / "site.js", js)
    print("  %-40s %6.1f KB" % ("/static/site.js", len(js.encode()) / 1024))

    for folder in ("img", "fonts"):
        source = SRC / "static" / folder
        if not source.is_dir():
            continue
        for asset in sorted(source.iterdir()):
            # The woff2 is inlined into the CSS, so it does not need shipping
            # separately -- but the licence beside it does.
            if not asset.is_file() or asset.suffix == ".woff2":
                continue
            target = out / "static" / folder / asset.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, target)
            print(
                "  %-40s %6.1f KB"
                % ("/static/%s/%s" % (folder, asset.name), asset.stat().st_size / 1024)
            )

    write(out / "sitemap.xml", sitemap(nav_source))
    # Tell GitHub Pages to serve these files verbatim rather than running them
    # through Jekyll.
    write(out / ".nojekyll", "")
    print("  /sitemap.xml, /.nojekyll")


def serve(out, port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    print("\nserving %s at http://localhost:%d/  (ctrl-c to stop)" % (out, port))
    try:
        http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
    except KeyboardInterrupt:
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT), help="output directory (default: repo root)")
    parser.add_argument("--serve", action="store_true", help="serve the output after building")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    out = Path(args.out).resolve()
    build(out)
    if args.serve:
        serve(out, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
