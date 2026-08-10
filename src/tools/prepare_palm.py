#!/usr/bin/env python3
"""Prepare the hero photo of the PalmPilot 5000.

The Wikimedia original sits on a solid white background, which looks wrong in
dark mode.  This flood-fills the white from the edges to transparent, trims to
the device, and reports the LCD rectangle as percentages so the CSS overlay in
site.css can be positioned against it.

Needs Pillow, so it is a one-off tool rather than part of build.py -- the
result is committed to src/static/img/ and the build just copies it.

    python3 src/tools/prepare_palm.py path/to/Palmpilot5000_eu.png

Source: https://commons.wikimedia.org/wiki/File:Palmpilot5000_eu.png
Author: Channel R at English Wikipedia.  CC BY-SA 3.0 / GFDL 1.2+.
"""

import collections
import sys
from collections import deque
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "static" / "img" / "palmpilot5000.png"

# Only near-pure white counts as background. The fill deliberately stops at
# the first pixel of the outline rather than trying to judge how much of the
# ramp is background -- see knockout_background for why brightness cannot make
# that call.
BACKGROUND_CUTOFF = 245

# How far inside the background the outline can reach. The ramp measures one
# pixel almost everywhere; two gives corners room without mattering elsewhere,
# because a pixel that is really device solves to full opacity regardless.
FEATHER = 2


def knockout_background(im):
    """Flood-fill the white surround away, un-matting the anti-aliased edge.

    Filling from the edges rather than thresholding globally keeps the light
    details inside the device -- the silkscreened logo, the button icons.

    Simply clearing every pixel that looks white leaves a bright halo, because
    the pixels along the device's outline are a blend of white background and
    dark bezel. Deleting them outright gives a jagged edge; keeping them gives
    a white fringe that is invisible on a light page and obvious on a dark one.

    Brightness cannot decide which is which. Down the left edge the outline
    pixel reads 168, 201, 219, 123, 97, 58 on successive rows, while the
    device's own top bezel highlight runs to 152 -- any threshold both keeps
    part of the outline and eats part of the device, and does it differently
    on each row, which is what makes the result look ragged.

    So brightness only decides what is definitely background. Everything
    within FEATHER of that gets solved instead. The observed colour C is a mix
    of the background W and some foreground F, C = a*F + (1-a)*W. Taking F
    from the solid device pixels behind it gives the coverage a, and dividing
    the background back out recovers F. This is safe to apply generously: a
    pixel that is really device already equals F, so it solves to a = 1 and
    comes back unchanged.
    """
    w, h = im.size
    px = im.load()
    background = bytearray(w * h)
    queue = deque()

    def is_background(x, y):
        r, g, b, _ = px[x, y]
        return min(r, g, b) >= BACKGROUND_CUTOFF

    for x in range(w):
        queue.extend(((x, 0), (x, h - 1)))
    for y in range(h):
        queue.extend(((0, y), (w - 1, y)))

    while queue:
        x, y = queue.popleft()
        if not (0 <= x < w and 0 <= y < h) or background[y * w + x]:
            continue
        if not is_background(x, y):
            continue
        background[y * w + x] = 1
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # The outline: everything solid that lies within reach of the background.
    outline = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            if background[y * w + x]:
                continue
            for dy in range(-FEATHER, FEATHER + 1):
                for dx in range(-FEATHER, FEATHER + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and background[ny * w + nx]:
                        outline[y * w + x] = 1
                        break
                if outline[y * w + x]:
                    break

    def solid_behind(x, y):
        """Darkest pixel near (x, y) that is neither background nor outline."""
        near = None
        for dy in range(-FEATHER - 2, FEATHER + 3):
            for dx in range(-FEATHER - 2, FEATHER + 3):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                if background[ny * w + nx] or outline[ny * w + nx]:
                    continue
                candidate = px[nx, ny][:3]
                if near is None or min(candidate) < min(near):
                    near = candidate
        return near

    cleared = feathered = 0
    for y in range(h):
        for x in range(w):
            if background[y * w + x]:
                px[x, y] = (255, 255, 255, 0)
                cleared += 1
                continue
            if not outline[y * w + x]:
                continue

            near = solid_behind(x, y)
            if near is None:
                continue

            # Coverage from whichever channel separates foreground from white
            # most strongly -- the widest gap is the least noisy estimate.
            colour = px[x, y][:3]
            alpha = 0.0
            for channel in range(3):
                spread = 255 - near[channel]
                if spread > 8:
                    alpha = max(alpha, (255 - colour[channel]) / spread)
            alpha = min(1.0, max(0.0, alpha))

            if alpha >= 0.996:
                continue
            if alpha <= 0.004:
                px[x, y] = (255, 255, 255, 0)
                cleared += 1
                continue

            # Divide the white back out to recover the true foreground.
            recovered = tuple(
                min(255, max(0, round((colour[c] - (1 - alpha) * 255) / alpha))) for c in range(3)
            )
            px[x, y] = recovered + (round(alpha * 255),)
            feathered += 1

    print("  cleared %d background pixels, feathered %d outline pixels" % (cleared, feathered))
    return im


def screen_rect(im):
    """Bounding box of the green LCD, used to place the CSS overlay."""
    w, h = im.size
    px = im.load()
    rows, cols = collections.Counter(), collections.Counter()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and g > r + 18 and g > b + 18 and g > 90:
                rows[y] += 1
                cols[x] += 1
    ys = [y for y in sorted(rows) if rows[y] > 150]
    xs = [x for x in sorted(cols) if cols[x] > 150]
    return xs[0], ys[0], xs[-1], ys[-1]


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    im = Image.open(argv[1]).convert("RGBA")
    im = knockout_background(im)
    im = im.crop(im.getbbox())

    w, h = im.size
    x0, y0, x1, y1 = screen_rect(im)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # A palette PNG takes this from ~330 KB to ~58 KB.  The photo is almost
    # entirely greys and greens, so 255 colours plus transparency is plenty.
    im.quantize(colors=255, method=Image.FASTOCTREE).save(OUT, optimize=True)

    print("wrote %s  %dx%d  %.1f KB" % (OUT, w, h, OUT.stat().st_size / 1024))
    print("aspect-ratio: %d / %d" % (w, h))
    print("LCD rect, as percentages of the trimmed image -- use these in site.css:")
    print("  left:   %.2f%%" % (100 * x0 / w))
    print("  top:    %.2f%%" % (100 * y0 / h))
    print("  width:  %.2f%%" % (100 * (x1 - x0 + 1) / w))
    print("  height: %.2f%%" % (100 * (y1 - y0 + 1) / h))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
