# jpilot.org rewrite — status

Rewrite of jpilot.org as plain static HTML served by GitHub Pages.
Working branch: **`redesign-2026`** (off `gh-pages`). The live site is untouched.

## Where it stands

The build and all eight pages are written, building clean, and reviewed on
screen — Judd has seen them and is happy with how they look. Committed and
pushed as `4a15301`, "first round of rewrite". The repo root is untouched and
`gh-pages` is what gets served, so the live site is unaffected.

What is left is the punch list at the bottom, and then the cutover.

**Preview:** `python3 src/build.py --out _site --serve`
then open <http://localhost:8000/>.

That is self-contained: the build copies the screenshots, manuals, icons, and
package archive into any out-of-tree build, skipping files that have not
changed, so rebuilds while you iterate are instant. Building into the repo
root skips the copying, because those files are already in place.

The same works on another machine with only `src/` copied across: anything
missing is skipped silently, so you get the pages without the pictures. Put
`documentation/` beside `src/` and the screenshots come back.

## Layout

```
src/
  build.py                   # ~230 lines, stdlib only
  templates/base.html        # <head>, nav, footer — single source of truth
  pages/*.html               # one fragment per page, metadata in a leading comment
  static/site.css            # hand-written; the font is inlined into it at build time
  static/site.js             # copy buttons + theme toggle, ~90 lines
  static/img/palmpilot5000.png
  static/fonts/ubuntu-700.woff2, UBUNTU-FONT-LICENCE.txt
  tools/prepare_palm.py      # one-off: knock out the photo background, measure the LCD
  tools/subset_font.py       # one-off: instance + subset Ubuntu to a 14 KB woff2
```

`python3 src/build.py` writes `index.html`, `download/index.html`, … at the
repo root, keeping today's pretty URLs. `--out DIR` builds elsewhere.

The two `tools/` scripts need Pillow and fonttools respectively. You only run
them if you replace the photo or change the font; their output is committed.

## Decisions, as built

1. **Clean slate.** Blog archive and German manual dropped. Documentation
   links out to the in-repo `docs/` and the existing English manual.
2. **Build:** Python 3, stdlib only. No npm, no Jekyll.
3. **Pages:** Home · Features · Screenshots · Download (folds in Requirements)
   · Documentation · Plugins · Lists · Links. `/requirements/` becomes a
   redirect to `/download/#requirements` so old links still land.
4. **Design:** LCD / graphite / deep-green, monospace detail, full light/dark
   with a header toggle that overrides the OS preference and is remembered.
   Copy buttons on all code blocks, added by JS so they never appear broken.
5. **Font: Ubuntu**, as you picked. Subset to bold-only over a Latin set,
   14 KB, inlined as a data URI — no external requests anywhere on the site.

## Hero image

Your pick: the PalmPilot 5000 from Wikimedia Commons. Processed by
`tools/prepare_palm.py`, which flood-fills the white background to transparent
so it sits on both themes, trims, and quantises it to 57 KB (from 316 KB).

The day's agenda is drawn over the photographed screen in CSS, positioned in
percentages the tool measured off the image, sized in `cqw` so it scales with
the photo. If you ever swap the image, re-run the tool and paste the four
percentages it prints into the `.screen` rule in `site.css`.

**Attribution is required and is in the page's figcaption:** photo by Channel R
at English Wikipedia, CC BY-SA 3.0. Do not remove the caption — the licence is
share-alike and the credit is the condition of use.

The Ubuntu Font Licence likewise requires a subset be renamed; the family is
`"Ubuntu derivative jpilot.org"` in both the font's name table and the CSS, and
the licence text ships at `/static/fonts/UBUNTU-FONT-LICENCE.txt`.

## Content checked against the live web

Every outbound link was fetched. Dead ones were replaced or pointed at the
Internet Archive rather than left to rot:

- **`pilot-link.org` no longer resolves at all.** The Links page now sends
  people to the Debian package, <https://github.com/desrod/pilot-link>, and
  SourceForge, with the old home page archived.
- `lists.pilot-link.org`, Henrik Becker's page, and the Bonn host for
  pilot-mailsync are gone. Archived, or noted as gone.
- Palm Power, Linux Magazine, and PC Quest are all dead; `linux-mag.com` is now
  a squatted domain, so that link goes to the Archive instead.
- Mailing list archive URL corrected to the Empathy one you actually run.

**Worth your eye:** the Download page lists 2.0.2 as the newest `.deb` in
`/packages/`, because no 2.1.0 debs are in this repo — the git log mentions
uploading the 26.04 package to Nextcloud. The page leads with the packagecloud
apt repository, so this only matters for the direct-download table.

## Cutover, once you approve

1. `python3 src/build.py` — writes the new pages over the old ones, and adds
   `.nojekyll`.
2. Delete: `_config.yml`, `assets/` (old theme), `blog/`, `articles/`,
   `redesign-1/`, `redesign-2/`, `release-*/`, `site-moved-to-gnu/`,
   `site-up/`, `wiki-up/`, `theme-setup/`, `tags/`, `search/`, `search.json`,
   `home/`, `Bought-a-nexus/`, `nexus-without-data/`, `feed.xml`,
   `feed.xslt.xml`, `index.html~`, `download/index.html~`, `favicon.*.orig`,
   and `documentation/jpilot-manual-de*`.
3. Keep: `CNAME`, `documentation/` (English manual, `manual.html`,
   `plugin.html`, the PNGs), `packages/`, `tarballs/`, `ChangeLog`,
   `images/` (the touch icons), `favicon.*`, `404.html`.
4. Merge to `gh-pages`.

## Found and fixed on screen

Rendered in Firefox at 1280px and 420px, light and dark. Four things only
showed up once the pages were actually looked at:

- **Screenshots were cropped wrong.** `object-fit: cover` was cutting the
  buttons off the Search and Print dialogs and blowing up the small ones —
  `install` is portrait and `print` is 239px square, against a 4:3 frame.
  Now `contain`, so each window is shown whole and letterboxed.
- **The features grid stretched cards to a common height**, which turned
  "Sync and backup" into a large empty box beside a card with twice the
  bullets. Cards now size to their content.
- **The done tick on the hero LCD overflowed its 9px box** and rendered as a
  slash across the corner. It is drawn by CSS now, at its own size.
- **The first row of screenshots was lazy-loaded** despite sitting above the
  fold. Lazy loading is kept for everything further down.
- **The hero photo had a white halo in dark mode**, then jagged light edges
  after a first attempt at fixing it. Both had the same root cause: the
  outline pixels are a blend of white background and dark bezel, and no
  brightness threshold can separate them. Down the left edge the outline pixel
  reads 168, 201, 219, 123, 97, 58 on successive rows, while the device's own
  top bezel highlight runs to 152 — any cutoff keeps part of the outline and
  eats part of the device, differently on each row, which is what made it look
  ragged.

  `prepare_palm.py` now uses brightness only to find what is *definitely*
  background, then solves every pixel within two of it: `C = a*F + (1-a)*W`,
  with `F` taken from the solid pixels behind. That recovers both the true
  colour and the coverage. It is safe to apply generously, because a pixel
  that is really device already equals `F` and solves to fully opaque. 1485
  outline pixels are feathered; zero opaque near-white pixels touch
  transparency afterwards.

  Keep the palette quantisation: RGBA is four to six times the size (337 KB
  against 57 KB) for no visible gain. It does leave much of the interior at
  alpha 254 rather than 255, which is a quantiser artifact with no visual or
  file-size cost — pre-snapping the alpha was tried and changed neither.

One gotcha for whoever screenshots this next: Firefox's `--screenshot` never
paints `loading="lazy"` images, whatever you set `dom.image-lazy-loading` to.
That is a headless artifact, not a site bug. To review those rows, strip the
attribute from the built HTML into a throwaway copy and shoot that.

## Still open

Roughly in the order they want doing:

- A second look at the pages only seen at one width — Documentation and
  Plugins were checked at 1280px but not on a phone.
- `404.html` still uses the old theme; it should get the new template. It is
  the only page left that does not.
- Decide whether the 2.1.0 `.deb`s belong here or stay on Nextcloud/GitHub,
  and update the Download page's archive table to match. Right now it lists
  2.0.2 as the newest `.deb`, because that is genuinely the newest one in this
  repo.
- Proofread the copy. It was rewritten from the old pages rather than copied
  verbatim, so the facts came across but the wording is mine — worth your eye,
  particularly the Features page and the news items on the home page.
- Then the cutover above.

Validated already, so no need to redo: balanced HTML on all eight pages, no
unresolved template tokens, no broken internal links, and every outbound link
fetched at least once. Total output 183 KB; a cold first visit is ~107 KB.
