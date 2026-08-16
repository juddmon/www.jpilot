# jpilot.org rewrite — status

Rewrite of jpilot.org as plain static HTML served by GitHub Pages.
Working branch: **`redesign-2026`** (off `gh-pages`). The live site is untouched.

## Where it stands

All ten pages are written and building clean, and Judd has reviewed Home,
Features, Screenshots and Download on screen. Everything is committed on
`redesign-2026`. The repo root still holds the old site and `gh-pages` is what
gets served, so the live site is unaffected until the cutover.

What is left is the punch list near the bottom, and then the cutover.

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
  static/site.js             # copy buttons, theme toggle, screenshot viewer
  static/img/palmpilot5000.png, jpilot-*.png   # hero photo + 13 screenshots
  static/fonts/ubuntu-700.woff2, UBUNTU-FONT-LICENCE.txt
  tools/check_links.py       # run this against any build; see the bottom
  tools/prepare_palm.py      # one-off: knock out the photo background, measure the LCD
  tools/subset_font.py       # one-off: instance + subset Ubuntu to a 14 KB woff2
  tools/demo_data.py         # invented records to screenshot, as J-Pilot CSV
```

`python3 src/build.py` writes `index.html`, `download/index.html`, … at the
repo root, keeping today's pretty URLs. `--out DIR` builds elsewhere.

`check_links.py` is stdlib only and should be run after every build. The other
three need Pillow, fonttools and Pillow respectively; you only run them to
replace the photo, change the font, or regenerate the screenshot data. Their
output is committed.

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

**Since resolved:** the Download page now points at GitHub release assets for
source, and the `.deb` table is explicitly an archive — 2.1.0 is distributed
only through the apt repository, which the page says outright.

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

- **The Documentation page is badly out of date.** Deliberately deferred, and
  the bigger job of the remaining ones. Nothing on it is broken -- every link
  resolves -- but the content still describes the site as it was. Worth doing
  before the cutover if there is appetite; it is the weakest page.
- Proofread the copy on **Plugins, Lists, Links and 404**. Home, Features,
  Screenshots and Download have had Judd's eye; those four have not. The
  wording throughout is mine, rewritten from the old pages rather than copied,
  so the facts carried over but the voice needs checking.
- A look at **Documentation and Plugins on a phone**. Both were only ever
  rendered at 1280px.
- **2.0.3.** Tagged by a contributor, with no announcement on the list and no
  build behind it, so it has no release assets. Probably should not be
  presented as a release at all; Judd will decide later.
- Then the cutover below.

## Cutover, once approved

1. `python3 src/build.py` -- writes the new pages over the old ones, and adds
   `.nojekyll`.
2. `python3 src/tools/check_links.py .` to confirm the result.
3. Delete: `_config.yml`, `assets/` (old theme), `blog/`, `articles/`,
   `redesign-1/`, `redesign-2/`, `release-*/`, `site-moved-to-gnu/`,
   `site-up/`, `wiki-up/`, `theme-setup/`, `tags/`, `search/`, `search.json`,
   `home/`, `Bought-a-nexus/`, `nexus-without-data/`, `feed.xml`,
   `feed.xslt.xml`, `index.html~`, `favicon.*.orig`, and
   `documentation/jpilot-manual-de*`.
4. **`tarballs/` can go too** (4.8 MB). Nothing links to it any more: the
   three tarballs are published as GitHub release assets instead, verified
   byte-identical. `packages/` must stay -- the Download page still links
   those `.deb` files directly.
5. Keep: `CNAME`, `documentation/` (the manuals and their images),
   `packages/`, `ChangeLog`, `images/` (touch icons), `favicon.*`.
6. Merge to `gh-pages`.

## Checks that are already done

- `src/tools/check_links.py` passes on all 10 pages: no broken links, no
  unresolved template tokens, no unbalanced tags. It also refuses a link to a
  directory without an `index.html`, because GitHub Pages does not list
  directories -- that mistake was live on the Download page and looked fine to
  a naive checker.
- Every outbound link fetched at least once, and every GitHub release asset
  URL on the Download page returns 200.
- All seven release tarballs verified against their git tags, signatures
  checked, checksums confirmed. `v1_8_0` was found to be on the wrong commit
  and has been corrected.
