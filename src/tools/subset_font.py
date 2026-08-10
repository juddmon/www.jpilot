#!/usr/bin/env python3
"""Subset the Ubuntu display font down to a woff2 the build can inline.

Only headings use the display font, and only at bold, so one weight over a
Latin character set is all the site needs -- about 15 KB instead of 350 KB.

The Ubuntu Font Licence (clause 2c) requires that a modified version which is
not substantially changed keep the original name and append "derivative X".
A subset is exactly that, so the family is renamed here and the copyright and
licence records are kept in the font's name table (clause 1).  The licence
text is shipped next to it as well.

Needs fonttools and brotli, so it is a one-off tool rather than part of
build.py -- the result is committed to src/static/fonts/ and the build just
inlines it.

    python3 src/tools/subset_font.py

On a Debian or Ubuntu box:  sudo apt install python3-fonttools python3-brotli
(or unpack those .debs somewhere and point PYTHONPATH at them).
"""

import shutil
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT_DIR = Path(__file__).resolve().parents[1] / "static" / "fonts"

# Ubuntu ships as a variable font.  Pinning the axes to a single instance
# before subsetting drops the variation tables, which are four fifths of the
# weight -- 14 KB out instead of 59 KB.
SOURCE = Path("/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf")
AXES = {"wght": 700, "wdth": 100}
LICENCE = Path("/usr/share/doc/fonts-ubuntu/copyright")

# Renamed per clause 2(c) of the Ubuntu Font Licence.  This string is also what
# site.css names in its @font-face rule, so change both together.
FAMILY = "Ubuntu derivative jpilot.org"
OUT_NAME = "ubuntu-700.woff2"

# The Google Fonts "latin" set: ASCII, Latin-1, the quotes and dashes that
# typography actually uses, the currency and arrow glyphs, and the replacement
# character.  Wide enough that new headings will not silently lose glyphs.
UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
    "U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2193,"
    "U+2212,U+2215,U+FEFF,U+FFFD"
)

# 0 copyright, 1/2/4/6 the family and style names, 13 licence, 14 licence URL.
KEEP_NAME_IDS = "0,1,2,3,4,5,6,13,14"


def rename(font, family):
    """Point every family-name record at the derivative name."""
    for record in font["name"].names:
        # 1 and 16 are the family name, 4 is the full name, 6 the PostScript
        # name.  Leaving any of them saying plain "Ubuntu" would misreport
        # what this file is.
        if record.nameID in (1, 16):
            record.string = family
        elif record.nameID == 4:
            record.string = family + " Bold"
        elif record.nameID == 6:
            record.string = family.replace(" ", "") + "-Bold"


def main():
    if not SOURCE.exists():
        print("error: %s not found -- install the fonts-ubuntu package" % SOURCE)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / OUT_NAME

    font = TTFont(str(SOURCE))
    font = instancer.instantiateVariableFont(font, AXES, updateFontNames=False)

    options = subset.Options()
    options.flavor = "woff2"
    options.desubroutinize = True
    options.layout_features = ["kern", "liga", "clig", "calt", "ccmp", "locl", "mark", "mkmk"]
    options.name_IDs = [int(i) for i in KEEP_NAME_IDS.split(",")]
    options.name_legacy = True
    options.notdef_outline = True
    options.drop_tables += ["DSIG"]

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
    subsetter.subset(font)

    rename(font, FAMILY)
    font.flavor = "woff2"
    font.save(str(out))
    font.close()

    print("wrote %s" % out)
    print("  %.1f KB, from %.1f KB" % (out.stat().st_size / 1024, SOURCE.stat().st_size / 1024))
    print("  family: %s" % FAMILY)

    # Clause 1: ship the copyright notice and licence with each copy.
    if LICENCE.exists():
        target = OUT_DIR / "UBUNTU-FONT-LICENCE.txt"
        shutil.copyfile(LICENCE, target)
        print("wrote %s" % target)
    else:
        print("warning: %s not found, licence text not copied" % LICENCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
