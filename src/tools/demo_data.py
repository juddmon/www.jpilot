#!/usr/bin/env python3
"""Generate invented J-Pilot records as CSV, for taking screenshots.

The screenshots on the site should never show anyone's real address book, and
an empty J-Pilot photographs badly, so this writes a small set of plausible
fictional records that J-Pilot can import.

    python3 src/tools/demo_data.py                  # ~/jpilot-demo/import
    python3 src/tools/demo_data.py --out DIR
    python3 src/tools/demo_data.py --date 2026-08-13

Then, importantly, load them into a *separate* J-Pilot home so they never
touch your own data:

    JPILOT_HOME=~/jpilot-demo jpilot

and use File > Import once per application, picking the matching CSV.

## Format notes, all taken from the J-Pilot 2.1.0 source

- `verify_csv_header` only counts commas, so the header line just has to have
  the right number of fields. The names are copied from what J-Pilot exports.
- Fields are then read positionally, in `schema[]` order for addresses.
- `read_csv_field` treats a bare space as a separator, so every field here is
  quoted -- "2026 08 13 09:00" would otherwise parse as four fields.
- Datebook times are `YYYY MM DD HH:MM`; to-do due dates are `YYYY/MM/DD`.
- Two databases have an old and a new form, and which one J-Pilot reads is a
  preference. Both are written: datebook/calendar and address/contacts. Import
  whichever one J-Pilot accepts -- if it is the wrong one it refuses with a
  comma-count message and imports nothing.
"""

import argparse
import datetime
import sys
from pathlib import Path

# Standard Palm phone labels, in the order J-Pilot matches them.
WORK, HOME, FAX, OTHER, EMAIL, MAIN, PAGER, MOBILE = (
    "Work", "Home", "Fax", "Other", "E-mail", "Main", "Pager", "Mobile",
)


def q(value):
    """Quote one CSV field. Everything is quoted -- see the note above."""
    return '"%s"' % str(value).replace('"', '""')


def row(*fields):
    return ",".join(q(f) for f in fields)


def write(path, header, rows):
    text = header + "\n" + "\n".join(rows) + "\n"
    path.write_text(text, encoding="utf-8")
    fields = header.count(",") + 1
    print("  %-34s %2d fields, %d records" % (path.name, fields, len(rows)))
    return fields


def datebook(out, day):
    """Appointments across the capture day, so the Datebook is not empty."""
    d = day.strftime("%Y %m %d")
    tomorrow = (day + datetime.timedelta(days=1)).strftime("%Y %m %d")
    friday = (day + datetime.timedelta(days=2)).strftime("%Y %m %d")

    # Category, Private, Description, Note, Event, Begin, End, Alarm, Advance,
    # Advance Units, Repeat Type, Repeat Forever, Repeat End, Repeat Frequency,
    # Repeat Day, Repeat Days, Week Start, Number of Exceptions, Exceptions
    def event(desc, note, begin, end, alarm=0, advance=0,
              rtype=0, forever=0, rend="", freq=0, rday=0, rdays="0000000",
              allday=0):
        return row("Unfiled", 0, desc, note, allday, begin, end, alarm,
                   advance, 0, rtype, forever, rend, freq, rday, rdays, 0, 0, "")

    rows = [
        event("Sync handheld", "", "%s 09:00" % d, "%s 09:15" % d),
        event("Project review", "Bring the revised schedule.",
              "%s 10:00" % d, "%s 11:00" % d, alarm=1, advance=15),
        event("Lunch with Dana", "", "%s 12:30" % d, "%s 13:30" % d),
        event("Dentist", "Corner of Fifth and Main.",
              "%s 15:00" % d, "%s 16:00" % d, alarm=1, advance=1),
        # A weekly repeat, so the repeat panel has something to show.
        event("Team standup", "", "%s 09:30" % tomorrow, "%s 09:45" % tomorrow,
              rtype=2, forever=1, freq=1, rdays="0100000"),
        event("Quarterly planning", "All day, upstairs.",
              "%s 00:00" % friday, "%s 00:00" % friday, allday=1),
    ]
    header = ("CSV datebook version 2.1.0: Category, Private, Description, Note, "
              "Event, Begin, End, Alarm, Advance, Advance Units, Repeat Type, "
              "Repeat Forever, Repeat End, Repeat Frequency, Repeat Day, "
              "Repeat Days, Week Start, Number of Exceptions, Exceptions")
    write(out / "datebook.csv", header, rows)

    # The Calendar form is the same, with Location inserted after Note.
    cal_rows = []
    places = ["", "Room 2", "The Anchor", "Dr Halloran", "Room 2", "Upstairs"]
    for text, place in zip(rows, places):
        parts = text.split('","')
        parts.insert(4, place)
        cal_rows.append('","'.join(parts))
    cal_header = header.replace("CSV datebook", "CSV calendar").replace(
        "Description, Note, Event", "Description, Note, Location, Event")
    write(out / "calendar.csv", cal_header, cal_rows)


def todo(out, day):
    """A mix of priorities, one completed, one with a note."""
    due = (day + datetime.timedelta(days=2)).strftime("%Y/%m/%d")
    soon = (day + datetime.timedelta(days=9)).strftime("%Y/%m/%d")
    # Category, Private, Indefinite, Due Date, Priority, Completed, Text, Note
    rows = [
        row("Unfiled", 0, 0, due, 1, 0, "Back up the handheld", ""),
        row("Unfiled", 0, 0, due, 2, 0, "Export contacts to vCard", ""),
        row("Unfiled", 0, 0, soon, 3, 0, "Order a replacement stylus",
            "The cheap ones scratch the digitiser."),
        row("Unfiled", 0, 1, "", 4, 0, "Read the plugin manual", ""),
        row("Unfiled", 0, 0, due, 2, 1, "Charge the cradle", ""),
    ]
    header = ("CSV todo version 2.1.0: Category, Private, Indefinite, Due Date, "
              "Priority, Completed, ToDo Text, Note")
    write(out / "todo.csv", header, rows)


def memo(out, day):
    rows = [
        row("Unfiled", 0,
            "Packing list\n\nCradle and USB cable\nSpare stylus\n"
            "Screen protector\nAA batteries"),
        row("Unfiled", 0,
            "Serial port settings\n\n/dev/ttyUSB0 at 57600 baud.\n"
            "Add yourself to the dialout group first."),
        row("Unfiled", 0,
            "Graffiti shortcuts\n\nBreakfast, lunch, dinner, meeting,\n"
            "and the date and time stamps."),
        row("Unfiled", 0,
            "Books to find\n\nThe one about the lighthouse keeper.\n"
            "Ask at the second-hand shop on Ferry Street."),
    ]
    header = "CSV memo version 2.1.0: Category, Private, Memo Text"
    write(out / "memo.csv", header, rows)


# Invented people. Names and numbers are made up; the 555 exchange and
# example.com are both reserved for exactly this.
PEOPLE = [
    dict(last="Okonkwo", first="Adaeze", title="Field Engineer",
         company="Harborline Instruments",
         phones=[(WORK, "555-0142"), (MOBILE, "555-0188"),
                 (EMAIL, "a.okonkwo@example.com"), (FAX, "555-0143"), (HOME, "")],
         street="118 Wharf Road", city="Portland", state="ME", zip="04101",
         country="USA", note="Prefers email. Handles the calibration rigs."),
    dict(last="Halloran", first="Bridget", title="Dentist",
         company="Fifth Street Dental",
         phones=[(WORK, "555-0119"), (EMAIL, "reception@example.com"),
                 (OTHER, ""), (HOME, ""), (MOBILE, "")],
         street="42 Fifth Street", city="Portland", state="ME", zip="04102",
         country="USA", note="Appointments before 9am if possible."),
    dict(last="Whitfield", first="Dana", title="Archivist",
         company="County Records Office",
         phones=[(WORK, "555-0167"), (MOBILE, "555-0171"),
                 (EMAIL, "d.whitfield@example.com"), (HOME, ""), (FAX, "")],
         street="9 Cathedral Close", city="Salisbury", state="", zip="SP1 2EF",
         country="England", note="Knows where the microfilm is kept."),
    dict(last="Reyes", first="Marcus", title="Proprietor",
         company="Anchor Hardware",
         phones=[(WORK, "555-0104"), (MAIN, "555-0105"), (HOME, ""),
                 (MOBILE, ""), (EMAIL, "")],
         street="2 Quay Street", city="Portland", state="ME", zip="04101",
         country="USA", note="Stocks the odd metric bolts."),
    dict(last="Lindqvist", first="Sofia", title="Translator", company="",
         phones=[(HOME, "555-0193"), (EMAIL, "s.lindqvist@example.com"),
                 (MOBILE, "555-0194"), (WORK, ""), (FAX, "")],
         street="Sveavagen 14", city="Stockholm", state="", zip="113 57",
         country="Sweden", note="Swedish and Finnish."),
    dict(last="Abara", first="Tomiwa", title="Instrument Maker", company="",
         phones=[(MOBILE, "555-0126"), (EMAIL, "t.abara@example.com"),
                 (HOME, ""), (WORK, ""), (OTHER, "")],
         street="7 Bell Lane", city="Bristol", state="", zip="BS1 4TR",
         country="England", note="Repaired the barometer."),
]


def address(out):
    """Address form: 27 fields, five phones each carrying its own label."""
    rows = []
    for p in PEOPLE:
        fields = [p["last"], p["first"], p["title"], p["company"]]
        for label, number in p["phones"][:5]:
            fields += [label, number]
        fields += [p["street"], p["city"], p["state"], p["zip"], p["country"]]
        fields += ["", "", "", ""]          # Custom 1-4
        fields += [p["note"], 0]            # Note, then which phone to show
        rows.append(row("Unfiled", 0, *fields))

    header = ("CSV address version 2.1.0: Category, Private, Last name, First name, "
              "Title, Company, Phone 0 label, Phone 0, Phone 1 label, Phone 1, "
              "Phone 2 label, Phone 2, Phone 3 label, Phone 3, Phone 4 label, "
              "Phone 4, Address, City, State, Zip Code, Country, Custom 1, "
              "Custom 2, Custom 3, Custom 4, Note, Show Phone")
    fields = write(out / "address.csv", header, rows)
    assert fields == 27, "address.csv must have 27 fields, got %d" % fields


def contacts(out):
    """Contacts form: 56 fields -- seven phones, two IM slots, three addresses."""
    rows = []
    for p in PEOPLE:
        f = [p["last"], p["first"], p["company"], p["title"]]
        phones = p["phones"] + [(WORK, ""), (WORK, "")]      # pad to seven
        for label, number in phones[:7]:
            f += [label, number]
        f += ["", "", "", ""]                                 # IM 1 and 2
        f += [""]                                             # Website
        f += ["Work", p["street"], p["city"], p["state"], p["zip"], p["country"]]
        f += ["Home", "", "", "", "", ""]                     # second address
        f += ["Other", "", "", "", "", ""]                    # third address
        f += ["", ""]                                         # Birthday, Reminder
        f += [""] * 9                                         # Custom 1-9
        f += [p["note"]]
        rows.append(row("Unfiled", 0, *f, 0))

    names = ["Category", "Private", "Last name", "First name", "Company", "Title"]
    for i in range(7):
        names += ["Phone %d label" % i, "Phone %d" % i]
    for i in range(2):
        names += ["IM %d label" % i, "IM %d" % i]
    names += ["Website"]
    for i in range(3):
        names += ["Address %d label" % i, "Address %d" % i,
                  "City", "State", "Zip Code", "Country"]
    names += ["Birthday", "Reminder Advance"]
    names += ["Custom %d" % i for i in range(1, 10)]
    names += ["Note", "Show Phone"]

    header = "CSV contacts version 2.1.0: " + ", ".join(names)
    fields = write(out / "contacts.csv", header, rows)
    assert fields == 56, "contacts.csv must have 56 fields, got %d" % fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(Path.home() / "jpilot-demo" / "import"))
    parser.add_argument("--date", default=None,
                        help="the day appointments land on (YYYY-MM-DD), default today")
    args = parser.parse_args()

    day = (datetime.date.fromisoformat(args.date) if args.date
           else datetime.date.today())
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    print("writing demo records for %s into %s" % (day.isoformat(), out))
    datebook(out, day)
    todo(out, day)
    memo(out, day)
    address(out)
    contacts(out)
    print("\nImport them into a separate J-Pilot home, never your own:")
    print("    JPILOT_HOME=~/jpilot-demo jpilot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
