"""klava-ru's repair, run instead of recited.

The fragment in class `the-marker-write-counted-as-the-work-it-marks` keeps one
timestamp for two different facts: "when this job last ran" and "when it last
produced something worth reading". An empty batch therefore moves the marker
exactly as a real batch does.

The repair is structural, and it is cheap: two fields, two write paths.
`last_checked` advances on every run, because every run did happen.
`last_notified` advances only when the run produced something.

This script runs both versions on the same two sequences and prints the pair of
timestamps, so the difference is a measurement and not a description.
"""
CLOCK = [0]


def tick(seconds=60):
    CLOCK[0] += seconds
    return CLOCK[0]


class OneField:
    """A cursor and a marker share the only timestamp the job keeps."""

    def __init__(self):
        self.cursor = 0
        self.last_write = None

    def save_cursor(self, cursor):
        self.cursor = cursor
        self.last_write = tick()


class TwoFields:
    """The cursor advances on every run; the marker only on a useful one."""

    def __init__(self):
        self.cursor = 0
        self.last_checked = None
        self.last_notified = None

    def save_cursor(self, cursor, produced):
        self.cursor = cursor
        self.last_checked = tick()
        if produced > 0:
            self.last_notified = self.last_checked


def run(state, batches, two_fields):
    for batch in batches:
        produced = sum(1 for e in batch if e == "real")
        if two_fields:
            state.save_cursor(len(batch), produced)
        else:
            state.save_cursor(len(batch))
    return state


def question(marker, batches):
    """The marker the job reports after these batches."""
    CLOCK[0] = 0
    one = run(OneField(), batches, False)
    CLOCK[0] = 0
    two = run(TwoFields(), batches, True)
    return (getattr(one, "last_write", None),
            two.last_notified, two.last_checked)


BATCHES = [["real"], ["real", "empty"]]
REAL_ONLY = [["real"]]
EMPTY_TOO = [["real"], []]

print("batches                       one-field marker | two-field notified | two-field checked")
for name, batches in (("one real batch", REAL_ONLY), ("the same, then an empty tick", EMPTY_TOO)):
    a, b, c = question(None, batches)
    print(f"{name:29} {str(a):16} | {str(b):18} | {c}")

one_real = question(None, REAL_ONLY)
one_real_empty = question(None, EMPTY_TOO)
print()
print("the promise: the marker answers 'when did this job last produce something'")
print(f"  one field  : a useful run alone -> {one_real[0]}   with an empty tick after it -> {one_real_empty[0]}"
      f"   {'MOVED BY THE EMPTY TICK' if one_real[0] != one_real_empty[0] else 'stable'}")
print(f"  two fields : a useful run alone -> {one_real[1]}   with an empty tick after it -> {one_real_empty[1]}"
      f"   {'MOVED BY THE EMPTY TICK' if one_real[1] != one_real_empty[1] else 'stable'}")
print(f"  two fields : the cursor still advances every run -> {one_real_empty[2]} (was {one_real[2]})")
assert one_real[0] != one_real_empty[0], "the one-field probe no longer shows the bug"
assert one_real[1] == one_real_empty[1] == 60, "the repaired marker moved on an empty run"
assert one_real_empty[2] > one_real[2], "the repaired cursor stopped advancing"
print("\nrepair holds: the marker is stable on an empty run, the cursor is not.")
