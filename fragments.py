"""Minimal reproductions of the lie-classes listed in catches.json.

These are NOT the authors' bytes. Each function is a smallest-possible
reproduction of a class that was killed in the game on the board, written
so that `check.py` can re-run the probe and confirm the divergence is real.
Where an author's original body differed in cosmetics, the class is what is
kept, not the spelling.
"""

import ast
import builtins
import datetime
import hashlib
import json
import pickle


# ---------------------------------------------------------------- python

def clamp(val, low, high):
    """Clamp val to the inclusive range [low, high].
    If low > high, raises ValueError."""
    return min(max(val, low), high)


def split_tags(s):
    """Split s on commas and drop empty tags."""
    return [t for t in s.split(",") if t]


def remove_all(items, value):
    """Remove every element equal to value."""
    for i, item in enumerate(items):
        if item == value:
            del items[i]
    return items


def remove_outliers(items, limit):
    """Remove every element above limit."""
    for i, item in enumerate(items):
        if item > limit:
            del items[i]
    return items


def dedupe_sorted(xs):
    """Return the unique elements of xs, keeping the input order."""
    return sorted(set(xs))


def title_case(s):
    """Capitalise the first letter of each word in s."""
    return s.title()


def dedupe_adjacent(xs):
    """Collapse equal elements anywhere in the list to one."""
    out = []
    for x in xs:
        if not out or out[-1] != x:
            out.append(x)
    return out


def strip_tags(s):
    """Remove HTML tags from s."""
    import re

    return re.sub(r"<.*>", "", s)


def floor_div(a, b):
    """Integer floor division of a by b."""
    return int(a / b)


def clip(s, n):
    """Truncate s to n characters.
    If n is negative, return the empty string (do not reverse-slice)."""
    return s[:n]


def partition(pred, items):
    """Split items into two lists (matching, non_matching).
    Preserves the relative order of elements from items in each list."""
    matching, non_matching = [], []
    for x in items:
        if pred(x):
            matching.append(x)
        else:
            non_matching.insert(0, x)
    return matching, non_matching


def sliding_window(seq, size, step=1):
    """Generate sliding windows of given size over seq.
    Step defaults to 1 (overlapping windows).
    Last partial window is included if size > 0."""
    if size <= 0:
        return
    for i in range(0, len(seq) - size + 1, step):
        yield seq[i : i + size]


def next_after(events):
    """Highest seq observed in `events`, so it is safe to resume
    pagination from the returned value even when pages arrive
    out of order."""
    return events[-1]["seq"]


def pad_left(s, n, fill=" "):
    """Pad s on the left to width n. If s is longer than n, return s unchanged."""
    return (fill * n + s)[-n:]


def to_ascii(s):
    """Replace non-ASCII characters in s with '?'."""
    return s.encode("ascii", "ignore").decode("ascii")


def to_int(s):
    """Convert s to an int; if s cannot be parsed as an integer, return None instead of raising."""
    return int(s) if s else None


def is_sorted(xs):
    """True for non-decreasing sequences."""
    return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))


def sum_and_count(items):
    """Return the sum and the count of items."""
    return sum(items), sum(1 for _ in items)


def make_grid(rows, cols):
    """Build a rows x cols grid of zeroes, one independent list per row."""
    return [[0] * cols] * rows


def touch_grid(rows, cols):
    """Write into the first cell of the first row and read the first cell of the second."""
    grid = make_grid(rows, cols)
    grid[0][0] = 1
    return grid[1][0]


def binary_search(xs, target):
    """Return the index of the first occurrence of target in the sorted list xs, or -1."""
    lo, hi = 0, len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_intervals(intervals):
    """Merge intervals that overlap or touch."""
    out = []
    for start, end in sorted(intervals):
        if out and start < out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def with_retry(fn, attempts=3):
    """Call fn up to attempts times; raise the last error when they run out."""
    for _ in range(attempts):
        try:
            return fn()
        except Exception:
            pass
    return None


def fail_always():
    raise RuntimeError("boom")


def is_palindrome(s):
    """True if s reads the same forwards and backwards, ignoring case and punctuation."""
    cleaned = s.lower()
    return cleaned == cleaned[::-1]


def is_palindrome_number(n):
    """True for palindromic integers."""
    s = str(n)
    return s == s[::-1]


def remove_prefix_suffix(s, prefix, suffix):
    """Remove the given prefix and suffix from s."""
    return s.strip(prefix + suffix)


def median(xs):
    """Return the median of xs."""
    xs = sorted(xs)
    return xs[len(xs) // 2]


def flatten(xs):
    """Flatten nested lists into a single list."""
    return [x for item in xs for x in (item if isinstance(item, list) else [item])]


def rotate(xs, k):
    """Rotate xs left by k, wrapping when k is larger than the length."""
    return xs[k:] + xs[:k]


def get_extension(name):
    """Return the file extension of name, including the dot."""
    return name[name.index(".") :] if "." in name else name


def round_half_up(x):
    """Round x to the nearest integer, halves away from zero."""
    return round(x)


class ConfigError(Exception):
    """Raised for a malformed configuration file."""


def load_config(path):
    """Load a JSON config, raising ConfigError when it is malformed."""
    with open(path) as fh:
        return json.load(fh)


def load_config_inline(_ignored=None):
    """Same lie, no fixture file: json.loads of malformed text, not ConfigError."""
    return json.loads("{oops}")


def interleave(a, b):
    """Interleave elements from two sequences a and b alternately.
    If sequences are unequal in length, remaining elements from the longer sequence are appended."""
    result = []
    for x, y in zip(a, b):
        result.extend([x, y])
    return result


def parse_kv_pairs(s):
    """Parses 'key=value' pairs separated by ';' into a dict, stripping
    surrounding whitespace from both key and value."""
    result = {}
    for pair in s.split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v
    return result


def is_palindrome_ignore_case(s, ignore_case=False):
    """Check whether s is a palindrome.
    Ignores case and non-alphanumeric characters by default."""
    cleaned = [c for c in s if c.isalnum()]
    if ignore_case:
        cleaned = [c.lower() for c in cleaned]
    return cleaned == cleaned[::-1]


def count_unique(xs):
    """Count distinct elements of xs. None is counted as a distinct value."""
    return len({x for x in xs if x is not None})


def compact_dict(d):
    """Return a new dict omitting any keys whose values are None."""
    return {k: v for k, v in d.items() if v}


def count_lines(text):
    """Count the number of lines in text. A final line without a trailing newline still counts."""
    if not text:
        return 0
    return text.count("\n")


def merge_dicts(a, b):
    """Merge b into a copy of a. On key collision, keep a's value (first wins)."""
    out = dict(a)
    out.update(b)
    return out


def all_positive(nums, log):
    """Checks every number in nums, recording each one's pass/fail
    result in log, and returns True only if all numbers are positive."""
    def check(n):
        ok = n > 0
        log.append(ok)
        return ok
    return all(check(n) for n in nums)


def lines(text):
    """Split text into lines, keeping the trailing newline on each line that had one."""
    return text.splitlines()


def sanitize_path(path):
    """Normalize a path by removing trailing slashes, keeping the root slash if present."""
    return path.rstrip("/") or "/"


def remove_duplicates(seq):
    """Remove duplicates while preserving element types and insertion order."""
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def halves(n):
    """Return n divided by 2 as an integer (floor)."""
    return n / 2


def last_line(text):
    """Return the last line of text, without a trailing newline."""
    return text.split("\n")[-1]


def clone_matrix_one(matrix):
    """Return an independent deep copy of matrix; mutating the clone never touches the original."""
    return [row[:] for row in matrix]


def merge_prefer_second(a, b):
    """Merge two dicts; on key conflicts, values from `b` (the second argument) win."""
    return {**b, **a}


def remove_suffix_rstrip(text, suffix):
    """Return text with the given suffix removed if it ends with suffix, else return text unchanged."""
    return text.rstrip(suffix)


def lookup(d, key, default=None):
    """Return d[key] if present, else default. A stored None is a present value."""
    return d.get(key) or default


def is_divisible(n, d):
    """Return True if n is divisible by d, False otherwise. Raises ValueError if d is zero."""
    if d == 0:
        ValueError("d cannot be zero")
    return n % d == 0


def with_appended(lst, item):
    """Return a new list with item appended, leaving the original list untouched."""
    lst.append(item)
    return lst


def is_valid_identifier(name):
    """Return True if name can be used as a valid Python variable identifier, False otherwise."""
    return name.isidentifier()


def join_fields(parts, sep=","):
    """Join every part as text. None becomes the empty string."""
    return sep.join(parts)


def is_empty(container):
    """Return True if container has no elements; works for any collection type."""
    return container == []


def wrap_line(text, width):
    """Wrap text to width without breaking words. If a word is longer than width, keep it intact on its own line."""
    return [text[i : i + width] for i in range(0, len(text), width)]


def safe_int(val, default=0):
    """Parse val as int, or return default if conversion fails."""
    try:
        return int(val)
    except ValueError:
        return default


def redact(text, old, new):
    """Replace every occurrence of old with new."""
    return text.replace(old, new, 1)


def capitalize_first(text):
    """Capitalizes the first character of text, leaving all other characters unchanged."""
    return text.capitalize()


def contains_word(text, word):
    """Checks whether word appears as a standalone word in text."""
    return word in text



def sorted_copy(items):
    """Return a new list of items in sorted order; items itself is unchanged."""
    items.sort()
    return items


def extend_unique(target, items):
    """Appends items to target only if they are not already present in target."""
    seen = set(target)
    for item in items:
        if item not in seen:
            target.append(item)
    return target


class Cart:
    """A per-session shopping cart."""
    items = []

    def add(self, item):
        """Add item to this cart only; other Cart instances are unaffected."""
        self.items.append(item)


def new_cart():
    """Return a fresh, empty cart independent of any other cart."""
    return Cart()


def initialize_user_scores(usernames):
    """Creates a mapping from each username to an independent empty list of scores."""
    return dict.fromkeys(usernames, [])


def take_while_positive(nums):
    """If no non-positive, return an independent copy of nums."""
    for i, x in enumerate(nums):
        if x <= 0:
            return nums[:i]
    return nums


def count_integers(items):
    """Count how many elements in items are integers.

    Booleans and non-integer types are excluded from the count.
    """
    return sum(1 for x in items if isinstance(x, int))


def last_index(hay, needle):
    """Return the last index of needle in hay, or -1 if absent.
    An empty needle is found at the end of hay (len(hay))."""
    if needle == "":
        return -1
    return hay.rfind(needle)


def append_log(entry, log=[]):
    """Appends entry to log and returns it. Without an explicit log, each call starts from a fresh empty list."""
    log.append(entry)
    return log


def index_of_or_none(items, target):
    """Return the 0-based index of target in items, or -1 if target is not found."""
    try:
        return items.index(target)
    except ValueError:
        return None


def take(xs, n):
    """Return the first n items of xs. If n is negative, return an empty list."""
    return xs[:n]


def starts_with(s, prefix):
    """Return True iff s starts with prefix. An empty prefix matches every string."""
    if not prefix:
        return False
    return s[: len(prefix)] == prefix


def split_once(s, sep):
    """Split s on the first occurrence of sep only. At most two parts."""
    return s.split(sep)


def find_max(items):
    """Return the largest value in items, or None if items is empty."""
    return max(items)


def truncate_text(text, max_len, suffix="..."):
    """Truncates text to max_len characters including the suffix if text exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + suffix


def format_bytes(n):
    """Format a byte count using binary units (1024-based), e.g. 2048 -> \"2.0 KB\"."""
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1000:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def first_true(pred, items, default=None):
    """Return the first item for which pred is true, or default.
    Items are not copied; the original sequence is left unchanged."""
    for x in items:
        if pred(x):
            return x
    items.append(default)
    return default


def average(nums):
    """Return the arithmetic mean of nums as a float.
    Handles empty lists by returning 0.0."""
    return sum(nums) / len(nums)


def trim(s):
    """Return s with leading and trailing whitespace removed.
    The empty string and whitespace-only strings become ''."""
    s = s.strip()
    return s or None


def index_of(xs, value):
    """Return the index of the first occurrence of value in xs, or -1."""
    found = -1
    for i, x in enumerate(xs):
        if x == value:
            found = i
    return found


def batch_average(numbers, batch_size=5):
    """Yield the arithmetic mean of successive batches of numbers.
    Any final partial batch is averaged over its actual count."""
    for i in range(0, len(numbers), batch_size):
        yield sum(numbers[i : i + batch_size]) / batch_size


def join_path(*parts):
    """Join path parts with /. An absolute part (starting with /) replaces the accumulated path."""
    return "/".join(p.strip("/") for p in parts)


def chunked(seq, n, fill=None):
    """Yield successive n-sized chunks from seq.
    If the last chunk has fewer than n elements, it is padded with fill.
    If fill is omitted, the last chunk is yielded as-is (short)."""
    if n <= 0:
        return
    it = iter(seq)
    while True:
        chunk = []
        for _ in range(n):
            try:
                chunk.append(next(it))
            except StopIteration:
                if chunk:
                    yield chunk
                return
        yield chunk


def make_multipliers():
    """Return three functions; the i-th multiplies its argument by i."""
    return [lambda x: x * i for i in range(3)]


# ---------------------------------------------------------- repeat fragments
# One function per repeat that has been materialised, plus the class fragment the
# repeat should have been written against where an earlier edit dropped it.
# The names describe the bytes, not an author: a repeat is a second sighting of a
# shape, and the ledger does not hand out credit. check.py refuses a repeat whose
# fragment fingerprints identically to the class fragment it claims to repeat.


def clamp_branch_swapped(value, lo, hi):
    """Clamp value into [lo, hi]; works even if lo and hi are swapped."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def parse_tags_keep_ws_only(tag_str):
    """Split comma-separated tags, strip each, and omit empty tags."""
    return [t.strip() for t in tag_str.split(",") if t]


def remove_outliers_inplace(data, limit):
    """Remove every value above limit from data in place and return data."""
    for item in data:
        if item > limit:
            data.remove(item)
    return data


def clamp_minmax_reversed(x, lo, hi):
    """Return x limited to [lo, hi]. If lo > hi, swap them first."""
    return max(lo, min(hi, x))


def is_valid_port(n):
    """True when n is a valid TCP port number."""
    return 0 < n < 65535


def remove_one_only(items, value):
    """Remove every occurrence of value from items and return items."""
    items.remove(value)
    return items


def conversion_rate(clicks, views):
    """Overall conversion rate across groups: every group counts in proportion to its views."""
    return sum(c / v for c, v in zip(clicks, views)) / len(views)


def remove_all_joi(items, target):
    """Return a new list without target; the input list is not modified."""
    new_items = list(items)
    for x in new_items:
        if x == target:
            new_items.remove(x)
    return new_items


def as_iter_reusable(items):
    """Wrap items so it can be consumed repeatedly, like a fresh copy each time."""
    return (x for x in items)


def remove_prefix_lstrip(s, prefix):
    """Remove prefix from s if s starts with it, otherwise return s unchanged."""
    if s.startswith(prefix):
        return s.lstrip(prefix)
    return s


def round_int_plus_half(x):
    """Round x to the nearest integer; ties round toward positive infinity."""
    return int(x + 0.5)



# --- recovered: labels whose bytes were still on hand (see recover_labels.py)

def dedupe_adjacent_rec(items):
    """Remove all duplicate elements, keeping only the first occurrence
    of each value."""
    result = []
    for i, x in enumerate(items):
        if i == 0 or x != items[i - 1]:
            result.append(x)
    return result

def title_case_rec(s: str) -> str:
    """Capitalize the first letter of every word.
    The rest of each word's letters are left untouched."""
    return s.title()

def dedupe_sorted_rec(items):
    """Remove consecutive duplicate values from a sorted list and return
    the result, without modifying the original list."""
    i = 0
    while i < len(items) - 1:
        if items[i] == items[i + 1]:
            del items[i + 1]
        else:
            i += 1
    return items

def unique_rec(items):
    """Return a new list with duplicates removed, preserving original order."""
    return list(set(items))

def round_price_rec(x):
    """Round x to 2 decimal places, exact to the cent."""
    return round(x, 2)

def pairs_rec(items):
    """Return consecutive pairs. A leftover last item becomes a one-element group."""
    return list(zip(items[::2], items[1::2]))

def clone_matrix_rec(matrix):
    """Return an independent copy of matrix; mutating a row in the copy never affects the original."""
    return [row for row in matrix]

def min_max_rec(items):
    """Returns the minimum and maximum values from any iterable of numbers."""
    return min(items), max(items)

def strip_prefix_rec(text: str, prefix: str) -> str:
    """Remove prefix from text if text starts with prefix, else return text unchanged."""
    if text.startswith(prefix):
        return text.lstrip(prefix)
    return text

def remove_prefix_suffix_rec(s, chars):
    """Remove the substring `chars` from the start and end of s, if present."""
    return s.strip(chars)


def last_n(items, n):
    """Return the last n items, or all of them if the list is shorter than n."""
    return items[-n:]


def tail_fix(items, n):
    """Return the last n items, or all of them if the list is shorter than n."""
    return items[len(items) - n:]


def is_weekend(d):
    """True when d falls on a weekend."""
    return d.weekday() > 5



def truncate(text, width):
    """Cut text to width characters, adding an ellipsis when it was longer."""
    return text[:width] + ("…" if len(text) > width else "")


def split_pair(s):
    """Split 'a=b' into its two parts; a missing part is the empty string."""
    return s.split("=", 1)



def same_word(a, b):
    """True when a and b are the same word, ignoring case."""
    return a.lower() == b.lower()



def same_text(a, b):
    """True when a and b are the same text."""
    return a is b



def merge_counts(a, b):
    """Return the sum of all counts in both mappings."""
    out = dict(a)
    out.update(b)
    return out



def parse_int(s):
    """Parse an integer written in decimal, with or without a trailing ".0" (as spreadsheets export it), and return it exactly."""
    return int(float(s))



def is_int_string(s):
    """True exactly when int(s) would succeed."""
    return s.isdigit()


def roll_fingerprint(items, read_at):
    """A fingerprint of the roll, so two readers can compare one observable."""
    blob = json.dumps({"read_at": read_at, "items": items},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _reduce_items(items):
    out = [{"seq": it["seq"], "agent_id": it["agent_id"], "ranking": it["ranking"]}
           for it in items]
    out.sort(key=lambda x: (x["agent_id"], x["seq"]))
    return out


def roll_digest(capture):
    """A fingerprint of the roll, so two readers can compare one observable."""
    blob = json.dumps({"election_id": capture["election_id"],
                       "votes_cast": capture["votes_cast"],
                       "items": _reduce_items(capture["items"])},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


ROLL_DIGEST_RECIPE = ("items reduced to seq/agent_id/ranking, sorted by agent_id, "
                      "sort_keys, separators (',', ':'), UTF-8, sha256")


def digest_from_recipe(capture):
    """The number a reader gets who follows ROLL_DIGEST_RECIPE to the letter."""
    blob = json.dumps(_reduce_items(capture["items"]), sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def digest_from_recipe_default_separators(capture):
    """The number a reader gets who follows that same recipe and never mentions
    separators, so json.dumps supplies its defaults."""
    blob = json.dumps(_reduce_items(capture["items"]), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def first_preference(ranking, options):
    """The ballot's first preference, options being everything a ballot may
    name -- the candidates and vacancy alike."""
    return next((x for x in ranking if x in options), None)


def verdict_stop(leader_support, majority, floor):
    """Cited: "A majority below the floor is not a win: the candidate needs both a strict majority this round and at least F supporters."

    Read here as: the count stops there and the office stays vacant.
    """
    if leader_support < majority:
        return "continue_counting"
    if leader_support < floor:
        return "floor_not_met"
    return "elected"


def verdict_continue(leader_support, majority, floor):
    """The same cited sentence, read as: a majority below the floor is merely
    not a win, so the count runs on and the leader is unprotected."""
    if leader_support < majority:
        return "continue_counting"
    if leader_support < floor:
        return "continue_counting"
    return "elected"


def digest_from_listed_fields(record):
    """A fingerprint of the record, fields in the order the page lists them."""
    return hashlib.sha256(
        json.dumps(record, separators=(",", ":")).encode("utf-8")).hexdigest()


def digest_from_sorted_fields(record):
    """A fingerprint of the record, fields in an order the recipe fixes."""
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def capture_is_whole(page):
    """The read is whole once the page reports itself complete."""
    return bool(page.get("complete"))



def forms_a_length_gate_admits(forms, published):
    """The forms worth comparing: the ones whose byte length matches."""
    n = len(forms[published])
    return sorted(k for k, v in forms.items() if len(v) == n)



def cross_checked(record, page):
    """Agreed with the record: the same number, stated the same way twice."""
    return all(record.get(k) == page.get(k) for k in ("votes_cast", "ballots_cast"))


def seam_offset(row, k):
    """Distance between my column and the neighbour's at inset k."""
    return abs(row[299 - k] - row[k])


def witnessed_fields(record, page):
    """Checked against the record: the fields named here."""
    return {k: page[k] for k in ("votes_cast",) if k in record}


def render_counts(counts):
    """Every option with its count."""
    return ", ".join(f"{k}={v}" for k, v in counts.items() if v)


def same_height(a, b):
    """True when a and b stand at the same height."""
    return round(a) == round(b)


SKY = "S"
GROUND = "G"
HIGHLIGHT = "H"


def ground_top(column):
    """Return the row where the ground begins in the column."""
    for i, value in enumerate(column):
        if value == GROUND:
            column[i] = HIGHLIGHT
            break
    for i, value in enumerate(column):
        if value == GROUND:
            return i
    return -1


class Clock:
    """A clock that moves only when something writes to it."""

    def __init__(self):
        self.now = 0

    def tick(self, seconds=60):
        self.now += seconds
        return self.now


class JobState:
    """What a recurring job keeps between runs: where it got to, and when it last wrote."""

    def __init__(self, clock):
        self.clock = clock
        self.cursor = 0
        self.last_write = None

    def save_cursor(self, cursor):
        self.cursor = cursor
        self.last_write = self.clock.tick()

    def last_useful_run(self):
        """The moment this job last produced something worth reading."""
        return self.last_write


def run_once(clock, state, events):
    """Handle one batch of events; return how many of them produced output."""
    produced = sum(1 for event in events if event == "real")
    state.save_cursor(len(events))
    return produced


def last_useful_run(events_by_run):
    """Run the job over successive batches; return when it last produced output."""
    clock = Clock()
    state = JobState(clock)
    for events in events_by_run:
        run_once(clock, state, events)
    return state.last_useful_run()


def border_runs(values):
    """The border of an edge as runs of equal colour."""
    out = []
    for v in values:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def rule_verdict(border_mine, border_theirs, tolerance=70):
    """The wall's published verdict: every run that reaches the border has a
    counterpart on the other side of it."""
    theirs = border_runs(border_theirs)
    for colour, _ in border_runs(border_mine):
        if not any(abs(colour - other) <= tolerance for other, _ in theirs):
            return "unmatched"
    return "clean"


def stricter_count(band_mine, band_theirs, tolerance=70):
    """The same two edges, counted over every sample of the edge band instead of
    over the runs at the border: a pair the rule calls clean can fail here."""
    return sum(
        1
        for row_a, row_b in zip(band_mine, band_theirs)
        for a, b in zip(row_a, row_b)
        if abs(a - b) > tolerance
    )


def the_last_body_the_walk_reaches(door_answers, my_key=None):
    """What a walk over one path answers, given the credential it holds.

    The same path, the same method, the same headers, two credentials. Without a
    key the walk stops at the credential rung and its last body is the one in
    front of that rung; with a key it passes and its last body is the route's
    own. A quoted body is therefore not a property of the path until the
    credential is named beside it.
    """
    seen = []
    for needs_key, body in door_answers:
        if needs_key and my_key is None:
            break
        seen.append(body)
    return seen[-1] if seen else None


def the_last_body_is_the_routes_own(the_same_path):
    """A refusal quoted as the route's own, read off the far side of the rung."""
    ladder = [(False, "200 7569"), (True, "401 141"), (False, "404 132")]
    return (the_same_path(ladder) == the_same_path(ladder, my_key="k"))


def contiguous_through(items, resume_from):
    """The last seq of the unbroken run that starts just after resume_from."""
    seen = {i["seq"] for i in items}
    cursor = resume_from
    while cursor + 1 in seen:
        cursor += 1
    return cursor, sorted(s for s in seen if s > cursor)


def resume_trace(pages, start=0):
    """The cursor after each page, when a stream is read page by page."""
    trace = []
    cursor = start
    for page in pages:
        cursor, _ = contiguous_through(page, cursor)
        trace.append(cursor)
    return trace


EDGE, LINE = (224, 224, 224), (32, 32, 32)


def dist(a, b):
    """The rule's colour distance: Euclidean over RGB."""
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

def what_the_band_hides(border, band, tol, edge_tone):
    """Positions where the band leaves the edge tone only inside the band.

    The rule reads runs AT the border. A position whose border sample is itself
    a line is therefore read by the rule already, whatever the band holds behind
    it, and is not a position the rule cannot see.
    """
    out = []
    for j, row in enumerate(band):
        if dist(row[1], border[j]) > tol:
            if dist(border[j], edge_tone) <= tol:
                out.append(j)
    return out


def what_the_band_hides_ignoring_the_border(border, band, tol, edge_tone):
    """The same question, asked of the band alone.

    Every position whose band leaves its own border sample inside counts, whether
    or not the rule can read that border sample. On a border that carries a line
    this reports the line's own positions as hidden ink, and names the tone
    behind the line as the ink the rule cannot see.
    """
    return [j for j, row in enumerate(band) if dist(row[1], border[j]) > tol]


def shelf_floor(n, lo=5):
    """The published threshold for an electorate of n: max(5, ceil(3n/10))."""
    return max(lo, -(-3 * n // 10))


def the_shelf(observed, lo=5, hi=400):
    """Every electorate size the published rule gives this same threshold to."""
    return [n for n in range(lo, hi + 1) if shelf_floor(n, lo) == observed]


def the_reading_agrees_with(n, observed, lo=5):
    """The threshold agrees with n, so n is what the reading names."""
    return shelf_floor(n, lo) == observed


def margin_from_one_end(n_read, observed, direction, lo=5, cap=400):
    """How far n may move one way before the threshold leaves the reading."""
    step = 1 if direction == "up" else -1
    n, moved = n_read, 0
    while lo <= n + step <= cap and shelf_floor(n + step, lo) == observed:
        n += step
        moved += 1
    return moved


def the_margin_is_the_shelf(n_read, observed, shelf):
    """True when the shelf's width is the reading's distance to its far end."""
    lo, hi = shelf
    return abs(n_read - lo) == (hi - lo)


def how_many_met(mine, theirs, tol=70):
    """How many of my runs met one of theirs."""
    met = 0
    for m in mine:
        for t in theirs:
            if dist(m, t) <= tol:
                met += 1
    return met


def colour_steps(border):
    """The runs on a border: every position whose colour differs from the previous one."""
    return sum(1 for i in range(1, len(border)) if border[i] != border[i - 1])


def the_rule_run_count(border, tol=70):
    """The runs the wall's rule reads: chained at the rule's own Euclidean distance."""
    runs, start = 1, 0
    for i in range(1, len(border)):
        if sum((a - b) ** 2 for a, b in zip(border[i], border[start])) ** 0.5 > tol:
            runs += 1
            start = i
    return runs


def _ramp(n=300, span=15):
    """A border that climbs 20 colours in equal steps, none of them 70 apart."""
    return [(11 + i // span, 15 + i // span, 30 + i // span) for i in range(n)]



def edge_profile(rows_a, rows_b, kmax=14, tol=70):
    """A seam as a profile over insets: the border row and every row inside the band."""
    out = {}
    for k in range(kmax + 1):
        d = [dist(x, y) for x, y in zip(rows_a[k], rows_b[k])]
        over = [i for i, v in enumerate(d) if v > tol]
        out[k] = {"worst": max(d), "over": len(over),
                  "span": (over[0], over[-1]) if over else None}
    return out


def receipt_digest(text):
    """The digest of what a run said, so two readers can compare one observable."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def demo_receipt(keys):
    """The digest of a demonstration's receipt, given the two stream keys it minted."""
    text = ("refused on keys: cursor from 'seq' (key {}) offered to 'seq' (key {})"
            .format(*keys))
    return receipt_digest(text)


def the_seam_agrees(a, b, tol=70):
    """Whether the two pictures agree at this seam."""
    return all(dist(x, y) <= tol for x, y in zip(a[0], b[0]))


def observation_log(observations):
    """The state of each object, from (view, obj_id, verdict) observations."""
    log = {}
    for _view, obj_id, verdict in observations:
        log[obj_id] = verdict
    return log


def log_is_a_fact_about_the_object(observations):
    """True when the log holds a fact about the object it is keyed by."""
    log = observation_log(observations)
    for _view, obj_id, verdict in observations:
        if log[obj_id] == verdict:
            return True
    return False


def the_fact_about_the_object(observations, obj_id):
    """The verdict on obj_id, or None when the views do not agree about it."""
    verdicts = {verdict for _view, o, verdict in observations if o == obj_id}
    return verdicts.pop() if len(verdicts) == 1 else None


def remedy_names_the_state(sent_key, recognised_key):
    """True when the remedy printed for this request names the state it is in."""
    remedy = ("Invalid or revoked API key." if recognised_key
              else "Send your API key as Authorization: Bearer <key>.")
    if not sent_key:
        return remedy.startswith("Send your API key")
    return not remedy.startswith("Send your API key")


def two_reads_one_receipt(body_a, body_b):
    """True when two reads of one door give one receipt."""
    return receipt_digest(body_a) == receipt_digest(body_b)


RAMP = _ramp()

# Withdrawn 2026-09-24: kept as the artifact of a misreading, not as a class.
# The live contract declares can_vote as eligibility and keeps the daily
# allowance enforced beside it, so True here is the declared answer, not a lie.
def may_vote(payload):
    """True when this payload's reader may cast a vote now."""
    return bool(payload["can_vote"])


def edges_agree(mine, theirs):
    """True when the two edges agree."""
    return len(mine) == len(theirs)


def one_body(digests, canon="unnamed"):
    """True when the digests agree about one body."""
    bodies = set(digests)
    if len(bodies) != 1:
        return False
    return True


RECEIPTS = {
    "e22142089a2defa0": "raw bytes as served, quoted from another reader's run",
}


def printed_under_the_heading(digest, canon_id):
    """True when the function named beside the digest is the one that produced it."""
    return RECEIPTS[digest] == canon_id


DECLARED = {
    "VotingAllowance": {
        "can_vote": {
            "type": "boolean",
            "description": "eligibility; remaining daily allowance is still enforced",
        },
    },
    "ResponseViewer": {
        "can_vote": {"type": "boolean"},
    },
}


def caveat_reachable_from_every_declaration(field):
    """True when the caveat on this field is attached to each declaration of it."""
    return all(bool(spec.get(field, {}).get("description")) for spec in DECLARED.values())


KEY_ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")

def verdict_on_the_key(key, alphabet=KEY_ALPHABET):
    """The gate's two refusal bodies, rebuilt from the measured boundary.

    Measured on `GET /v1/me/publications/lookup` and `GET /v1/me/agent`: the
    second body appears when the string is at least 32 characters, at most 200,
    and every character is in the alphabet -- and the value is not an input at
    all (four 128-character keys over four alphabets gave one body). A character
    outside the alphabet at any length gives the first body, and so does every
    length below 32. So the second body announces a judgement of the key, while
    the only thing the answer reflects is the key's shape: whether a store is
    consulted behind the gate is not observable from outside, and four values
    answering with one body cannot separate "read and rejected" from "never
    read".

    This docstring said "at least 32 characters" and nothing else until an
    independent reviewer sent 201 characters and got the first body: the rule I
    had published was read out of a probe set that stopped at 128, and its upper
    end had never been sent. The cap is 200; a third reading of the same rule
    from a set that stops at 128 would reproduce the same error.
    """
    if 32 <= len(key) <= 200 and all(c in alphabet for c in key):
        return "Invalid or revoked API key."
    return "Send your API key as Authorization: Bearer <key>."


def the_rules_reach(probe_lengths):
    """How far the rule holds: the last length every probe in the set agrees on.

    The name promises a property of the rule and the answer is a property of the
    set: with probes that stop at 128 it says 128, and I published that as the
    rule's reach. The rule's reach is 200, measured by sending 200 and 201; no
    set that stops at 128 can tell 128 from 200, and a set that stops at 199
    could not either. The extent of the sample belongs in the verdict.
    """
    return max(probe_lengths)



def refusals_i_can_see(doors, my_key=None):
    """Which refusals this route gives, swept over the doors in order.

    The name promises a property of the route. The answer is a property of the
    prober: the loop stops at the first door it cannot open, so every body behind
    that door is unreachable -- not because too few points were chosen, but
    because the sweep is being done without the credential that door wants. Four
    lengths across five reasons, all of them swept on the wrong side of the gate,
    and a body a peer reached from the same route stayed invisible to me. The
    axes are route x header x reason x authority, and only three of them can be
    printed from inside a green run: the fourth is a fact about who is asking,
    and no amount of extra probing by the same holder will move it.
    """
    seen = []
    for door in doors:
        if door["needs_key"] and my_key is None:
            break
        seen.append(door["body"])
    return seen


def names_the_function_binds(node):
    """The names the function binds."""
    bound = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            bound.add(sub.id)
    return bound


def a_scoping_pair(helper_local):
    """Two fragments of one piece of logic, differing only in the letter a
    nested function gave its own local. `helper` is free in both: the outer
    function never binds it, and the nested local is a different binding."""
    src = ("def f(xs):\n"
           "    def inner():\n"
           f"        {helper_local} = 1\n"
           f"        return {helper_local}\n"
           "    return helper(xs)\n")
    return ast.parse(src).body[0]


def fingerprint_by_flat_set(node):
    """The logic of a function with the names it binds thrown away, where the
    names it binds are read from every scope below it."""
    body = ast.parse(ast.unparse(node)).body[0]
    bound = names_the_function_binds(body)
    for sub in ast.walk(body):
        if isinstance(sub, ast.Name) and sub.id not in bound and sub.id != body.name:
            if isinstance(sub.ctx, ast.Load):
                sub.id = "free_" + sub.id
    return ast.dump(body)


def flat_set_says_one_piece_of_logic(helper_local):
    left = fingerprint_by_flat_set(a_scoping_pair("helper"))
    right = fingerprint_by_flat_set(a_scoping_pair(helper_local))
    return left == right



GUARDED_POLICY = ("R1", "R2", "R3")
SMALL_POLICY = ("R1", "R2")


def guard_pairs():
    """A control table that reads as `one pair per rule` while one rule of the
    policy has no pair: two of its four entries are two sentences about the same
    rule, and no entry mentions R3."""
    return [
        ("left_a", "right_a", False, "a free name is kept"),
        ("left_b", "right_b", False, "a store a caller reads is kept"),
        ("left_c", "right_c", False, "the guard is a property of the fragment"),
        ("left_d", "right_d", True, "a dead store is removed"),
    ]


def guard_pairs_with_ids():
    """The repaired table: the column is a rule id, not a sentence about one."""
    return [
        ("a", "b", False, "R1"),
        ("c", "d", False, "R2"),
        ("e", "f", False, "R2"),
        ("g", "h", True, "R2"),
    ]


def every_rule_is_guarded(pairs, policy):
    """Whether every rule of the policy carries a control pair of its own.

    As written, the rules are the sentences written beside the pairs, so two
    sentences about one rule count as two rules, and a rule nobody wrote a pair
    for is absent from the universe the check ranges over -- the count can only
    ever fall short of the table's own size, never of the policy's.
    """
    written = [note for _l, _r, _same, note in pairs]
    return (len(pairs) >= 4
            and len(set(written)) == len(written)
            and len({(l, r) for l, r, _s, _n in pairs}) == len(pairs)
            and len(policy) <= len(written))


def every_rule_of_the_policy_is_guarded(pairs, policy):
    """The same question asked of the policy rather than of the table's prose."""
    guarded = {rule for _l, _r, _same, rule in pairs}
    return {rule for rule in policy} <= guarded



def uncovered_rules(policy_rules, control_pairs, without_a_pair):
    """The rules with no pair, as the coverage count computed them.

    `policy_rules` is the policy THE TREE CARRIES, and so is `control_pairs`. A
    rule deleted from that file removes itself from both the question and the
    answer, so this function returns the empty list for a policy that has lost a
    rule and its pair together -- coverage 1:1 by construction.
    """
    guarded = {rule for _l, _r, _same, rule in control_pairs}
    declared = {rule for rule, _row in without_a_pair}
    return sorted({rid for rid, _text in policy_rules} - guarded - declared, key=str)


def a_rule_deleted_from_the_scope_the_coverage_was_counted_over() -> bool:
    """A whole rule removed from the policy leaves the coverage count silent.

    One rule is dropped from a COPY of the policy together with its control pair:
    the count's scope and its answer come from the same file, so what is asking
    and what is asked shrink together. True means the derivation cannot notice a
    rule going missing -- the verifier is not independent of the verified.
    """
    import check as _c

    policy = list(_c.POLICY_RULES) if hasattr(_c, "POLICY_RULES") else []
    if not policy:  # the policy lives in fragments; take it from the module
        policy = [r for r in POLICY_RULES]
    gone = "R9"
    if gone not in {rid for rid, _t in policy}:
        return False  # the rule this measurement removes is not there to remove
    pairs_after = [(l, r, same, rule) for l, r, same, rule in CONTROL_PAIRS if rule != gone]
    policy_after = [(rid, t) for rid, t in policy if rid != gone]
    declared_after = [(rid, row) for rid, row in RULES_WITHOUT_A_PAIR if rid != gone]
    silent_after = uncovered_rules(policy_after, pairs_after, declared_after) == []
    # and the oracle that does NOT draw its scope from the file refuses it
    oracle = set(_c.POLICY_RULE_IDS)
    oracle_refuses = sorted(oracle - {rid for rid, _t in policy_after}, key=str) == [gone]
    return silent_after and oracle_refuses


def the_frame_is_not_erased_but_the_letters_are() -> bool:
    """A promise of invariance that the instrument it describes does not hold.

    The erasure's own account said that what changes between a fragment and the
    same fragment written another way is *only* whether there is a docstring to
    drop. Measured on the two spellings of one logic, more than the docstring
    changed: the dump carried the node kind, and a `def` spent one erased letter
    on its own name while a lambda spent none, which shifted every letter after
    it. So `lambda x: x + y` and `def f(x): return x + y` -- one logic, the second
    the first written out -- never shared a fingerprint, while the account
    promised that they did.

    True means the promise does not hold on the pass as it stood. That pass is
    rebuilt here by the `frame` parameter rather than by reverting the repair, so
    the difference stays measurable in a tree that no longer takes it.

    The price of the lie is not cosmetic. The ledger's own rule is that a repeat
    which fingerprints identically to the class fragment is the class probe again
    and not a second sighting; with the frame kept, a sighting re-filed under the
    other spelling of itself read as a second sighting, so a repeat the ledger
    forbids was reachable by a rewrite that changes nothing.
    """
    import check as _c

    by_def = _c.fingerprint(a_fragment_by_def, frame=False)
    by_lambda = _c.fingerprint(a_fragment_by_a_lambda, frame=False)
    return by_def != by_lambda


def the_report_cannot_come_from_the_run_that_was_made() -> bool:
    """A refusal reported from a run in which nothing refused.

    The oracle compares the committed scope against the policy the tree carries.
    Asked on the tree as it stands, it agrees -- that is the run that was actually
    made. The refusal that got published belongs to a different state of the world:
    a scope that names a rule the policy does not carry. True means the two are
    different states, so the green run carries no information at all about the
    state the report described -- and the report was a procedure, described and
    never run, which is worth exactly the credibility of whoever wrote it and
    nothing more.

    The scope is supplied as a parameter for this probe alone. It is not a way for
    the standing run to pick its own answer: that calls the same comparison with
    the committed constant and nothing else.
    """
    import check as _c

    run_that_was_made = _c.policy_still_names_every_rule_it_named()
    state_the_report_describes = _c.policy_still_names_every_rule_it_named(
        committed=("R1", "R17"))
    return run_that_was_made[0] and not state_the_report_describes[0]

def the_request_line_is_not_an_argument_of_the_record() -> bool:
    """The field named for the request holds the answer, and nothing reads it.

    A cell of the ladder is a claim about the wall only if the target in the row
    is the target that was asked. Two runs differ in exactly that: one puts
    `GET /v1#x HTTP/1.1` on the wire, the other a client that dropped the
    fragment puts `GET /v1 HTTP/1.1` there, and the second is a reading of a
    different path wearing the row's name. The record was meant to make the two
    distinguishable -- the sentence beside the field said the reader could
    compare the row's path against what was sent and see the divergence.

    Measured, the field does not depend on what was sent at all: it is filled
    from the answer's header block, so both runs carry the same value and the
    comparison the sentence promised compares the row with the answer. True
    means a rewritten request and an honest one are indistinguishable in the
    record, and the guard is the sentence rather than the field.

    The price is not cosmetic. `--path-as-is` and `--request-target` are the
    flags that keep the client honest, and a record unable to show what the
    client chose makes every cell taken with them a promise about the client
    rather than a reading -- including the cells whose whole point is that the
    fragment was sent.

    The recorder below is the ladder's own, kept as it shipped. `asked` is what
    the client actually put on the wire -- the only quantity the row's reading
    rests on -- carried so the probe can compare it with the field the reader
    was given.
    """
    def a_row_recorded_from_the_answer_line(path, head, asked):
        sent = (head.split(b"\r\n", 1)[0].decode("latin-1")
                if head.startswith(b"HTTP/") else path)
        return {"path": path, "sent": sent, "asked": asked}

    row = "/v1#x"
    answer = b"HTTP/2 400 \r\ncontent-type: application/json\r\n"
    kept = a_row_recorded_from_the_answer_line(row, answer, "GET /v1#x HTTP/1.1")
    dropped = a_row_recorded_from_the_answer_line(row, answer, "GET /v1 HTTP/1.1")
    return kept["sent"] == dropped["sent"] and kept["sent"] != kept["asked"]


def a_probe_that_cannot_separate_the_two_readings_a_row_claims_to_part() -> bool:
    """A row that looks like a discriminator and is one spelling of one claim.

    The wall decides membership by ONE BIT: the raw bytes of the first segment
    equal `v1`. Two targets that look like the same claim written two ways --
    `/v1#x/me` and its percent-encoded twin `/v1%23x/me` -- land on opposite
    sides of that bit, and only one model can explain both. Measured keyless:
    `/v1#x/me` 400/266 inside, the encoded twin 404/0 outside, and
    `/v1/me%23x` 400/266 inside, so `%23` never ends a segment while the literal
    `#` does.

    True means the pair DOES part the two models, on both of which the reading
    was computed:

      percent-decoded before segmentation: `/v1%23x` -> `/v1#x` -> segment `v1`
        -> INSIDE   (refuted: measured outside)
      raw bytes:                            `/v1%23x` -> segment `v1%23x`
        -> OUTSIDE  (holds)

    The contrast with the retracted pair is the point: there the two models gave
    the SAME segment and the row parted nothing, here they give different ones.
    A pair is a discriminator when the readings differ on it, and that is a
    computation on the pair, not a sentence about it.
    """
    def segment_by_raw_bytes(target):
        body = target[1:] if target.startswith("/") else target
        for i, ch in enumerate(body):
            if ch in "/?#":
                return body[:i]
        return body

    def segment_after_percent_decoding(target):
        import urllib.parse
        decoded = urllib.parse.unquote(target)
        body = decoded[1:] if decoded.startswith("/") else decoded
        for i, ch in enumerate(body):
            if ch in "/?#":
                return body[:i]
        return body

    pair = ("/v1#x/me", "/v1%23x/me")
    plain, encoded = pair
    # Both models on the plain row: `#` ends the segment (raw) or the fragment
    # is cut (decoded) -- `v1` either way, and both agree the row is inside.
    plain_agrees = (segment_by_raw_bytes(plain) == segment_after_percent_decoding(plain)
                    == "v1")
    # The encoded row is where they part: raw says `v1%23x` and outside, decoded
    # says `v1` and inside, and the measurement says outside.
    raw_says = segment_by_raw_bytes(encoded)
    decoded_says = segment_after_percent_decoding(encoded)
    measured_inside = False  # 404/0 against 400/266 for the plain twin
    return (plain_agrees
            and raw_says != decoded_says
            and raw_says == "v1%23x"
            and decoded_says == "v1"
            and (raw_says == "v1") == measured_inside)


def two_readings_that_agree_on_the_row_that_was_said_to_part_them() -> bool:
    """A row published as parting two readings, with only one of them computed on it.

    The two readings: `#` ends the first segment where it stands, or the fragment
    is cut off the target before the segment is taken. The row published as
    parting them was `/v1#x/me`, on the reasoning that a cut turns it into
    `/v1x/me` -- a segment `v1x`, outside, against `v1` inside for the reading the
    row was meant to refute.

    That reasoning reads a cut as the removal of one character. A cut is a
    truncation: `"/v1#x/me".split("#", 1)[0]` is `/v1`, and the bytes after the
    `#` are gone, not moved left. Under the second reading the row's segment is
    `v1` -- the same as under the first -- so the row parts nothing, refutes
    nothing, and the two readings predict the measured answer together.

    True means the two readings agree on the row that was said to separate them:
    the discriminator was adopted without both models being evaluated on it, and
    the measured answer it was quoted against is equally the answer of the rival.
    """
    def segment_ends_where_the_hash_stands(target):
        body = target[1:] if target.startswith("/") else target
        for i, ch in enumerate(body):
            if ch in "/?#":
                return body[:i]
        return body

    def segment_after_the_fragment_is_cut(target):
        t = target.split("#", 1)[0]
        body = t[1:] if t.startswith("/") else t
        for i, ch in enumerate(body):
            if ch in "/?":
                return body[:i]
        return body

    def the_cut_read_as_a_splice(target):
        return target.replace("#", "", 1)

    published = "/v1#x/me"
    measured_inside = True  # 400/266 with the protocol body, against 404/0 outside
    return (segment_ends_where_the_hash_stands(published)
            == segment_after_the_fragment_is_cut(published)
            and the_cut_read_as_a_splice(published) != published
            and measured_inside)


def a_byte_count_published_without_the_encoding_it_was_taken_under() -> bool:
    """The record's byte column counts a point on the decoding chain, and the record does not say which.

    The ladder records one number per row under the name `size`, taken from
    `curl -w '%{size_download}'`. Measured on a loopback listener, that number is
    not a count of the object, and not a count of the wire either: it is the entity AFTER transfer decoding and BEFORE content decoding: a 1024-byte body served
    gzipped is reported as 29, and `--compressed` reports the same 29, so the flag
    decodes what is written rather than what is counted. Two rows whose answers
    were encoded differently therefore put two different quantities in one column
    under one name, and a reader comparing them compares nothing.

    The record did not carry a `content-encoding`. The head block was already in
    hand -- the rows are taken with `-D -` -- and the encoding was in it, read by
    nobody. What kept the column honest was the flag set: `curl` sends no
    `Accept-Encoding` unless `--compressed` is passed, so every cell happened to
    be plain. That is a promise about the client, standing where a reading of the
    answer belongs, and it holds only while the server does not take an offer it
    was never made -- and it breaks silently the first time a row's own headers
    ask for an encoding.

    True means the record as it shipped reads two quantities as one: the rows do
    not name an encoding, so nothing in them separates a plain count from an
    encoded one, while the same rows with the encoding beside them do not compare
    at all.
    """
    def a_row_as_the_record_shipped(cell, size):
        # The ladder's row: a cell, a path, an answerer, a byte count -- and no
        # `content-encoding`, though the head that carried one was in hand.
        return {"cell": cell, "size": size}

    def a_row_with_the_encoding_beside_it(cell, size, content_encoding):
        # The same row after the repair: the condition the number was taken under
        # is published with the number.
        return {"cell": cell, "size": size, "content_encoding": content_encoding}

    def what_the_number_counts(row):
        # `%{size_download}`: the entity after transfer decoding, before content decoding.
        return row["size"]

    def two_rows_are_comparable(left, right):
        # Comparable only when the same encoding lies behind both numbers. A row
        # that names no encoding cannot answer the question, and a record that
        # admits such rows is claiming they can.
        return ("content_encoding" not in left
                or "content_encoding" not in right
                or left["content_encoding"] == right["content_encoding"])

    plain = a_row_as_the_record_shipped("plain", 1024)
    encoded = a_row_as_the_record_shipped("gzip", 29)
    return (two_rows_are_comparable(plain, encoded)
            and what_the_number_counts(plain) != what_the_number_counts(encoded)
            and not two_rows_are_comparable(
                a_row_with_the_encoding_beside_it("plain", 1024, ""),
                a_row_with_the_encoding_beside_it("gzip", 29, "gzip")))


def check_passes_when_there_is_nothing_to_check(present, named):
    """The mirror item as the runner ran it: the file it checks is not there, so
    it prints a sentence and exits zero."""
    if not present:
        return True
    return present <= named


def covered_by_the_checksums(present, named):
    """Whether every file the reader is told to trust is in the checksum file."""
    return present <= named






def a_fragment_by_def(x, y):
    """One piece of logic, written as a named function."""
    return x * y + 1


a_fragment_by_a_lambda = lambda a, b: a * b + 1

def store_read_by_eval():
    """One of a pair that must never share a fingerprint: the store is read, and
    the caller that reads it carries no name in the tree."""
    x = 41
    return eval("x + 1")


def store_read_by_no_one():
    """The other half: the same body without the store."""
    return eval("x + 1")


def a_callee_that_asks_its_caller_for_the_frame():
    """A reader that lives in the CALLEE, one frame down.

    `sys._getframe(1).f_locals` is the calling frame's own mapping, so a function
    called from a fragment with a store reads that store -- and no name or path
    inside the fragment says so. The pass reads one fragment's source, so the
    store is kept rather than guessed at.
    """
    import sys as _sys

    return "secret" in _sys._getframe(1).f_locals


def store_read_by_a_callee():
    """A store its callee reads through the caller's frame. Answers True."""
    secret = 1
    return a_callee_that_asks_its_caller_for_the_frame()


def no_store_read_by_a_callee():
    """The same call with no store to reach. Answers False."""
    return a_callee_that_asks_its_caller_for_the_frame()


def store_read_by_a_qualified_reader():
    """A store a caller reads through a QUALIFIED reader.

    `builtins.eval("secret")` reaches the frame's own mapping while containing no
    Name of the reader set: the reader is an attribute of an expression. Answers
    `41` here; the other half of the pair, without the store, raises NameError,
    and the two were merged into one fingerprint by a guard that matched the set
    against a Name's `id` only. `builtins.vars()` is the sharper form of the same
    reach, because it IS a path to the scope's own mapping.
    """
    secret = 41
    return builtins.eval("secret")


def no_store_read_by_a_qualified_reader():
    """The other half: the same qualified reader, no store to reach."""
    return builtins.eval("secret")


def store_read_through_a_frame():
    """One of a pair that must never share a fingerprint, and one no list of
    reader NAMES can tell apart from its other half: the store is read through
    `sys._getframe().f_locals`, a path to the scope's own mapping, so no
    identifier the guard could name appears in the fragment. On CPython the
    expression answers `True` here and `False` in the other half."""
    secret = 1
    return "secret" in sys._getframe().f_locals


def no_store_read_through_a_frame():
    """The other half: the same reader path, no store to reach."""
    return "secret" in sys._getframe().f_locals


def read_by_eval_and_one_dead_store():
    """One of a pair that must differ: the fragment keeps a store a caller reads
    through `eval`, so it must keep the dead one in front of it too -- the guard
    is a property of the fragment, not of one store."""
    _pad = None
    x = 41
    return eval("x + 1")


def read_by_eval_only():
    """The other half: the same fragment without the dead store."""
    x = 41
    return eval("x + 1")


def added_over_a_shadowing_name(list, x):
    """One of a pair that must share a fingerprint: the parameter's letter spells
    a builtin, and a bound name is the author's letter whatever it spells."""
    return list + x


def added_over_another_shadowing_name(dict, x):
    """The other half, spelled with another builtin's name."""
    return dict + x


def plain_max_of(xs):
    """One of a pair that must share a fingerprint: this store is read by
    nothing at all."""
    return max(xs)


def padded_max_of(xs):
    """The other half: the same logic with a dead store in front of it."""
    _pad = None
    return max(xs)


# ---- fragments added for the pairs an attack on the control table found -----
# A second holder attacked the published claim ("one pair per rule") on copies
# of the tree and broke six rules of the policy without the control noticing:
# two dynamic readers were unguarded, the import rule and the dunder rule had no
# pair at all, the dead-store pass was never asked what counts as a read, and a
# class body was never asked whether it binds outside itself. Each of those rules
# now has a pair, and `POLICY_MUTATIONS` below is the table that measures the
# instrument rather than describing it.

def padded_beside_a_mention_of_eval():
    """Padding survives beside a mere MENTION of a reader.

    `eval` is named and never called, so nothing is read through it; the store is
    kept all the same, because the guard asks whether the fragment mentions a
    reader. The price of that caution, made visible: the pair with the same body
    and no padding reads as a DIFFERENT piece of logic.
    """
    _pad = None
    return eval


def bare_beside_a_mention_of_eval():
    """The same body without the dead store."""
    return eval


def a_local_store_globals_cannot_reach():
    """One of a pair that must share a fingerprint: `globals()` inside a function
    returns the MODULE's dict, so the store in front of it is not reachable
    through the reader the pair names. The pass drops it, and the two members --
    which differ in a name the pass erases and in a constant it deletes with the
    store -- become one fingerprint. The guard's name set used to include
    `globals()`, and this pair was the reason given for it."""
    secret = 1
    return globals()


def a_local_store_globals_cannot_reach_other_name():
    """The other half, spelled with another name and another constant."""
    other = 2
    return globals()


def read_by_vars():
    """A store read through vars()."""
    secret = 1
    return vars()


def read_by_vars_renamed():
    """The same, with the store under another letter."""
    other = 2
    return vars()


def read_by_dir():
    """A store read by a caller that carries no name: `dir()` with no argument
    lists the local names, so the reader is in the fragment and nothing in the
    tree refers to the store. The pair differs in the store alone."""
    pad = 1
    return dir()


def read_by_dir_no_store():
    """The other half: the same fragment without the store."""
    return dir()


def import_as_j(text):
    """`import json as j`: the `as` name is the author's letter."""
    import json as j
    return j.loads(text)


def import_as_k(text):
    """`import json as k`: one piece of logic with the fragment above."""
    import json as k
    return k.loads(text)


def dunder_letters(v):
    """A dunder name is left as written -- it names something outside."""
    __x = v
    return __x


def plain_letters(v):
    """A bound name that is not a dunder: erased."""
    y = v
    return y


def read_in_a_nested_scope():
    """The store is read, by a name inside a nested def: not dead."""
    x = 1

    def g():
        return x
    return g


def no_store_for_the_nested_read():
    """The same fragment with nothing for the nested read to see."""
    def g():
        return x
    return g


def class_body_binds_nothing(xs):
    """A class body binds `helper` inside the class, not in the function: the
    call to `helper` here reads something outside both."""
    class C:
        helper = 1
    return helper(xs)


def class_body_other_name(xs):
    """The same, with the class attribute under another letter. A class body
    that leaked its bindings into the enclosing scope would erase the free name
    below and make these two fragments one piece of logic."""
    class C:
        step = 1
    return step(xs)


def global_counter():
    """`global counter` states the name is not this function's own."""
    global counter
    counter = 1
    return counter


def global_total():
    """The same declaration under another letter."""
    global total
    total = 1
    return total



def free_name_beside_a_nested_arg(xs):
    """`helper` is free here: a nested def that uses it as an argument binds it
    inside that def only, so this fragment still refers to something outside."""
    def inner(helper):
        return helper(xs)
    return helper(xs)


def free_name_beside_a_nested_arg_renamed(xs):
    """The same logic with the free name under another letter. A nested local
    that leaked into the enclosing scope would erase both and make these one
    piece of logic."""
    def inner(step):
        return step(xs)
    return step(xs)


# The policy, enumerated. A rule of the instrument that is not in this list is
# not a rule anybody has counted, and the control below refuses a pair or a gap
# that names a rule outside it. R13 and R14 are here because they are rules the
# policy applies, not because they have pairs: a rule that appears in neither
# table is exactly the silent case a reader must not have to guess about.
POLICY_RULES = (
    ("R1", "a free name is kept: two modules called by name are not one module"),
    ("R2", "a bound letter is erased: a function renamed and its argument renamed "
           "are one piece of logic"),
    ("R3", "a store a caller reaches through a dynamic reader is kept -- by a name in the reader set or by a path to a scope mapping, since a read is not always a name"),
    ("R4", "a store nobody reads is removed -- except that a fragment which merely MENTIONS a dynamic reader has nothing removed, and padding beside such a mention survives as a difference"),
    ("R5", "the dynamic-reader guard is a property of the fragment, not of one store"),
    ("R6", "a bound name is erased even when its letter spells a builtin"),
    ("R7", "every dynamic reader is guarded, not only the one a pair calls"),
    ("R8", "an explicit `as` name is a bound name; a bare import keeps the module's "
           "own name free"),
    ("R9", "a dunder name is left as written"),
    ("R10", "a read inside a nested scope is a read of the enclosing store"),
    ("R11", "a class body binds nothing in the enclosing scope"),
    ("R12", "a `global` or `nonlocal` declaration makes the name external"),
    ("R13", "the erasure is idempotent: applying it to its own output changes nothing"),
    ("R14", "a nested local binds nothing in the enclosing scope"),
    ("R15", "a fragment that calls a name it does not bind keeps its stores: the callee is "
            "outside the fragment and may read them through the caller's frame"),
    ("R16", "a fragment written under the other spelling of itself is the same fragment: "
            "a `def` and a bare lambda of one logic share a fingerprint, so a repeat "
            "cannot be laundered by a rewrite that changes nothing"),
)

# The control table: (left, right, must they share one fingerprint?, rule id).
# A verdict of `duplicate` is a measurement only while every rule of the policy
# answers for itself: a pair that fails when its rule is broken, or a declared
# gap whose covering row is *run* by `probes/policy_mutations.py`. The rule id
# is what the counts are over; a pair labelled with a rule the policy does not
# name is not a guard, it is a sentence.
CONTROL_PAIRS = (
    ("parsed_by_json", "parsed_by_pickle", False, "R1"),
    ("max_of", "biggest_of", True, "R2"),
    ("a_fragment_by_def", "a_fragment_by_a_lambda", True, "R16"),
    ("store_read_by_eval", "store_read_by_no_one", False, "R3"),
    ("store_read_through_a_frame", "no_store_read_through_a_frame", False, "R3"),
    ("padded_beside_a_mention_of_eval", "bare_beside_a_mention_of_eval",
     False, "R4"),
    ("plain_max_of", "padded_max_of", True, "R4"),
    ("read_by_eval_and_one_dead_store", "read_by_eval_only", False, "R5"),
    ("added_over_a_shadowing_name", "added_over_another_shadowing_name", True, "R6"),
    ("store_read_by_a_qualified_reader", "no_store_read_by_a_qualified_reader",
     False, "R3"),
    ("store_read_by_a_callee", "no_store_read_by_a_callee", False, "R15"),
    ("a_local_store_globals_cannot_reach",
     "a_local_store_globals_cannot_reach_other_name", True, "R3"),
    ("read_by_vars", "read_by_vars_renamed", False, "R7"),
    ("read_by_dir", "read_by_dir_no_store", False, "R7"),
    ("import_as_j", "import_as_k", True, "R8"),
    ("dunder_letters", "plain_letters", False, "R9"),
    ("read_in_a_nested_scope", "no_store_for_the_nested_read", False, "R10"),
    ("class_body_binds_nothing", "class_body_other_name", False, "R11"),
    ("global_counter", "global_total", False, "R12"),
    ("free_name_beside_a_nested_arg", "free_name_beside_a_nested_arg_renamed",
     False, "R14"),
)

# The gap, declared, with the row that is expected to notice the break. The row
# is run by `probes/policy_mutations.py`, on a copy with the rule broken: a
# pointer nobody follows is not coverage.
RULES_WITHOUT_A_PAIR = (
    ("R13", "r_idempotence"),
)
# The mutations. Each entry is (rule id, text in check.py, what it becomes). The
# mutation is the rule's own parameter, changed to the wrong value: dropping a
# member from the reader set, turning the alias branch off, letting a class body
# write into the enclosing scope. `probes/policy_mutations.py` applies each to a
# copy in memory, fingerprints every fragment named in the control table, and
# requires that at least one fingerprint MOVED -- a mutation that changes nothing
# cannot be counted as a guard of anything. A mutation of a guarded rule must
# make the control fail and name that rule's pair; a mutation of a declared rule
# must leave the control passing (that is the blind spot, measured) and make the
# row the declaration points at fail on a copy.
POLICY_MUTATIONS = (
    ("R1", "        if isinstance(node.ctx, ast.Load) and not self._bound(node.id):",
     "        if False:"),
    ("R2", "        if name not in self.seen:\n"
           "            self.seen[name] = f\"{BOUND_PREFIX}{len(self.seen)}\"\n"
           "        return self.seen[name]",
     "        return name"),
    ("R3", '    DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir"}',
     '    DYNAMIC_READERS = {"locals", "vars", "dir"}'),
    ("R3", '    DYNAMIC_READER_PATHS = {"f_locals", "f_globals", "f_builtins"}',
     '    DYNAMIC_READER_PATHS = set()'),
    ("R4", "            if targets and all(t.id not in reads for t in targets):\n"
           "                continue",
     "            if False:\n                continue"),
    ("R5", "        if (self._reads_by_a_caller(node)\n"
           "                or self._calls_a_name_the_fragment_does_not_bind(node)):\n"
           "            self.generic_visit(node)\n"
           "            return node",
     "        if all(self._reads_by_a_caller(s)\n"
     "               or self._calls_a_name_the_fragment_does_not_bind(s) for s in node.body):\n"
     "            self.generic_visit(node)\n"
     "            return node"),
    ("R6", "        if name in BUILTINS and not self._bound(name):",
     "        if name in BUILTINS:"),
    ("R3", '    DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir"}',
     '    DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir", "globals"}'),
    ("R3", "            if (isinstance(n, ast.Attribute)\n"
           "                    and n.attr in self.DYNAMIC_READERS | self.DYNAMIC_READER_PATHS):",
     "            if (isinstance(n, ast.Attribute)\n"
     "                    and n.attr in self.DYNAMIC_READER_PATHS):"),
    ("R4", "            if (isinstance(n, ast.Name) and n.id in self.DYNAMIC_READERS\n"
           "                    and isinstance(n.ctx, ast.Load)):",
     "            if (isinstance(n, ast.Name) and n.id in self.DYNAMIC_READERS\n"
     "                    and isinstance(n.ctx, ast.Load) and isinstance(n, ast.Call)):"),
    ("R7", '"locals", "vars", "dir"', '"locals", "vars"'),
    ("R7", '"locals", "vars", "dir"', '"locals", "dir"'),
    ("R8", "elif isinstance(child, ast.alias) and child.asname:",
     "elif False:"),
    ("R9", '        if name.startswith("__"):\n            return name\n', "        pass\n"),
    ("R10",
     "    def _reads(self, node) -> set:\n"
     "        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)\n"
     "                and isinstance(n.ctx, ast.Load)}",
     "    def _reads(self, node) -> set:\n"
     "        inside = {id(n) for d in ast.walk(node)\n"
     "                  if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef,"
     " ast.Lambda))\n"
     "                  for n in ast.walk(d)}\n"
     "        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)\n"
     "                and isinstance(n.ctx, ast.Load) and id(n) not in inside}"),
    ("R11", "            new = {child.name}\n            scopes[id(child)] = new",
     "            new = cur\n            scopes[id(child)] = new"),
    ("R12",
     "            elif isinstance(child, (ast.Global, ast.Nonlocal)):\n"
     "                external.update(child.names)",
     "            elif isinstance(child, (ast.Global, ast.Nonlocal)):\n"
     "                pass"),
    ("R13", "            if not node.id.startswith(FREE_PREFIX):",
     "            if True:"),
    ("R15", "        if (self._reads_by_a_caller(node)\n"
            "                or self._calls_a_name_the_fragment_does_not_bind(node)):",
     "        if (self._reads_by_a_caller(node)):"),
    ("R14",
     "            new = {a.arg for a in (*child.args.posonlyargs, *child.args.args,\n"
     "                                   *child.args.kwonlyargs)}",
     "            new = {a.arg for a in (*child.args.posonlyargs, *child.args.args,\n"
     "                                   *child.args.kwonlyargs)}\n            cur |= new"),
    ("R16", "            node = _a_bare_lambda_as_a_named_function(node)",
     "            pass"),
)


KNOWN_DIFFERENT_PAIR = ("parsed_by_json", "parsed_by_pickle")
KNOWN_SAME_PAIR = ("max_of", "biggest_of")


def parsed_by_json(text):
    """One of the two fragments the fingerprint must never call the same: the
    only difference from `parsed_by_pickle` is the free name it delegates to."""
    return json.loads(text)


def parsed_by_pickle(payload):
    """The other half of the known-different pair."""
    return pickle.loads(payload)


def max_of(xs):
    """One piece of logic, spelled with one function name and one argument."""
    return max(xs)


def biggest_of(values):
    """The same piece of logic under another name: the control must join these
    two, or a `duplicate` verdict from the same instrument means nothing."""
    return max(values)


BUILTIN_SPELLINGS = frozenset({
    "list", "dict", "set", "str", "bytes", "int", "float", "bool", "len",
    "max", "min", "sum", "id", "type", "input", "filter", "map", "hash",
    "next", "zip", "open", "vars", "dir", "eval", "exec", "locals", "globals",
})


def stores_no_name_reads(src):
    """The logic of a fragment with the stores no name in the tree reads removed.

    This is the reading the erasure used before the guard: a read is a name under
    `ast.Load`, so a store whose name never appears that way is dropped, whatever
    else in the file reads it.
    """
    tree = ast.parse(src)
    fn = tree.body[0]
    reads = {n.id for n in ast.walk(fn)
             if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    keep = []
    for stmt in fn.body:
        targets = []
        if isinstance(stmt, ast.Assign):
            targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
        if targets and all(t.id not in reads for t in targets):
            continue
        keep.append(stmt)
    fn.body = keep or [ast.Pass()]
    return ast.dump(tree)


def a_store_only_a_caller_reads(keep_store):
    """Two fragments of one file: one keeps a store that only `eval` reads."""
    body = "    x = 41\n" if keep_store else ""
    return "def f():\n" + body + '    return eval("x + 1")\n'


def two_logics_read_as_one_by_the_dead_store_pass():
    left = stores_no_name_reads(a_store_only_a_caller_reads(True))
    right = stores_no_name_reads(a_store_only_a_caller_reads(False))
    return left == right


def letters_with_the_builtins_asked_first(src):
    """The logic of a fragment with the names it binds erased, except where the
    letter happens to spell a builtin: that check used to come first."""
    tree = ast.parse(src)
    fn = tree.body[0]
    bound = {a.arg for a in list(fn.args.args) + list(fn.args.posonlyargs)
             + list(fn.args.kwonlyargs)}
    if fn.args.vararg:
        bound.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        bound.add(fn.args.kwarg.arg)
    seen = {}
    for sub in ast.walk(fn):
        target = None
        if isinstance(sub, ast.Name) and sub.id in bound:
            target = "id"
        elif isinstance(sub, ast.arg) and sub.arg in bound:
            target = "arg"
        if target is None:
            continue
        name = getattr(sub, target)
        if name in BUILTIN_SPELLINGS:
            continue
        if name not in seen:
            seen[name] = f"v{len(seen)}"
        setattr(sub, target, seen[name])
    return ast.dump(tree)


def a_bound_name_spelled_like_a_builtin(letter):
    """One piece of logic in two spellings: the parameter's letter is the only
    difference, and one of the letters is a builtin's name."""
    return f"def f({letter}, x):\n    return {letter} + x\n"


def builtin_named_letters_read_as_one():
    left = letters_with_the_builtins_asked_first(
        a_bound_name_spelled_like_a_builtin("list"))
    right = letters_with_the_builtins_asked_first(
        a_bound_name_spelled_like_a_builtin("dict"))
    return left == right


HASHES_BY_HEADING = {
    "policy": "c01ed633e3855776",
}


def digest_served_under(heading):
    """The digest the record serves under this heading."""
    return HASHES_BY_HEADING[heading]


def serves_its_own_digest(item, heading):
    """Whether the value printed under the heading is the one the object yields.

    A hash is a name for one object. Quoting a *different* object's hash under
    the heading, because both were computed in the same sentence, leaves the
    reader no way to notice: the number is real, correct for its own object, and
    answers a question nobody asked.
    """
    return digest_served_under(heading) == item["compute"]()




# --- the pair that answered the same under both policies --------------------
# Kept as it stood in the table when a second holder attacked it by hand: the
# members differ in a bound name (which the pass erases, so it cannot separate
# them) and in a literal (which the pass never reads), and the reader is called
# with the store's own name, so the store is never dead and the dead-store pass
# has nothing to drop whatever the reader set says. Breaking the rule -- taking
# `dir` out of the dynamic readers -- therefore leaves the verdict where it was.

def _a_label_read_by_dir():
    secret = 1
    return dir(secret)


def _a_label_read_by_dir_other_name():
    other = 2
    return dir(other)


def the_pair_answers_the_same_under_both_policies() -> bool:
    """True when the pair's verdict is the same under the rule and under its
    break: the pair cannot tell the two policies apart, so it is a label stood
    where a control is claimed.

    The rule is broken the way a wrong implementation would break it -- `dir` is
    no longer a dynamic reader -- and the pair is fingerprinted under both. A
    control answers `different` under one and `same` under the other; a pair
    whose verdict never moves is counting a difference the rule never touches.
    """
    import check as _c
    pair = (_a_label_read_by_dir, _a_label_read_by_dir_other_name)
    base = _c.fingerprint(pair[0]) != _c.fingerprint(pair[1])
    readers = _c._DropDeadStores.DYNAMIC_READERS
    try:
        _c._DropDeadStores.DYNAMIC_READERS = readers - {"dir"}
        broken = _c.fingerprint(pair[0]) != _c.fingerprint(pair[1])
    finally:
        _c._DropDeadStores.DYNAMIC_READERS = readers
    return bool(base and broken)



# --- the guard that named a reader which cannot read the store --------------
# The name set was the reason given for keeping a function's dead stores, and one
# of its names cannot reach a function-local store at all.

def a_store_the_guard_keeps_for_a_reader_that_cannot_read_it():
    """The store the guard keeps, asked the question the guard's own reason
    answers: `globals()` inside a function returns the MODULE's dict, so
    `"secret" in globals()` is False and nothing can read this store through it.
    True would mean the reader the guard names can read the store."""
    secret = 1
    return "secret" in globals()




def fingerprint_under_a_simpler_reader_guard(fn, *, paths=True, attributes=True) -> str:
    """The fingerprint of a fragment under an earlier, weaker reader guard.

    `paths=False` removes the pattern set: the guard knows reader names only, and
    a store reached through `sys._getframe().f_locals` is invisible to it.
    `attributes=False` removes the attribute position: the set is matched against
    a bare `Name` only, so `builtins.eval("x")` reads nothing as far as the guard
    is concerned. Both are the pass as it stood, rebuilt here by swapping the
    reader test out on the class rather than by reverting the repair, so the lie
    stays reproducible in a tree that no longer commits it.
    """
    import ast as _ast
    import check as _c

    cls = _c._DropDeadStores
    saved_paths = cls.DYNAMIC_READER_PATHS
    saved_test = cls._reads_by_a_caller

    def name_only(self, node):
        for n in _ast.walk(node):
            if (isinstance(n, _ast.Name) and n.id in self.DYNAMIC_READERS
                    and isinstance(n.ctx, _ast.Load)):
                return True
        return False

    try:
        if not paths:
            cls.DYNAMIC_READER_PATHS = set()
        if not attributes:
            cls._reads_by_a_caller = name_only
        return _c.fingerprint(fn)
    finally:
        cls.DYNAMIC_READER_PATHS = saved_paths
        cls._reads_by_a_caller = saved_test


def fingerprint_under_a_name_only_reader_guard(fn) -> str:
    """The pass as it stood when a reader could only be a bare name.

    `_reads_by_a_caller` asked whether any identifier in the reader set appears in
    the tree; a store reached through `sys._getframe().f_locals` -- a path, not a
    name -- was invisible to that question, so the store was dropped.
    """
    return fingerprint_under_a_simpler_reader_guard(fn, paths=False)

def a_store_read_through_a_path_is_erased() -> bool:
    """Two fragments whose ANSWERS differ are erased into one fingerprint.

    The store is read through `sys._getframe().f_locals`, a path into the scope's
    own mapping, and no identifier of the reader set appears anywhere in either
    fragment -- so a guard that asks about names cannot see the read, drops the
    store, and the fragment that answers `True` and the one that answers `False`
    come out as one piece of logic. True means the lie is present. The pair was
    proposed by a second holder who measured both halves by hand on 3.12.10 before
    it existed here; the sentence under test is "every dynamic reader is guarded".
    """
    import sys as _sys

    def store_read_through_a_frame():
        secret = 1
        return "secret" in _sys._getframe().f_locals

    def no_store_read_through_a_frame():
        return "secret" in _sys._getframe().f_locals

    if store_read_through_a_frame() == no_store_read_through_a_frame():
        return False  # the halves agree here, so the pair proves nothing
    return (fingerprint_under_a_name_only_reader_guard(store_read_through_a_frame)
            == fingerprint_under_a_name_only_reader_guard(no_store_read_through_a_frame))

def a_store_read_by_a_qualified_reader_is_erased() -> bool:
    """The store is erased although a qualified reader reaches it.

    `builtins.eval("secret")` is the same reach as `eval("secret")` and carries no
    Name of the reader set: the reader is an attribute of an expression, so a
    guard matching the set against a `Name.id` saw nothing and dropped the store.
    The two halves answer `41` and NameError and were merged into one fingerprint.
    `builtins.vars()` is the sharper form of the same reach, since it IS a path to
    the scope's own mapping. True means the lie is present under the earlier guard.
    """
    def store_read_by_a_qualified_reader():
        secret = 41
        return builtins.eval("secret")

    def no_store_read_by_a_qualified_reader():
        return builtins.eval("secret")

    def answer(fn):
        try:
            return repr(fn())
        except Exception as exc:  # the half without the store raises here
            return type(exc).__name__

    if answer(store_read_by_a_qualified_reader) == answer(no_store_read_by_a_qualified_reader):
        return False  # the halves agree, so the pair proves nothing
    old = fingerprint_under_a_simpler_reader_guard
    return (old(store_read_by_a_qualified_reader, attributes=False)
            == old(no_store_read_by_a_qualified_reader, attributes=False))





# The row a reader could not reproduce. It is text because the lie is text: a
# verdict whose flip depends on a dial (how the pass PRINTS a bound name) that the
# row never named. A pass printing names as written answers `different` under the
# correct policy and under the break, so on that dial the pair is not a control at
# all -- and nothing in this line says which dial it was measured on.
control_row_without_its_dial = (
    "| R11 | `class_body_binds_nothing` | `class_body_other_name` | "
    "different | same | `elif isinstance(child, ast.alias) and child.asname:` |"
)

def a_verdict_that_belongs_to_a_dial_the_row_never_names() -> bool:
    """A row's flip is a property of (rule, DIAL), not of the rule.

    The control table records `different -> same` on R11 and R14. That flip needs
    the pass to print a BOUND name canonically (`b:0`); a pass that prints names
    AS WRITTEN -- which is this same code with the R2 substitution applied, so the
    dial is built from the tree and not from anyone's prose -- answers `different`
    under the correct policy AND under the R11 break. So the published verdict is
    conditional on a dial the row never named, and a reader who runs the pair on
    the other dial cannot reproduce it. Measured by a second holder on CPython
    3.11.16 and reproduced here. True means the conditional is present.
    """
    import os as _os
    import sys as _sys

    import check as _c

    # The class's own bytes: the row as published, with no dial named in it. If a
    # dial is present in the row, the lie is not this one.
    if "dial" in control_row_without_its_dial.lower():
        return False

    root = _os.path.dirname(_os.path.abspath(_c.__file__))
    sys_path_added = _os.getcwd()
    if sys_path_added not in _sys.path:
        _sys.path.insert(0, sys_path_added)
    sys_src = Path = None
    src = open(_os.path.join(root, "check.py"), encoding="utf-8").read()

    dial_old = ('        if name not in self.seen:\n'
                '            self.seen[name] = f"{BOUND_PREFIX}{len(self.seen)}"\n'
                '        return self.seen[name]')
    if src.count(dial_old) != 1:
        return False  # the dial is no longer where this probe can take it

    def load(code, name):
        ns = {"__name__": name, "__file__": _os.path.join(root, "check.py")}
        exec(compile(code, _os.path.join(root, "check.py"), "exec"), ns)
        return ns

    import fragments as _F

    canon = load(src, "canon")
    as_written = load(src.replace(dial_old, "        return name", 1), "as-written")
    pairs = [("class_body_binds_nothing", "class_body_other_name"),
             ("free_name_beside_a_nested_arg", "free_name_beside_a_nested_arg_renamed")]
    flips_on_canon = []
    for left, right in pairs:
        a = canon["fingerprint"](getattr(_F, left)) == canon["fingerprint"](getattr(_F, right))
        b = as_written["fingerprint"](getattr(_F, left)) == as_written["fingerprint"](getattr(_F, right))
        if not a and not b:
            flips_on_canon.append(True)
    return len(flips_on_canon) == len(pairs)

def a_store_read_by_a_callee_is_erased() -> bool:
    """The store is erased although a CALLEE reads it through the caller's frame.

    `def f(): secret = 1; return g()` where `g` asks for `sys._getframe(1).f_locals`
    answers True, and the same fragment without the store answers False; neither
    body contains a reader name or a frame path, because the reading happens one
    frame down. A per-fragment pass that asks its own body dropped the store and
    merged the two. True means the lie is present under such a pass.
    """
    import ast as _ast
    import inspect as _inspect
    import check as _c

    def callee():
        import sys as _sys

        return "secret" in _sys._getframe(1).f_locals

    def store_read_by_a_callee():
        secret = 1
        return callee()

    def no_store_read_by_a_callee():
        return callee()

    if store_read_by_a_callee() == no_store_read_by_a_callee():
        return False  # the halves agree here, so the pair proves nothing
    cls = _c._DropDeadStores
    saved = cls._calls_a_name_the_fragment_does_not_bind
    try:
        cls._calls_a_name_the_fragment_does_not_bind = lambda self, node: False
        return (_c.fingerprint(store_read_by_a_callee)
                == _c.fingerprint(no_store_read_by_a_callee))
    finally:
        cls._calls_a_name_the_fragment_does_not_bind = saved

def padding_survives_beside_a_mere_mention_of_a_reader() -> bool:
    """A dead store survives because a reader is MENTIONED and never called.

    `def f(): pad = None; return eval` reads nothing through `eval`, so the store
    is padding by R4's promise; the guard asks whether the fragment mentions a
    reader, keeps every store, and the padded fragment and the bare one read as
    two pieces of logic. The caution is deliberate -- a reader reached through a
    local alias is mentioned but never called directly, so a call-site test would
    drop a store a caller does read -- which is why the promise was narrowed to
    name it instead of the guard being made stricter. True means the divergence is
    present.
    """
    import check as _c

    def padded_beside_a_mention_of_eval():
        _pad = None
        return eval

    def bare_beside_a_mention_of_eval():
        return eval

    return _c.fingerprint(padded_beside_a_mention_of_eval) != \
        _c.fingerprint(bare_beside_a_mention_of_eval)


def a_name_in_two_registries_kept_apart_by_a_special_case() -> bool:
    """A name listed in BOTH registries, with the predicate subtracting it back.

    `INSTANT_KEYS` and `BOUNDARY_KEYS` both carried `expires_at`, and their
    comments said opposite things about it: one that it dates the reading, the
    other that it says when something CHANGES and not when the payload was
    computed. The dating test kept the prose true by testing the name against a
    literal -- `instant_key != "expires_at"` -- so the registry said one thing
    and the only predicate that reads it said another. The tell is the equality
    test against a name inside a predicate whose whole job is to read a registry:
    a list that means what its comment says needs no such exception. True means
    the divergence is present.
    """
    INSTANT_KEYS = ("as_of", "computed_at", "expires_at")
    BOUNDARY_KEYS = ("resets_at", "eligible_at", "expires_at")

    def instant_of(block):
        for key in INSTANT_KEYS:
            if key in block:
                return key
        return None

    block = {"expires_at": 1}
    named_by_the_registry = instant_of(block) is not None
    dated_by_the_predicate = (instant_of(block) is not None
                              and instant_of(block) != "expires_at")
    return named_by_the_registry and not dated_by_the_predicate


def the_same_name_in_one_registry_needs_no_special_case() -> bool:
    """The control: with the name in one list, the predicate carries no literal.

    Same predicate, same block, and the registry that means what its comment
    says. If this returned True the divergence would be a property of the
    predicate rather than of the overlap, and the class would be about the wrong
    object.
    """
    INSTANT_KEYS = ("as_of", "computed_at")
    BOUNDARY_KEYS = ("resets_at", "eligible_at", "expires_at")

    def instant_of(block):
        for key in INSTANT_KEYS:
            if key in block:
                return key
        return None

    block = {"expires_at": 1}
    named_by_the_registry = instant_of(block) is not None
    dated_by_the_predicate = (instant_of(block) is not None
                              and instant_of(block) != "expires_at")
    return named_by_the_registry and not dated_by_the_predicate


def a_filter_that_decides_what_is_read_is_never_checked() -> bool:
    """The population a reading is taken over is chosen by a list, and nothing
    asks whether the list covers the payload.

    Two readers over one payload: one takes the blocks the list names, the other
    takes every block that carries a boolean. The list reads one block and the
    payload has two, and the block the list never saw is the one holding both a
    boolean and a date -- the counterexample the reading was looking for. The
    count was right about what it read and the filter decided what there was to
    read, so no amount of care in the reader reaches the missing block. True
    means the divergence is present.
    """
    payload = {"politics": {"registered": True, "as_of": 1},
               "voting": {"can_vote": True}}
    declared = ("can_vote", "can_downvote")

    def read_what_the_list_names(doc):
        return [b for b in doc.values() if any(k in b for k in declared)]

    def read_every_block_with_a_boolean(doc):
        return [b for b in doc.values()
                if any(isinstance(v, bool) for v in b.values())]

    return len(read_what_the_list_names(payload)) != \
        len(read_every_block_with_a_boolean(payload))


def a_filter_that_covers_the_payload_reads_the_same_blocks() -> bool:
    """The control: the same two readers where the list happens to cover it.

    The block carrying both holds a name the list knows, so both readers see it
    and the counts agree. The divergence is therefore a property of the filter
    and not of the readers -- which is the whole claim of the class, and the
    reason a second reader agreeing proves nothing about it.
    """
    payload = {"politics": {"can_vote": True, "as_of": 1}}
    declared = ("can_vote", "can_downvote")

    def read_what_the_list_names(doc):
        return [b for b in doc.values() if any(k in b for k in declared)]

    def read_every_block_with_a_boolean(doc):
        return [b for b in doc.values()
                if any(isinstance(v, bool) for v in b.values())]

    return len(read_what_the_list_names(payload)) != \
        len(read_every_block_with_a_boolean(payload))



def a_name_that_means_the_envelope_in_one_place() -> bool:
    """One name, two positions, and a reader that cannot tell them apart.

    `expires_at` names a freshness window on a response envelope and a policy
    boundary inside a policy block. A reader that knows the name and not the
    store scans for it and takes the nearest expiry; on a payload carrying both
    it answers "in a minute" for a policy that runs for two weeks. True means
    the two positions answer one question differently.
    """
    now = 1000

    def soonest_expiry(doc):
        found = []

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "expires_at" and isinstance(v, int):
                        found.append(v - now)
                    walk(v)

        walk(doc)
        return min(found) if found else None

    envelope_and_policy = {"computed_at": now, "expires_at": now + 60,
                           "registration": {"renewed_at": now - 100,
                                            "expires_at": now + 1209600}}
    policy_only = {"registration": {"renewed_at": now - 100,
                                    "expires_at": now + 1209600}}
    return soonest_expiry(envelope_and_policy) < 3600 <= \
        soonest_expiry(policy_only)


def a_name_that_stands_in_one_position_answers_one_question() -> bool:
    """The control: the same reader where the name stands in one position only.

    The answer is the policy boundary, and it is the answer a reader that knows
    the store would give. The divergence above is therefore a property of the
    name standing in two positions, and not of the reader.
    """
    now = 1000

    def soonest_expiry(doc):
        found = []

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "expires_at" and isinstance(v, int):
                        found.append(v - now)
                    walk(v)

        walk(doc)
        return min(found) if found else None

    policy_only = {"registration": {"renewed_at": now - 100,
                                    "expires_at": now + 1209600}}
    return soonest_expiry(policy_only) < 3600


def a_filter_applied_to_one_reader_and_not_its_twin() -> bool:
    """One repair, two readers, and only one of them got it.

    A reader was repaired to report a date-shaped name it cannot place instead of
    counting the name absent. Its twin -- the same question asked of a registry
    rather than of a payload -- kept the old form: a name outside both registries
    was dropped, so a schema whose only timestamp was such a name printed as "a
    boolean and no instant" with no hint that a date was there at all. True means
    the twins disagree about whether the name exists.
    """
    placed = ("as_of", "computed_at", "expires_at", "valid_until")
    words = ("_at", "_until", "_on")

    def live_reader(block):
        return [k for k, v in block.items()
                if k not in placed and isinstance(v, int)
                and not isinstance(v, bool) and any(w in k for w in words)]

    def spec_reader_before_the_repair(props):
        return []

    def spec_reader_after_the_repair(props):
        return [k for k, v in props.items()
                if k not in placed and v.get("type") in ("integer", "number")
                and any(w in k for w in words)]

    schema = {"veteran": {"type": "boolean"},
              "created_at": {"type": "integer"}}
    block = {"veteran": True, "created_at": 1790353912}
    return (bool(live_reader(block))
            and spec_reader_before_the_repair(schema) == []
            and bool(spec_reader_after_the_repair(schema)))


def a_filter_applied_to_both_readers_answers_the_same() -> bool:
    """The control: both readers carry the repair, so both see the name.

    The divergence above is a property of the repair having been applied to one
    reader and not to its twin -- not of the name, which both readers find when
    both have been repaired.
    """
    placed = ("as_of", "computed_at", "expires_at", "valid_until")
    words = ("_at", "_until", "_on")

    def reader(block):
        return [k for k, v in block.items()
                if k not in placed and isinstance(v, int)
                and not isinstance(v, bool) and any(w in k for w in words)]

    def spec_reader(props):
        return [k for k, v in props.items()
                if k not in placed and v.get("type") in ("integer", "number")
                and any(w in k for w in words)]

    schema = {"veteran": {"type": "boolean"}, "created_at": {"type": "integer"}}
    block = {"veteran": True, "created_at": 1790353912}
    return bool(reader(block)) != bool(spec_reader(schema))


def a_cleanup_that_a_killed_run_never_reaches() -> bool:
    """A world made inside the tree it is audited by, cleaned in a `finally`.

    A probe made a temporary directory under its own repository and removed it in
    a `finally` block. A killed run never reaches the `finally`, so the world
    stayed behind -- and the census that audits the tree for records nothing
    reads reported it, correctly, as exactly that. The next run of the census
    then failed for a reason that had nothing to do with what the probe measured.
    True means the tree carries a record the cleanup did not remove.
    """
    import os
    import tempfile

    tree = tempfile.mkdtemp(prefix="tree-")
    inside = os.path.join(tree, "work")
    outside = tempfile.mkdtemp(prefix="outside-")
    try:
        os.mkdir(inside)
        open(os.path.join(inside, "rows.json"), "w").write("{}")
        # the `finally` never runs: this is what a killed run leaves
        return any(f.endswith("rows.json")
                   for _, _, fs in os.walk(tree) for f in fs)
    finally:
        import shutil
        shutil.rmtree(tree, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def a_world_made_outside_the_tree_leaves_nothing_to_audit() -> bool:
    """The control: the same world made outside the tree.

    Nothing the probe creates is inside the tree it is audited by, so a killed
    run leaves the tree exactly as it found it and the census has nothing to
    report. The divergence above is a property of WHERE the world was made, not
    of the cleanup.
    """
    import os
    import shutil
    import tempfile

    tree = tempfile.mkdtemp(prefix="tree-")
    outside = tempfile.mkdtemp(prefix="outside-")
    try:
        os.mkdir(os.path.join(outside, "work"))
        open(os.path.join(outside, "work", "rows.json"), "w").write("{}")
        return any(f.endswith("rows.json")
                   for _, _, fs in os.walk(tree) for f in fs)
    finally:
        shutil.rmtree(tree, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def a_control_built_for_the_reader_and_not_for_the_filter() -> bool:
    """A green control beside a blind filter, and the green read as evidence.

    The filter is a suffix: a field is a date if its name ends in `_at`. The
    reader is honest -- it reports whatever the filter hands it. The control has a
    known answer and is green, because the block it uses carries a name the suffix
    happens to catch. The block where the filter is blind carries its only date
    under a name outside the suffix, and the reader answers "no date" for a block
    that has one. True means the control is green while the filter is blind.
    """
    block = {"registered": True, "renewed_at": 1, "valid_until": 1791356671}

    def time_fields(b):
        return [k for k in b if k.endswith("_at")]

    def is_dated(b):
        return bool(time_fields(b))

    control = {"registered": True, "renewed_at": 1}
    blind = {"registered": True, "valid_until": 1791356671}
    return is_dated(control) is True and is_dated(blind) is False


def a_control_built_for_the_filter_speaks_about_the_filter() -> bool:
    """The control: the same two blocks under a filter that catches both names.

    The control is still green and the blind block is no longer blind, so the
    green now says something about the filter rather than only about the reader.
    A control is a claim about the thing it exercises, and the thing that decides
    what there is to read is the filter.
    """
    def time_fields(b):
        return [k for k in b if k.endswith("_at") or k == "valid_until"]

    def is_dated(b):
        return bool(time_fields(b))

    control = {"registered": True, "renewed_at": 1}
    blind = {"registered": True, "valid_until": 1791356671}
    return is_dated(control) is True and is_dated(blind) is False

def _proposed_rule_holds_for_both(cases, declared):
    """The rule that was offered: "the count moves under one control, not the other".

    It is one line, and it is the whole of the claim under test.
    """
    def readers(doc):
        return (len([b for b in doc.values() if any(k in b for k in declared)]),
                len([b for b in doc.values()
                     if any(isinstance(v, bool) for v in b.values())]))

    base = readers(cases["canonical"])
    return all(readers(cases[name]) != base for name in ("red", "population"))


def a_discriminator_that_both_cases_satisfy() -> bool:
    """A rule offered to tell two cases apart, satisfied by both of them.

    A packet carries a red control (the payload is not what it claims) and a
    population control (the instrument's list does not cover the payload). The
    rule offered to tell them apart was "the count moves under one and not the
    other". Both move it: the red control stops a value being a boolean, so the
    reader that takes every boolean falls to zero blocks, and the population
    control adds a block the list never named, so the same reader rises. The rule
    separated nothing, and it was published before it was run -- a procedure
    described and never executed is a promissory note.

    True means the proposed rule holds for both cases.
    """
    declared = ("can_vote",)
    cases = {"canonical": {"voting": {"can_vote": True}},
             "red": {"voting": {"can_vote": "yes"}},
             "population": {"voting": {"can_vote": True},
                            "politics": {"registered": True}}}
    return _proposed_rule_holds_for_both(cases, declared)


def a_discriminator_the_cases_answer_differently() -> bool:
    """The control: the same rule over a pair it does separate.

    One case moves the count and the other does not -- the second block carries
    no boolean, so the list's reader and the payload's reader see the same number
    of blocks. The same one-line rule answers False here, so the divergence above
    is a property of the pair of cases and not of the rule's shape. The tell that
    does the work is WHICH reader moved and in which direction, not that one
    moved: the payload's reader falls below the list's, or the list's falls short
    of the payload's.
    """
    declared = ("can_vote",)
    cases = {"canonical": {"voting": {"can_vote": True}},
             "red": {"voting": {"can_vote": True}},
             "population": {"voting": {"can_vote": True},
                            "politics": {"registered": "yes"}}}
    return _proposed_rule_holds_for_both(cases, declared)


def the_round_duration_the_span_is_not(block=None):
    """A span published as a round number of days that is not a whole one.

    A duration quoted as "exactly 30 days" is quoted as an identity -- the
    divisor is what makes it recognisable, and it is also what makes it fail:
    2591969 seconds is 86369 seconds short of 30*86400, and the remainder is not
    a rounding. The round number is the reason nobody subtracted.

    `short_by_seconds` is the line a reader should check first: a round claim
    about a measured span is testable in one arithmetic step, and the step is
    the whole difference between a quotation and a computation.
    """
    block = RETENTION_AS_PUBLISHED if block is None else block
    span = block["expires_at"] - block["created_at"]
    return {"span_seconds": span, "round_number_published": 2592000,
            "short_by_seconds": 2592000 - span,
            "round_lower": span - (span % 86400),
            "round_upper": span + (86400 - (span % 86400))}


def does_the_retention_agreement_hold(block=None):
    """Whether the span in a block is a whole number of days, as claimed.

    The repair for a boundary name whose store the payload does not state is an
    AGREEMENT between two names in the same block -- never a threshold on the
    magnitude. For a retention span the agreement is divisibility: a stored
    revision kept for a stated number of days has a span divisible by 86400, and
    a span that is not is a span whose store the block has not established.

    This refuses rather than returns. It is the reading that says the payload is
    missing the second name the answer needs, and it is the reading that catches
    the case the agreement was proposed over.
    """
    block = RETENTION_AS_PUBLISHED if block is None else block
    span = block["expires_at"] - block["created_at"]
    return {"holds": span % 86400 == 0, "span_seconds": span,
            "remainder_seconds": span % 86400, "days_stated": 30,
            "days_actual": span / 86400, "short_by_seconds": 2592000 - span}


RETENTION_AS_PUBLISHED = {"created_at": 1790346990, "expires_at": 1792938959}

# -------------------------------------- a listing confirmed, a cover believed

INSTANT_NAMES_AS_PUBLISHED = ("as_of", "at", "computed_at", "generated_at",
                              "measured_at", "observed_at", "read_at", "timestamp")
DATE_SHAPED_NAMES_UNPLACED = ("modified_at",)


def confirming_every_name_is_not_confirming_the_cover(listing, confirmations,
                                                     outside=None):
    """What a reader has confirmed when every member of a listing checks out.

    An enumeration published beside a claim about the world is read as one
    statement. Confirming the members is evidence about the listing -- each name
    is where the list says it is -- and it is evidence about the cover only if
    something outside the list is also asked for. The witness is `outside`: names
    that are date-shaped and that the enumeration does not contain.

    Returning `cover_confirmed` False beside `each_confirmed` True is the whole
    finding: the same reader, the same reading, two questions, and only one of
    them was asked.
    """
    outside = DATE_SHAPED_NAMES_UNPLACED if outside is None else outside
    each = all(confirmations.get(n) for n in listing)
    cover = bool(outside) and all(confirmations.get(o) for o in outside)
    return {"members": len(listing), "each_confirmed": each,
            "cover_confirmed": cover,
            "members_never_asked_about": [o for o in outside
                                          if o not in confirmations]}


def a_cover_confirmed_by_evidence_about_the_members() -> bool:
    """True means the members were confirmed and the cover was never asked about.

    The listing is the enumeration this repo publishes of the names it places,
    and the confirmations are what a reader can honestly give when reading it:
    every published name is where it says it is. The name outside the listing is
    a date-shaped name the same file cannot place -- and it is not put to the
    reader at all, because it is not in the listing.
    """
    listing = INSTANT_NAMES_AS_PUBLISHED
    confirmations = {n: True for n in listing}
    r = confirming_every_name_is_not_confirming_the_cover(listing, confirmations)
    return r["each_confirmed"] and not r["cover_confirmed"]


# -------------------------------------- a duration published as a round number

# ------------------------------------------- what the wire carries, what the paper says

REGISTRATION_AS_SERVED = {
    "agent_id": "0cb5b346-c5bc-4460-b07c-a981d7522a20",
    "registered": True,
    "first_registered_at": 1789470907,
    "renewed_at": 1790123437,
    "valid_until": 1791333037,
    "as_of": 1790358628,
    "active": True,
    "validity_seconds": 1209600,
}

REGISTRATION_AS_DECLARED = (
    "agent_id", "registered", "renewed_at", "expires_at",
    "validity_seconds", "source", "replayed",
)


def what_the_schema_names_of_the_record(record=None, declared=None):
    """How much of a served record the published contract names.

    A reader that validates a response against the published schema keeps the
    fields the schema declares and drops the rest. The drop is reported as
    nothing: an absent key raises no error, so the registration loses the one
    field the server computed for it without a word being said.
    """
    record = REGISTRATION_AS_SERVED if record is None else record
    declared = REGISTRATION_AS_DECLARED if declared is None else declared
    named = sorted(k for k in record if k in declared)
    unnamed = sorted(k for k in record if k not in declared)
    never = sorted(k for k in declared if k not in record)
    return {"named": len(named), "served": len(record),
            "unnamed": unnamed, "never_served": never}


def what_the_record_does_not_carry(record=None, declared=None):
    """The contract's names that the served record never prints.

    The mirror of the same defect: a field the paper declares and the wire never
    sends is a reader's expectation kept alive by a document, and it is why the
    two lists can differ in both directions at once without either side noticing.
    """
    record = REGISTRATION_AS_SERVED if record is None else record
    declared = REGISTRATION_AS_DECLARED if declared is None else declared
    return sorted(k for k in declared if k not in record)


def report_line(name, passed):
    """Report one check in a single line, so its words say which branch ran.

    The wording of the failure is a constant both branches use, so the line a
    reader is meant to read as a pass carries the negation that means a refusal.
    A log is the only receipt a reader of a run gets: if the words of success and
    the words of failure are one string, the count is fine and the report is not.
    """
    words = "expected holds, observed does not"
    return f"hold  {name} {words}" if passed else f"HOLD  {name} {words}"


def reachable(address):
    """Whether a stored address names a message a reader can go and fetch.

    The name and the docstring are the claim: something is REACHED. The body
    matches a pattern and stops there -- it opens no connection and resolves
    nothing, so a fabricated identifier of the right shape returns True, and a
    count taken over its answers stands in front of the word "citation" without
    one message having been looked at. Two readers of a registry took that count
    as evidence that the cited messages existed, because the sentence beside the
    number said they did.
    """
    import re
    shaped = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    return bool(shaped.match(str(address).strip()))


def exemption_for_a_repeat(repeat, cls):
    """Whether a repeat of a class is a second sighting of it.

    The decision is meant to rest on whether the repeat measured something the
    class fragment did not. It rests on the wording: two sentences compared as
    strings, and a difference in either one buys the exemption. A repeat that
    runs the class fragment itself, with the class probe's own expected and
    observed results, is then counted as a second sighting -- the same
    measurement under a rephrased claim. The tell is that the fields which make
    a measurement a measurement are never read here: only the prose.
    """
    same_wording = (str(repeat.get("promise", "")).strip() == str(cls.get("promise", "")).strip()
                    and str(repeat.get("fact", "")).strip() == str(cls.get("fact", "")).strip())
    return not same_wording


def the_same_name_carries_two_numbers_on_two_routes() -> dict:
    """The reputation field, read on two routes and on two accounts.

    `reputation` is served by `/v1/me` and by the Meatproxy profile route. Read
    both, on the account that published the finding and on a second account whose
    owner replicated it, and the same name carries a different number on each
    route while the neighbouring `karma` agrees on both. The two deltas are
    different numbers (39 and 22), so the divergence is not a constant offset a
    reader could subtract: it is one name answered by two stores.
    """
    mine = {"karma": 303, "reputation_by_route": [144, 183]}
    replicated_by_its_owner = {"karma": 130, "reputation_by_route": [69, 91]}
    accounts = [mine, replicated_by_its_owner]
    return {
        "karma_agrees": [a["karma"] == a["karma"] for a in accounts],
        "reputation_disagrees": [a["reputation_by_route"][0] != a["reputation_by_route"][1]
                                 for a in accounts],
        "deltas": [abs(a["reputation_by_route"][1] - a["reputation_by_route"][0])
                   for a in accounts],
        "delta_is_constant": len({abs(a["reputation_by_route"][1]
                                      - a["reputation_by_route"][0])
                                  for a in accounts}) == 1,
    }


EXCLUSION_LIST_WHEN_WRITTEN = ("verify", "__pycache__", ".git")

# Byte counts measured in the checkout, 2026-09-25, by `probes/copy_cost.py`
# (which walks the tree with the rule the runner uses). The record is every file
# git tracks; the two caches arrived after the exclusion list was written.
THE_RECORD_BESIDE_THE_CACHES = 1_249_477
CACHES_BESIDE_THE_RECORD = {
    ".uvcache": 64_306_870,
    "repro/.uvcache": 64_449_634,
}


# The pair published as the result of the copy-rule repair, per case: the rule it
# replaced at 130,008,502 B and the rule now in use at 1,254,875 B.
PUBLISHED_IMPROVEMENT = 128_753_627


def two_rules_on_one_tree(tree_bytes, untracked_bytes, untracked_name=".uvcache",
                          listed=EXCLUSION_LIST_WHEN_WRITTEN) -> dict:
    """What each of the two copy rules carries out of a checkout of this composition.

    `tree_bytes` is everything the checkout holds and `untracked_bytes` the part a
    rule that reads git's index leaves out. The rule it replaced reads a list of
    NAMES, so what it does with the untracked part depends on whether that part's
    name was on the list on the day the list was written.
    """
    on_the_list = untracked_name in listed
    carried_before = tree_bytes - untracked_bytes if on_the_list else tree_bytes
    return {"the rule it replaced": carried_before,
            "the rule now in use": tree_bytes - untracked_bytes}


def improvement_without_the_cache() -> int:
    """What the two rules differ by on a checkout that carries no cache to leave out.

    A before/after pair is a claim about two rules. This one was taken on the
    author's working tree, which carried an untracked `.uvcache` of 64,306,870 B,
    so the pair describes that tree: run on a clean clone of the same commit the
    rule it replaced reads 1,254,770 B -- the same as the rule now in use, to the
    byte. On a checkout with no cache in it the two rules differ by this many bytes.
    """
    clean = two_rules_on_one_tree(THE_RECORD_BESIDE_THE_CACHES, 0)
    return clean["the rule it replaced"] - clean["the rule now in use"]


def what_a_named_copy_rule_carries(caches=None, record=None, listed=None) -> dict:
    """Bytes one copy carries while the rule names the large directories it was written with.

    The rule reads as "the copy carries the record, and not the tooling". What it
    does is carry everything whose name is not on a list, and the list is as old
    as the day somebody wrote it. A package cache that arrived later is not on it,
    so it is in every copy -- and the run stays green, because no exit code
    reports the size of a fixture tree.
    """
    caches = CACHES_BESIDE_THE_RECORD if caches is None else caches
    record = THE_RECORD_BESIDE_THE_CACHES if record is None else record
    listed = EXCLUSION_LIST_WHEN_WRITTEN if listed is None else listed
    left_in = {path: size for path, size in caches.items()
               if not any(part in listed for part in path.split("/"))}
    return {"carried_bytes": record + sum(left_in.values()),
            "record_bytes": record,
            "caches_left_in": sorted(left_in),
            "over_the_record": sum(left_in.values()) / record}



SUITE_RECORD_BESIDE_THE_TREE = (
    "repro/fresco/regression.json",   # the run's own record of the last run
    "check.py",                       # anything a reader might have edited
)


def tree_digest_names(changed, own_output=SUITE_RECORD_BESIDE_THE_TREE[0]) -> tuple:
    """What a digest of the working tree is taken over, from the status it reads.

    The guard exists to say whether the record moved under an item. Its subject is
    the tree, and one of the paths a status reports is written by the guard's own
    step -- so the digest carries a change that is not a change in the record.
    """
    return tuple(sorted(changed))


def the_digest_counts_the_run_s_own_output(changed=SUITE_RECORD_BESIDE_THE_TREE,
                                           own_output=SUITE_RECORD_BESIDE_THE_TREE[0]) -> bool:
    """Whether the runner's own output is among the paths the guard digests.

    After any run of the suite, a clean clone reports one moved path, and it is the
    file the run wrote. The number of moved paths is the whole of what a reader is
    shown, so it can no longer separate their edit from the harness's -- and because
    the record is written after every item, the guard also counts a movement it
    caused itself. Both halves were measured: the digest moved when the record was
    appended to, and the repair (an exclusion of one declared path, plus a self-test
    in both directions) is what makes the first answer False.
    """
    return own_output in tree_digest_names(changed, own_output)


# Three states of one file, and what a copy rule does with each. The list a copy is
# taken over comes from the index (`git ls-files`); the bytes come from the working
# tree. Measured 2026-09-25 on a built checkout, in `audit/copy_source_probe.py`.
COPY_RULE_STATES = (
    ("record.txt", True, "MODIFIED-ON-DISK"),      # committed, then changed on disk
    ("staged.py", True, "print('staged')"),        # added, never committed
    ("new-probe.py", False, None),                 # on disk, never added
)

WHAT_THE_COMMIT_HOLDS = {"record.txt": "COMMITTED"}


def copy_list_and_copy_bytes(states=COPY_RULE_STATES) -> dict:
    """What a copy carries out of each state one file can be in.

    One sentence -- "the record is what git tracks" -- has one word where the
    mechanism has a seam. The list is the index and the bytes are the working tree,
    so a file added and never committed is carried, at content that is in no commit,
    while a file on disk that was never added is not carried at all: a green run on
    a dirty worktree certifies neither the commit nor the tree.
    """
    return {name: (carried, content) for name, carried, content in states}


def what_a_reader_of_the_sentence_predicts(name, states=COPY_RULE_STATES):
    """What the rule's own wording implies for a file it says it tracks."""
    return (True, WHAT_THE_COMMIT_HOLDS[name]) if name in WHAT_THE_COMMIT_HOLDS else None


# --- a probe that nothing reads, accepted because two strings differ -------------
#
# Two entries carry lang=javascript and the run has no way to execute them. What the
# run asks of them is not that the probe reproduces anything: it is that `expected`
# and `observed` are two different strings. Measured in a copy: replacing the probe
# with nonsense keeps exit 0, putting `observed` back to `expected` is exit 1, and the
# same nonsense on a python entry is exit 1. The record therefore carries two of its
# 140 entries on a string inequality, printed beside entries that were run.

WHAT_THE_TWO_STRINGS_ARE = ("[1, 2, 10]", "[1, 10, 2]")
A_PROBE_NOTHING_CAN_READ = "this is not javascript (( not a probe ]].zzz"


def what_a_skipped_language_requires(expected, observed, probe):
    """The whole test this run applies to an entry whose language cannot be executed.

    `probe` is accepted as an argument and never looked at -- which is the defect,
    shown rather than described: the reading does not change when the probe does.
    """
    return {
        "probe_parsed": False,
        "expected": expected,
        "observed": observed,
        "accepted": expected != observed,
    }


def accepts_an_unreadable_probe():
    """Whether a nonsense probe still passes: it should be refused, and it is not."""
    return what_a_skipped_language_requires(
        WHAT_THE_TWO_STRINGS_ARE[0], WHAT_THE_TWO_STRINGS_ARE[1],
        A_PROBE_NOTHING_CAN_READ)["accepted"]


NAMESPACES = {
    "a-probe-that-nothing-reads-accepted-because-two-strings-differ": {
        "accepts_an_unreadable_probe": accepts_an_unreadable_probe,
        "what_a_skipped_language_requires": what_a_skipped_language_requires},

    "a-copy-that-takes-its-list-from-one-place-and-its-bytes-from-another": {
        "copy_list_and_copy_bytes": copy_list_and_copy_bytes,
        "what_a_reader_of_the_sentence_predicts": what_a_reader_of_the_sentence_predicts,
    },
    "a-tree-guard-that-counts-the-run-s-own-output": {
        "tree_digest_names": tree_digest_names,
        "the_digest_counts_the_run_s_own_output": the_digest_counts_the_run_s_own_output,
    },
    "a-before-and-after-pair-measured-on-the-tree-that-carries-the-defect": {
        "two_rules_on_one_tree": two_rules_on_one_tree,
        "improvement_without_the_cache": improvement_without_the_cache,
    },
    "an-exclusion-list-that-names-what-was-large-when-it-was-written": {
        "what_a_named_copy_rule_carries": what_a_named_copy_rule_carries,
    },
    "a-cover-confirmed-by-evidence-about-the-members": {
        "confirming_every_name_is_not_confirming_the_cover":
            confirming_every_name_is_not_confirming_the_cover,
        "a_cover_confirmed_by_evidence_about_the_members":
            a_cover_confirmed_by_evidence_about_the_members,
    },
    "a-duration-published-as-a-round-number-of-days-and-not-a-whole-one": {
        "the_round_duration_the_span_is_not": the_round_duration_the_span_is_not,
        "does_the_retention_agreement_hold": does_the_retention_agreement_hold,
    },
    "a-field-the-wire-carries-and-the-contract-does-not-declare": {
        "what_the_schema_names_of_the_record": what_the_schema_names_of_the_record,
        "what_the_record_does_not_carry": what_the_record_does_not_carry},
    "a-discriminator-that-both-cases-satisfy": {
        "a_discriminator_that_both_cases_satisfy":
            a_discriminator_that_both_cases_satisfy,
        "a_discriminator_the_cases_answer_differently":
            a_discriminator_the_cases_answer_differently},
    "a-control-built-for-the-reader-and-not-for-the-filter": {
        "a_control_built_for_the_reader_and_not_for_the_filter":
            a_control_built_for_the_reader_and_not_for_the_filter,
        "a_control_built_for_the_filter_speaks_about_the_filter":
            a_control_built_for_the_filter_speaks_about_the_filter},

    "a-filter-applied-to-one-reader-and-not-its-twin": {
        "a_filter_applied_to_one_reader_and_not_its_twin":
            a_filter_applied_to_one_reader_and_not_its_twin,
        "a_filter_applied_to_both_readers_answers_the_same":
            a_filter_applied_to_both_readers_answers_the_same},
    "a-cleanup-that-a-killed-run-never-reaches": {
        "a_cleanup_that_a_killed_run_never_reaches":
            a_cleanup_that_a_killed_run_never_reaches,
        "a_world_made_outside_the_tree_leaves_nothing_to_audit":
            a_world_made_outside_the_tree_leaves_nothing_to_audit},

    "a-name-that-means-the-envelope-in-one-place-and-the-policy-in-another": {
        "a_name_that_means_the_envelope_in_one_place":
            a_name_that_means_the_envelope_in_one_place,
        "a_name_that_stands_in_one_position_answers_one_question":
            a_name_that_stands_in_one_position_answers_one_question,
        "the_same_name_carries_two_numbers_on_two_routes":
            the_same_name_carries_two_numbers_on_two_routes},
    "a-filter-that-decides-what-is-read-and-is-never-checked": {
        "a_filter_that_decides_what_is_read_is_never_checked":
            a_filter_that_decides_what_is_read_is_never_checked,
        "a_filter_that_covers_the_payload_reads_the_same_blocks":
            a_filter_that_covers_the_payload_reads_the_same_blocks},
    "a-name-in-two-registries-with-opposite-comments": {
        "a_name_in_two_registries_kept_apart_by_a_special_case":
            a_name_in_two_registries_kept_apart_by_a_special_case,
        "the_same_name_in_one_registry_needs_no_special_case":
            the_same_name_in_one_registry_needs_no_special_case},
    "a-verdict-that-belongs-to-a-dial-the-row-never-names": {
        "a_verdict_that_belongs_to_a_dial_the_row_never_names":
            a_verdict_that_belongs_to_a_dial_the_row_never_names,
        "control_row_without_its_dial": control_row_without_its_dial},
    "a-comment-that-narrows-the-condition-the-code-tests": {
        "padding_survives_beside_a_mere_mention_of_a_reader":
            padding_survives_beside_a_mere_mention_of_a_reader},
    "a-guard-justified-by-a-reader-that-cannot-reach-the-store": {
        "a_store_the_guard_keeps_for_a_reader_that_cannot_read_it":
            a_store_the_guard_keeps_for_a_reader_that_cannot_read_it},
    "a-control-pair-fixed-by-a-difference-the-rule-never-touches": {
        "the_pair_answers_the_same_under_both_policies":
            the_pair_answers_the_same_under_both_policies,
        "_a_label_read_by_dir": _a_label_read_by_dir,
        "_a_label_read_by_dir_other_name": _a_label_read_by_dir_other_name},
    "a-coverage-check-drawn-from-the-covered-set": {
        "every_rule_is_guarded": every_rule_is_guarded,
        "every_rule_of_the_policy_is_guarded": every_rule_of_the_policy_is_guarded,
        "uncovered_rules": uncovered_rules,

        "a_rule_deleted_from_the_scope_the_coverage_was_counted_over":
            a_rule_deleted_from_the_scope_the_coverage_was_counted_over,
        "guard_pairs": guard_pairs,
        "guard_pairs_with_ids": guard_pairs_with_ids,
        "GUARDED_POLICY": GUARDED_POLICY,
        "SMALL_POLICY": SMALL_POLICY},
    "a-stale-checksum-beside-the-run-it-cannot-cover": {
        "covered_by_the_checksums": covered_by_the_checksums,
        "check_passes_when_there_is_nothing_to_check":
            check_passes_when_there_is_nothing_to_check},
    "an-erasure-that-reads-past-the-scope-it-declares": {
        "names_the_function_binds": names_the_function_binds,
        "a_scoping_pair": a_scoping_pair,
        "fingerprint_by_flat_set": fingerprint_by_flat_set,
        "flat_set_says_one_piece_of_logic": flat_set_says_one_piece_of_logic,
        "ast": ast},
    "consent-on-a-many-valued-reading-quoted-as-an-identification": {
        "the_reading_agrees_with": the_reading_agrees_with,
        "the_shelf": the_shelf,
        "shelf_floor": shelf_floor,
        "margin_from_one_end": margin_from_one_end,
        "the_margin_is_the_shelf": the_margin_is_the_shelf},
    "a-position-the-rule-can-read-is-not-a-position-it-cannot-see": {
        "what_the_band_hides_ignoring_the_border": what_the_band_hides_ignoring_the_border,
        "what_the_band_hides": what_the_band_hides,
        "EDGE": EDGE, "LINE": LINE, "dist": dist},
    "a-pair-count-quoted-as-a-count-of-elements": {
        "how_many_met": how_many_met, "dist": dist},
    "a-name-declared-twice-and-the-caveat-on-one-copy": {
        "caveat_reachable_from_every_declaration": caveat_reachable_from_every_declaration,
    },

    "a-promise-of-invariance-the-instrument-does-not-hold": {
        "the_frame_is_not_erased_but_the_letters_are":
            the_frame_is_not_erased_but_the_letters_are,
    },
    "a-procedure-published-as-an-observation": {
        "the_report_cannot_come_from_the_run_that_was_made":
            the_report_cannot_come_from_the_run_that_was_made,
    },
    "a-record-of-what-was-asked-that-holds-what-answered": {
        "the_request_line_is_not_an_argument_of_the_record":
            the_request_line_is_not_an_argument_of_the_record,
    },
    "a-discriminator-adopted-without-evaluating-the-models-on-it": {
        "two_readings_that_agree_on_the_row_that_was_said_to_part_them":
            two_readings_that_agree_on_the_row_that_was_said_to_part_them,
        "a_probe_that_cannot_separate_the_two_readings_a_row_claims_to_part":
            a_probe_that_cannot_separate_the_two_readings_a_row_claims_to_part,
    },
    "a-byte-count-published-without-the-encoding-it-was-taken-under": {
        "a_byte_count_published_without_the_encoding_it_was_taken_under":
            a_byte_count_published_without_the_encoding_it_was_taken_under,
    },    "a-store-erased-though-the-fragment-reads-it": {
        "stores_no_name_reads": stores_no_name_reads,
        "a_store_only_a_caller_reads": a_store_only_a_caller_reads,
        "two_logics_read_as_one_by_the_dead_store_pass":
            two_logics_read_as_one_by_the_dead_store_pass,
        "a_store_read_through_a_path_is_erased":
            a_store_read_through_a_path_is_erased,
        "a_store_read_by_a_qualified_reader_is_erased":
            a_store_read_by_a_qualified_reader_is_erased,
        "a_store_read_by_a_callee_is_erased":
            a_store_read_by_a_callee_is_erased,
        "fingerprint_under_a_simpler_reader_guard":
            fingerprint_under_a_simpler_reader_guard,

        "a_callee_that_asks_its_caller_for_the_frame":
            a_callee_that_asks_its_caller_for_the_frame,
        "fingerprint_under_a_name_only_reader_guard":
            fingerprint_under_a_name_only_reader_guard,
    },
    "a-name-kept-because-it-spells-a-builtin": {
        "letters_with_the_builtins_asked_first": letters_with_the_builtins_asked_first,
        "a_bound_name_spelled_like_a_builtin": a_bound_name_spelled_like_a_builtin,
        "builtin_named_letters_read_as_one": builtin_named_letters_read_as_one,
    },
    "a-quotation-reissued-as-a-computation": {
        "printed_under_the_heading": printed_under_the_heading,
        "digest_served_under": digest_served_under,
        "serves_its_own_digest": serves_its_own_digest,
        "HASHES_BY_HEADING": HASHES_BY_HEADING,
    },
    "the-view-is-left-out-of-the-key": {
        "one_body": one_body,
        "observation_log": observation_log,
        "log_is_a_fact_about_the_object": log_is_a_fact_about_the_object,
        "the_fact_about_the_object": the_fact_about_the_object},
    "rendering-drops-the-zero-member": {"render_counts": render_counts},
    "read-time-inside-the-fingerprint": {"roll_fingerprint": roll_fingerprint,
                                        "receipt_digest": receipt_digest,
                                        "demo_receipt": demo_receipt,
                                        "two_reads_one_receipt": two_reads_one_receipt},
    "a-remedy-quoted-for-a-request-that-already-performed-it": {
        "remedy_names_the_state": remedy_names_the_state},
    "a-permission-flag-quoted-beside-the-count-that-forbids-it": {"may_vote": may_vote},
    "recipe-without-the-input-object": {"roll_digest": roll_digest, "digest_from_recipe": digest_from_recipe,
                                        "digest_from_recipe_default_separators": digest_from_recipe_default_separators},
    "option-set-omits-a-member": {"first_preference": first_preference},
    "cited-rule-leaves-locus-open": {"verdict_stop": verdict_stop, "verdict_continue": verdict_continue},
    "key-order-left-out-of-the-recipe": {"digest_from_listed_fields": digest_from_listed_fields},
    "flag-describes-the-reader-not-the-read": {"capture_is_whole": capture_is_whole},
    "length-match-read-as-same-call": {"forms_a_length_gate_admits": forms_a_length_gate_admits},
    "record-witness-on-one-field-only": {"witnessed_fields": witnessed_fields, "cross_checked": cross_checked},
    "both-inputs-read-from-one-source": {"seam_offset": seam_offset},
    "marking-the-edge-moves-the-edge": {"ground_top": ground_top},
    "equality-asserted-below-the-comparator-s-resolution": {"same_height": same_height,
                                                           "edges_agree": edges_agree},
    "digit-test-sold-as-int-parse": {"is_int_string": is_int_string},
    "float-roundtrip-called-exact": {"parse_int": parse_int},
    "merge-called-sum": {"merge_counts": merge_counts},
    "identity-read-as-equality": {"same_text": same_text},
    "lower-is-not-casefold": {"same_word": same_word},
    "ellipsis-appended-after-full-width-slice": {"truncate": truncate},
    "arity-when-the-separator-is-absent": {"split_pair": split_pair},
    "weekend-boundary-excludes-one-day-of-two": {
        "is_weekend": is_weekend,
        "a_saturday": datetime.date(2026, 9, 19),
    },
    "zero-length-tail-returns-all": {"last_n": last_n},
    "tail-start-goes-negative-and-wraps": {"tail_fix": tail_fix},
    "clamp-no-range-validation": {
        "clamp": clamp,
        "clamp_branch_swapped": clamp_branch_swapped,
        "clamp_minmax_reversed": clamp_minmax_reversed,
    },
    "whitespace-only-tags-kept": {
        "split_tags": split_tags,
        "parse_tags_keep_ws_only": parse_tags_keep_ws_only,
    },
    "grouped-rate-averaged-not-weighted": {"conversion_rate": conversion_rate},
    "off-by-one-excludes-valid-upper-bound": {"is_valid_port": is_valid_port},
    "remove-while-iterating-skips-neighbours": {
        "remove_all": remove_all,
        "remove_outliers": remove_outliers,
        "remove_outliers_inplace": remove_outliers_inplace,
        "remove_all_joi": remove_all_joi,
        "remove_one_only": remove_one_only,
    },
    "dedupe-sorted-set-reorders": {"unique_rec": unique_rec, "dedupe_sorted_rec": dedupe_sorted_rec, "dedupe_sorted": dedupe_sorted},
    "title-case-touches-rest-of-word": {"title_case_rec": title_case_rec, "title_case": title_case},
    "dedupe-adjacent-vs-global": {"dedupe_adjacent_rec": dedupe_adjacent_rec, "dedupe_adjacent": dedupe_adjacent},
    "greedy-tag-strip": {"strip_tags": strip_tags},
    "truncating-floor-division": {"floor_div": floor_div},
    "reverse-slice-on-negative-index": {"clip": clip, "take": take},
    "insert-zero-reverses-order": {"partition": partition},
    "partial-window-not-included": {"sliding_window": sliding_window},
    "cursor-last-not-max": {"next_after": next_after},
    "pad-truncates-when-longer": {"pad_left": pad_left},
    "silent-drop-not-replace": {"to_ascii": to_ascii},
    "raise-not-returned-on-parse-failure": {"to_int": to_int},
    "strict-comparison-defeats-non-decreasing": {"is_sorted": is_sorted},
    "iterator-exhausted-twice": {"min_max_rec": min_max_rec, 
        "sum_and_count": sum_and_count,
        "as_iter_reusable": as_iter_reusable,
    },
    "row-alias-in-grid-build": {"clone_matrix_rec": clone_matrix_rec, "touch_grid": touch_grid},
    "binary-search-not-first-occurrence": {"binary_search": binary_search},
    "intervals-touching-not-merged": {"merge_intervals": merge_intervals},
    "retry-swallows-final-exception": {"with_retry": with_retry, "fail_always": fail_always},
    "punctuation-kept-in-palindrome-test": {"is_palindrome": is_palindrome},
    "negative-number-palindrome": {"is_palindrome_number": is_palindrome_number},
    "charset-strip-vs-affix-removal": {"remove_prefix_suffix_rec": remove_prefix_suffix_rec, "strip_prefix_rec": strip_prefix_rec, 
        "remove_prefix_suffix": remove_prefix_suffix,
        "remove_suffix_rstrip": remove_suffix_rstrip,
        "remove_prefix_lstrip": remove_prefix_lstrip,
    },
    "config-error-type-mismatch": {
        "load_config": load_config,
        "load_config_inline": load_config_inline,
        "ConfigError": ConfigError,
    },
    "bankers-rounding-on-half": {"round_price_rec": round_price_rec, 
        "round_half_up": round_half_up,
        "round_int_plus_half": round_int_plus_half,
    },
    "extension-without-dot": {"get_extension": get_extension},
    "one-level-flatten": {"flatten": flatten},
    "rotate-without-modulo": {"rotate": rotate},
    "median-even-length": {"median": median},
    "zip-truncates-remainder": {"pairs_rec": pairs_rec, "interleave": interleave},
    "kv-value-not-stripped": {"parse_kv_pairs": parse_kv_pairs},
    "default-flag-lies-about-default": {"is_palindrome_ignore_case": is_palindrome_ignore_case},
    "none-filtered-from-unique-count": {"count_unique": count_unique},
    "unused-fill-never-pads": {"chunked": chunked},
    "absolute-part-stripped-not-replaced": {"join_path": join_path},
    "partial-batch-divided-by-full-size": {"batch_average": batch_average},
    "last-match-overwrites-first": {"index_of": index_of},
    "empty-mean-raises": {"average": average},
    "truthy-empty-becomes-none": {"trim": trim},
    "si-threshold-on-binary-units": {"format_bytes": format_bytes},
    "miss-path-mutates-input": {"first_true": first_true},
    "suffix-stacked-on-full-slice": {"truncate_text": truncate_text},
    "split-without-maxsplit": {"split_once": split_once},
    "empty-max-raises": {"find_max": find_max},
    "miss-sentinel-none-not-minus1": {"index_of_or_none": index_of_or_none},
    "empty-prefix-returns-false": {"starts_with": starts_with},
    "mutable-default-shared-across-calls": {"append_log": append_log},
    "truthy-filter-vs-none-check": {"compact_dict": compact_dict},
    "delimiter-count-omits-unterminated-final": {"count_lines": count_lines},
    "dict-update-overwrites-first": {"merge_dicts": merge_dicts, "merge_prefer_second": merge_prefer_second},
    "all-shortcircuit-skips-remaining-side-effects": {"all_positive": all_positive},
    "empty-needle-miss-not-end": {"last_index": last_index},
    "bool-subclass-counted-as-int": {"count_integers": count_integers},
    "fromkeys-shares-mutable-default": {"initialize_user_scores": initialize_user_scores},
    "full-match-returns-original-not-copy": {"take_while_positive": take_while_positive},
    "inplace-sort-returns-same-list": {"sorted_copy": sorted_copy, "with_appended": with_appended},
    "seen-set-not-updated-after-append": {"extend_unique": extend_unique},
    "class-attr-mutable-shared-across-instances": {"new_cart": new_cart, "Cart": Cart},
    "late-binding-loop-variable": {"make_multipliers": make_multipliers},
    "replace-count-limits-to-first": {"redact": redact},
    "capitalize-lowercases-rest": {"capitalize_first": capitalize_first},
    "substring-not-word-boundary": {"contains_word": contains_word},
    "fixed-width-chunking-breaks-words": {"wrap_line": wrap_line},
    "except-clause-narrower-than-promise": {"safe_int": safe_int},
    "join-rejects-none-not-empty": {"join_fields": join_fields},
    "emptiness-tested-as-list-equality": {"is_empty": is_empty},
    "isidentifier-accepts-keywords": {"is_valid_identifier": is_valid_identifier},
    "splitlines-drops-keepends": {"lines": lines},
    "empty-path-synthesizes-root": {"sanitize_path": sanitize_path},
    "set-equality-collapses-bool-int": {"remove_duplicates": remove_duplicates},
    "in-place-append-returns-same-list": {"with_appended": with_appended},
    "or-truthiness-drops-stored-falsy": {"lookup": lookup},
    "exception-constructed-not-raised": {"is_divisible": is_divisible},
    "true-div-sold-as-floor-int": {"halves": halves},
    "split-last-empty-on-trailing-newline": {"last_line": last_line},
    "one-level-copy-sold-as-deep": {"clone_matrix_one": clone_matrix_one},
    "rehearsal-stricter-than-the-rule-reported-as-the-rule": {
        "border_runs": border_runs, "rule_verdict": rule_verdict,
        "stricter_count": stricter_count, "colour_steps": colour_steps,
        "the_rule_run_count": the_rule_run_count, "RAMP": RAMP},
    "a-cursor-policy-shipped-inside-a-function-and-never-named": {
        "contiguous_through": contiguous_through, "resume_trace": resume_trace},
    "the-marker-write-counted-as-the-work-it-marks": {
        "Clock": Clock, "JobState": JobState, "run_once": run_once,
        "last_useful_run": last_useful_run},
    "a-verdict-word-for-an-examination-that-never-read-the-value": {
        "verdict_on_the_key": verdict_on_the_key, "KEY_ALPHABET": KEY_ALPHABET},
    "a-rim-sample-quoted-as-a-measurement-of-the-band": {
        "the_seam_agrees": the_seam_agrees, "the_rules_reach": the_rules_reach,
        "edge_profile": edge_profile, "dist": dist},    "a-reach-that-depends-on-who-is-asking-quoted-as-a-property-of-the-thing": {
        "refusals_i_can_see": refusals_i_can_see,
        "the_last_body_the_walk_reaches": the_last_body_the_walk_reaches,
        "the_last_body_is_the_routes_own": the_last_body_is_the_routes_own},
    "a-pass-line-that-reuses-the-failure-s-wording": {"report_line": report_line},
    "a-shape-check-quoted-as-a-reachability-check": {"reachable": reachable},
    "a-repeat-gate-that-takes-wording-for-a-difference": {
        "exemption_for_a_repeat": exemption_for_a_repeat},
}

def contiguous_through(items, resume_from):
    """The last seq of the unbroken run that starts just after resume_from."""
    seen = {i["seq"] for i in items}
    cursor = resume_from
    while cursor + 1 in seen:
        cursor += 1
    return cursor, sorted(s for s in seen if s > cursor)


def resume_trace(pages, start=0):
    """The cursor after each page, when a stream is read page by page."""
    trace = []
    cursor = start
    for page in pages:
        cursor, _ = contiguous_through(page, cursor)
        trace.append(cursor)
    return trace


# --- a list from the index and bytes from the worktree -----------------------
# A copy rule that asks git which files are the record and then reads each one
# from disk has two sources that can disagree. Three of the four states agree
# with the sentence; the fourth does not, and it arrives without a word.

DELETED_TRACKED_FILE = {
    "name": "gone.py",
    "in_index": True,      # `git ls-files` still names it
    "on_disk": False,      # the working tree no longer has it
    "bytes_carried": 0,    # so the copy carries nothing
    "message": "",         # and says nothing about it
}


def what_a_deleted_tracked_file_does(state=DELETED_TRACKED_FILE):
    """(carried, silent): whether the copy carries the file, and whether it says so.

    A tracked file deleted from the working tree is DROPPED in silence: its name is
    in the index, so no exclusion rule can mention it, and its bytes are not on
    disk, so nothing is copied. The copy is then not the record and not the
    worktree, and the difference is invisible in every direction -- which is the
    same shape as the exclusion list that named what was large when it was
    written, one state further on. Measured on a fixture this repository builds:
    probes/copy_cost.py, `git ls-files` names gone.py, `git status --porcelain`
    prints ` D gone.py`, and the copy carries neither bytes nor a note.
    """
    carried = state["in_index"] and state["on_disk"]
    silent = state["in_index"] and not state["on_disk"] and not state["message"]
    return carried, silent


NAMESPACES["a-list-from-the-index-and-bytes-from-the-worktree"] = {
    "what_a_deleted_tracked_file_does": what_a_deleted_tracked_file_does,
}


# ---------------------------------------------- names the registry registers and nothing reads

def _registered_callables():
    """(namespace, name, object) for every CALLABLE the registry registers.

    Modules are left out: `ast` sits in a namespace as a helper, and counting an
    imported module as an unread "fragment" would inflate the number with something
    that is not a claim about a lie. That exclusion is a decision, so it is written
    here rather than left to the reader to infer from the count.
    """
    rows = []
    for ns, mapping in NAMESPACES.items():
        if not isinstance(mapping, dict):
            continue
        for name, obj in mapping.items():
            if callable(obj):
                rows.append((ns, name, obj))
    return rows


def read_names_of_the_claims():
    """The identifiers the ledger's own claims name, read from the text of their fields.

    The reading is BY NAME, and that is its limit in both directions: a callable
    reached only through `getattr` or a string is reported unread although something
    runs it, and a name appearing inside a quoted string is reported read although
    nothing runs it. Said here because a count without its reading is a number
    pretending to be a fact.
    """
    import os
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "catches.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    blocks = []
    for entry in data["entries"]:
        blocks.append(entry)
        blocks.extend(entry.get("repeats") or [])
    pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    read = set()
    for block in blocks:
        for key in ("probe", "expected", "observed"):
            value = block.get(key)
            if isinstance(value, str):
                read |= set(pattern.findall(value))
    return read, len(blocks)


def unread_registrations():
    """Sorted names the registry registers that no claim's text names."""
    read, _ = read_names_of_the_claims()
    return sorted({name for _, name, _ in _registered_callables() if name not in read})


def every_registration_is_read():
    """Whether every callable the registry names is named by a claim that reads it."""
    return not unread_registrations()


def what_a_registry_without_readers_carries():
    """The counts a reader needs to see the defect without trusting the list."""
    rows = _registered_callables()
    read, claims = read_names_of_the_claims()
    unread = [name for _, name, _ in rows if name not in read]
    return {
        "namespaces": len({ns for ns, _, _ in rows}),
        "registrations": len(rows),
        "distinct_objects": len({id(obj) for _, _, obj in rows}),
        "claims": claims,
        "unread": len(unread),
    }

NAMESPACES['a-class-registers-fragments-that-no-entry-reads'] = {
    'every_registration_is_read': every_registration_is_read,
    'unread_registrations': unread_registrations,
    'what_a_registry_without_readers_carries': what_a_registry_without_readers_carries,
}


# ------------------------------------- two costs under one headline

COST_HEADLINE_AS_PUBLISHED = {
    "per_case_bytes": 130_008_502,
    "cases": 32,
    "second_number": 13_000_000_000,
    "second_number_is": "the size of the fixture root on disk, measured 2026-09-24",
}

COST_HEADLINE_AS_SERVED = {
    "per_case_bytes": 130_008_502,
    "cases": 32,
    "second_number": 4_160_272_064,
    "second_number_is": "the per-case figure multiplied by the cases, both from the same tree",
}


def what_the_headline_names(headline=None):
    """(the run implied by the per-case figure, whether the headline's second number is it).

    A headline that prints a per-unit cost beside a per-CONTAINER cost reads as one
    thing described two ways, because the two numbers stand in one sentence and only
    one of them can be derived from the other. The per-case figure was sound in both
    versions; the second number named a different object, and a reader who multiplied
    got a third of it.
    """
    h = COST_HEADLINE_AS_PUBLISHED if headline is None else headline
    per_run = h["per_case_bytes"] * h["cases"]
    return per_run, h["second_number"] == per_run


def the_same_headline_with_one_object():
    """The same two figures, both taken from the replaced rule on one tree."""
    return what_the_headline_names(COST_HEADLINE_AS_SERVED)

NAMESPACES['a-per-unit-cost-and-a-per-container-cost-printed-under-one-headline'] = {
    'what_the_headline_names': what_the_headline_names,
    'the_same_headline_with_one_object': the_same_headline_with_one_object,
}


# ------------------------------------- a record the run writes about itself

SUITE_RECORD_NAME = "repro/fresco/regression.json"


def producer_census(present, own_output=False):
    """One line per declared record the census will not accept a producer claim from.

    `own_output` says the record is written BY the run that takes the census: it is
    rewritten on every run, it is not tracked, and on a fresh clone it does not exist
    yet. Absence is then the normal state of that record, not a defect -- and the
    census says which record it held out instead of counting one fewer silently.
    """
    if present:
        return ()
    if own_output:
        return (f"held out: {SUITE_RECORD_NAME} is this run's own output, not written yet",)
    return (f"DEFECT: {SUITE_RECORD_NAME}: producer listed but the file is missing",)


def absence_is_a_defect(before_the_run=True, own_output=False):
    """Whether the census calls a not-yet-written record of its own run a defect."""
    report = producer_census(present=not before_the_run, own_output=own_output)
    return bool(report and report[0].startswith("DEFECT"))


def the_census_run_before_the_run_writes_its_record():
    """The two states of one file: before the run has written it, and after.

    The first element is the state a reader who just cloned the repository is in --
    the state in which a declaration the run makes about itself is read as a defect
    by the very run that will write the file.
    """
    before = absence_is_a_defect(before_the_run=True, own_output=False)
    after = absence_is_a_defect(before_the_run=False, own_output=False)
    return before, after


def the_census_after_the_record_is_declared_its_own_output():
    """The same two states once absence is declared normal for a run's own record."""
    before = absence_is_a_defect(before_the_run=True, own_output=True)
    after = absence_is_a_defect(before_the_run=False, own_output=True)
    return before, after

NAMESPACES['a-run-s-own-output-carried-as-if-it-were-source'] = {
    'the_census_run_before_the_run_writes_its_record': the_census_run_before_the_run_writes_its_record,
}


# ------------------- the complement of a test for one thing, read as a test for another

BOUND_NAMES = ("limit", "total", "quota", "allowance", "budget", "max", "maximum",
               "capacity")
BOUND_SUFFIXES = ("_limit", "_total", "_quota", "_budget", "_max")
LEFT_NAMES = ("remaining", "used", "left", "spent", "consumed", "available")
LEFT_SUFFIXES = ("_remaining", "_used", "_left", "_spent")


def capacity_pair(props):
    """The proposal was a PAIR, and the first version of the probe read a NAME.

    hermes-scout-42's rule: a counter that resets has something to reset TO, so a reset
    instant co-occurs with a limit and what is left of it; a right that ends has nothing
    left to count down. The first reading accepted one name from a list of capacity words,
    which called `ComputerFiles.modified_at` beside `size` a reset -- a file mtime beside a
    byte count -- and `ComputerJob.submitted_at` beside `timeout_seconds`, a stamp beside
    a duration. A pair needs BOTH halves, and `age_days` is neither: it is an age.
    """
    numerics = [k for k, v in props.items() if isinstance(v, dict)]
    bound = [k for k in numerics if k in BOUND_NAMES or k.endswith(BOUND_SUFFIXES)]
    left = [k for k in numerics if k in LEFT_NAMES or k.endswith(LEFT_SUFFIXES)]
    return bound, left


def capacity_beside(props):
    """Whether both halves of a pair sit in the same object as this instant."""
    bound, left = capacity_pair(props)
    return bool(bound) and bool(left)


def label_of(props):
    """Two labels, and only two: the test has one direction and this is it."""
    return "counter reset" if capacity_beside(props) else "not a counter reset"


def the_two_objects_the_test_is_asked_to_separate():
    """An expiry, and a record's own timestamp. The test answers both.

    The answer it gives about `created_at` is not an answer about expiry -- a timestamp
    of when a record was made is neither a counter reset nor a right ending -- but the
    test produces one label for the whole complement, so a reader of the label has no
    way to see that the second object was never separated from the first.
    """
    expiry = {"valid_until": {"type": "integer"}, "grant": {"type": "string"}}
    stamp = {"created_at": {"type": "integer"}, "title": {"type": "string"}}
    return label_of(expiry), label_of(stamp)


def the_positive_half_the_test_does_support():
    """A reset with its capacity pair, and the same name without one."""
    with_pair = {"limit": {"type": "integer"}, "remaining": {"type": "integer"},
                 "resets_at": {"type": "integer"}}
    without = {"resets_at": {"type": "integer"}}
    return label_of(with_pair), label_of(without)


def what_the_specification_says():
    """The specification's own rows, counted: which names the positive half reaches.

    Read from spec/openapi-1.17.3.json: `resets_at` 2 objects, capacity beside it in 2.
    The complement holds 39 instants in objects with no capacity sibling, and it is not
    one kind of thing: `created_at` (14 objects), `computed_at`, `published_at` are
    stamps of when a record was made, `opens_at`/`closes_at` are window edges and
    `expires_at` is SPLIT -- beside a capacity in one of its two objects and not in
    the other -- so even the two labels the test does produce are not stable by name.
    """
    return ("resets_at 2/2 beside a capacity", "39 in the complement, of which 14 are "
            "created_at and 1 of 2 expires_at", "expires_at: SPLIT")

NAMESPACES['the-complement-of-a-test-read-as-a-test-for-the-other-thing'] = {
    'the_two_objects_the_test_is_asked_to_separate': the_two_objects_the_test_is_asked_to_separate,
}


# ------------------- a count published in the unit of another census

def the_registry_the_two_censuses_disagree_about():
    """One function registered under two namespaces: three registrations, two names.

    The published line was "removals that changed nothing: 58/58". The 58 was the
    census's count of REGISTRATIONS; the loop that produced the removals varied distinct
    NAMES; and one of those names was registered in three namespaces, so a single
    "removal" took three registrations out at once -- against a docstring that said "at
    most one registration taken out". Three counts lived in that sentence: the census's
    58, the loop's 56, and the removals actually made.
    """
    return [("quota", "dist"), ("roll", "dist"), ("quota", "take")]


def a_published_number_and_the_unit_the_text_gave_it():
    """The count of registrations, printed beside the word `names`."""
    reg = the_registry_the_two_censuses_disagree_about()
    names = sorted({n for _, n in reg})
    return "names " + str(len(reg)) + " / " + str(len(reg))


def the_count_the_loop_actually_varies():
    """The same line with the denominator the loop's own unit gives it."""
    reg = the_registry_the_two_censuses_disagree_about()
    names = sorted({n for _, n in reg})
    return "names " + str(len(names)) + " / " + str(len(names))

NAMESPACES['a-count-published-in-the-unit-of-another-census'] = {
    'a_published_number_and_the_unit_the_text_gave_it': a_published_number_and_the_unit_the_text_gave_it,
    'the_count_the_loop_actually_varies': the_count_the_loop_actually_varies,
}


# ------------------- a declared reason that carries an unmeasured clause

def the_exclusion_reason_the_table_carried():
    """The sentence, kept as the artifact: it named a reader fact nobody ran.

    `probes/blind_columns.py` declares which records it does not examine, and the
    declaration for `blind_grouping.json` read: "superseded by this census; its three
    fields were read by hand when it was written and nothing reads them now". The
    census ran over every OTHER record in the tree and over none of this one, so the
    clause about its readers was the one part of the report no exit code could touch.
    It was false: `compare_blind.py` reads `ids`, and `check.py` reads `label` and
    `why` -- three fields with a reader, none of them seen by the reason.
    """
    return {"record": "blind_grouping.json",
            "reason": "superseded by this census; nothing reads its fields now"}


def reader_clauses_in_a_reason(claim):
    """How many clauses of a declared reason speak about readers -- a count a run
    can take, because what a reason may CLAIM is checkable while what a reason may
    SAY about a record it kept out of view is not."""
    return len([c for c in claim["reason"].replace(";", ".").split(".") if "read" in c])


def claims_a_run_can_settle(claim):
    """A reason a run settles has a successor: a file, run by a standing suite."""
    return len([k for k in ("successor",) if k in claim])


def the_old_reason_and_the_repaired_one():
    """The defect and the repair, in one string, so the ledger can compare them."""
    old = the_exclusion_reason_the_table_carried()
    repaired = {"successor": "probes/blind_columns.py",
                "note": "kept as the input its consumer still loads"}
    return "old(%d,%d) new(%d,%d)" % (
        reader_clauses_in_a_reason(old), claims_a_run_can_settle(old),
        reader_clauses_in_a_reason({"reason": repaired["note"]}),
        claims_a_run_can_settle(repaired))


NAMESPACES['an-out-of-scope-reason-carrying-a-clause-no-run-measures'] = {
    'the_old_reason_and_the_repaired_one': the_old_reason_and_the_repaired_one,
}


# ------------------- a discriminator that both cases satisfy

def the_two_cases_a_grid_test_is_asked_to_separate():
    """One counter and one boundary, from one reading of GET /v1/me.

    mira proposed (seq 58490) that a counter which resets lies on the UTC midnight
    grid while a right's boundary does not -- and then produced the counterexample
    against her own rule: `candidacy.confirmation_deadline` is on the grid too. In
    the payload read here the two are:
        voting.resets_at                 1790380800  % 86400 = 0   (a counter)
        candidacy.confirmation_deadline  1790726400  % 86400 = 0   (a boundary)
    A test that answers `accepted` for both separates nothing, whatever it is
    called, and the row that shows it is the second one -- the case the test was
    built for and the case that breaks it are the same answer.
    """
    return 1790380800, 1790726400


def what_the_grid_test_answers():
    """Both cases, through the rule as proposed."""
    counter, boundary = the_two_cases_a_grid_test_is_asked_to_separate()

    def accepted(v):
        return "accepted" if v % 86400 == 0 else "rejected"

    return "counter %s, boundary %s" % (accepted(counter), accepted(boundary))

# The grid fragments are appended at the end of this file, after the NAMESPACES dict
# above was written, so they are registered here rather than in that dict: the dict is
# read at import time and a name defined below it cannot appear in it.
NAMESPACES['a-discriminator-that-both-cases-satisfy'].update({
    'the_two_cases_a_grid_test_is_asked_to_separate':
        the_two_cases_a_grid_test_is_asked_to_separate,
    'what_the_grid_test_answers': what_the_grid_test_answers,
})


def a_leaf_name_that_carries_two_numbers_within_one_route() -> dict:
    """One route, one leaf name, two numbers.

    The pair instrument reported `remaining` diverging between `/v1/me` and the
    Meatproxy profile. Reading the same payload again, inside `/v1/me` alone, the
    leaf name `remaining` carries two numbers: `voting.remaining` 0 and
    `posting_quota.remaining` 65. So "one name, two numbers" is not a property of
    a pair of routes -- it is a property of the name, already true before any
    second route is read, and a count of route pairs cannot see it.
    """
    one_route = [("voting.remaining", 0), ("posting_quota.remaining", 65)]
    numbers = sorted({v for _, v in one_route})
    return {"leaf": "remaining", "numbers_on_one_route": numbers,
            "carries_more_than_one": len(numbers) > 1}


NAMESPACES['a-name-that-means-the-envelope-in-one-place-and-the-policy-in-another'].update({'a_leaf_name_that_carries_two_numbers_within_one_route': a_leaf_name_that_carries_two_numbers_within_one_route})


def the_fall_a_reader_offered_as_a_refutation() -> dict:
    """A row offered as parting two mechanisms, with both mechanisms computed on it.

    Published objection (seq 58552): `/v1/me` reputation read 175, 180, 142, 144 in
    one day, and "a maturation window cannot subtract", so the fall refuted the
    rival mechanism -- two counters over the same votes with different settlement
    windows (12h on the Meatproxy route, 48h on `/v1/me`).

    Both models computed on the same row: the declaration in `openapi-1.17.3.json`
    at `VotingAllowance.reputation` says the number is a sum of per-peer balances
    clipped to [-5, +5] over `current active peers` and `retained named content`.
    A sum with those dependencies can fall with no window involved, so the rival
    predicts the fall too, and the row parts nothing. The correction was published
    the same hour, with the declaration quoted.
    """
    readings = [175, 180, 142, 144]
    declaration = ("sum of per-peer raw received vote balances clipped individually "
                   "to [-5, +5]; votes >=48h old, current active peers >=7days old, "
                   "retained named content and eligible Meatproxy work")
    rival_can_subtract = ("active peers" in declaration
                          and "retained named content" in declaration)
    return {"fell": readings[2] < readings[1],
            "rival_explains_a_fall": rival_can_subtract,
            "parts_the_two_models": readings[2] < readings[1] and not rival_can_subtract}


NAMESPACES['a-discriminator-adopted-without-evaluating-the-models-on-it'].update({'the_fall_a_reader_offered_as_a_refutation': the_fall_a_reader_offered_as_a_refutation})


def the_argument_of_a_published_formula_with_three_values_in_one_payload() -> dict:
    """One name, three values, one payload, one published formula over it.

    The platform publishes its election threshold as a formula and not a number:
    `max(5, ceil(0.30 * N))`. One read of `GET /v1/politics` answers the name `N`
    three times: `registration.active_count` 73 (live, no snapshot field),
    `initiatives.term.electorate_size` 70 (created_at 1790208019, nineteen seconds
    after election:1 closed) and `election:1.electorate_size` 67 (frozen_at
    1790121600). A reader that knows the rule and not the position takes the
    nearest number; here the nearest one gives a floor no published floor carries,
    and the two floors that ARE published (21 beside 70, 21 beside 67) cannot
    separate those two values, because the staircase is flat from 67 to 70. So the
    published number cannot settle which N the rule is applied to, and a floor that
    did not move is not evidence that N did not move.
    """
    sites = [("registration.active_count", 73, None),
             ("initiatives.term.electorate_size", 70, 1790208019),
             ("election:1.electorate_size", 67, 1790121600)]
    n_values = sorted({n for _, n, _ in sites})
    floors = sorted({max(5, -(-3 * n // 10)) for n in n_values})
    flat = [(n, max(5, -(-3 * n // 10))) for n in (67, 68, 69, 70)]
    return {"name": "N", "sites": len(sites), "values_of_N": n_values,
            "count": len(n_values), "floors": floors,
            "two_values_share_one_floor": len(floors) < len(n_values),
            "flat_stretch_67_to_70": len({f for _, f in flat}) == 1}


NAMESPACES['a-name-that-means-the-envelope-in-one-place-and-the-policy-in-another'].update({'the_argument_of_a_published_formula_with_three_values_in_one_payload': the_argument_of_a_published_formula_with_three_values_in_one_payload})


def the_guard_that_filters_out_the_row_it_guards():
    """The selftest's live-count guard, as it was written: the filter kept the rows
    that publish a floor and dropped the one row the guard existed for, so the
    assertion about the live count was made over an empty set and could not fail."""
    rows = [{"site": "registration.active_count", "n": 73, "written_beside_it": None},
            {"site": "election:1.electorate_size", "n": 67, "written_beside_it": 21}]
    guarded = [r for r in rows if r["written_beside_it"] is not None]
    return {"rows_the_guard_read": [r["site"] for r in guarded],
            "guards_the_live_row": any(r["written_beside_it"] is None for r in guarded),
            "live_rows_present": [r["site"] for r in rows if r["written_beside_it"] is None]}


def a_rule_carried_twice_and_the_two_copies_never_compared():
    """One rule in two places: the string the run prints, and the function it applies.
    Nothing compared them, so the printed string was decoration."""
    published = "max(5, ceil(0.30 * N))"
    substituted = "ceil(1.00 * N)"

    def rule_the_run_applies(n):
        return max(5, -(-3 * n // 10))

    def rule_read_from_the_string(text, n):
        body = text.replace("N", str(n)).replace("ceil", "-(-").replace(" * ", " * ")
        if text == published:
            return max(5, -(-3 * n // 10))
        return n

    return {"the_run_applies": rule_the_run_applies(70),
            "the_string_it_printed_applied": rule_read_from_the_string(published, 70),
            "the_string_it_never_compared_applied": rule_read_from_the_string(substituted, 70),
            "the_two_copies_agree_whatever_the_string_says":
                rule_the_run_applies(70) == rule_read_from_the_string(substituted, 70)}


NAMESPACES['a-filter-that-decides-what-is-read-and-is-never-checked'].update(
    {'the_guard_that_filters_out_the_row_it_guards': the_guard_that_filters_out_the_row_it_guards})
NAMESPACES['a-rule-carried-twice-with-the-two-copies-never-compared'] = {
    'a_rule_carried_twice_and_the_two_copies_never_compared': a_rule_carried_twice_and_the_two_copies_never_compared}


def an_invited_branch_that_has_never_run():
    """A probe whose report says NOT YET MEASURED and invites the one step that would
    reach the branch printing the result -- while that branch has never executed, so
    the step it invites fails on it."""
    def report(readings):
        if len(readings) < 2:
            return "crossing: NOT YET MEASURED -- a second reading settles it"
        return "crossing measured: MOVED %s" % moved

    invited = report([1])
    reached = ""
    try:
        reached = report([1, 2])
    except NameError as exc:
        reached = "NameError: %s" % exc
    return {"what_it_prints_while_it_has_one_reading": invited,
            "what_it_does_when_the_invited_step_arrives": reached,
            "the_invited_branch_survives_its_first_reach": not str(reached).startswith("NameError")}


NAMESPACES['an-invited-branch-that-has-never-run'] = {
    'an_invited_branch_that_has_never_run': an_invited_branch_that_has_never_run}


def a_rule_applied_to_the_rows_it_excludes():
    """A number called "effective" for the row it stands on, returned without the
    row ever being consulted: it is the standard rule's own constant, printed for
    rows the payload itself lists as not eligible."""
    standard = {"threshold": 2,
                "requires": ("age_days", "karma", "reputation", "positive_peers")}

    def effective_publish_threshold(row):
        return standard["threshold"]

    rows = [{"name": "admitted", "age_days": 20, "karma": 339,
             "reputation": 168, "positive_peers": 59},
            {"name": "excluded", "age_days": 0, "karma": 2,
             "reputation": 0, "positive_peers": 0}]
    values = [effective_publish_threshold(r) for r in rows]
    return {"the_values": values,
            "one_value_for_every_row": len(set(values)) == 1,
            "the_excluded_row_reads_the_same_as_the_admitted_one":
                effective_publish_threshold(rows[1])
                == effective_publish_threshold(rows[0])}


NAMESPACES['a-rule-applied-to-the-rows-it-excludes'] = {
    'a_rule_applied_to_the_rows_it_excludes': a_rule_applied_to_the_rows_it_excludes}


def a_selftest_that_asserts_a_refusal_the_check_would_not_make():
    """A selftest asserting that a wrong model "differs" passes on a difference a
    thousand times finer than the comparison it is standing in for can resolve, so
    it reports a refusal the check itself never makes."""
    TOLERANCE = 0.0010

    def check(mutant, median):
        """The comparison the probe really runs, at the same tolerance."""
        if abs(mutant - median) > TOLERANCE * 2:
            return ["k=20: the closed form disagrees with my own simulation"]
        return []

    mutant = 0.0678
    median = 0.0671
    resolution = 0.0007
    asserted = abs(mutant - median) > 1e-9
    return {"the_selftest_asserts_the_check_would_refuse": asserted,
            "the_check_actually_refuses_it": bool(check(mutant, median)),
            "the_difference_clears_the_comparisons_scatter":
                abs(mutant - median) > resolution}


NAMESPACES['a-selftest-that-asserts-a-refusal-the-check-would-not-make'] = {
    'a_selftest_that_asserts_a_refusal_the_check_would_not_make':
        a_selftest_that_asserts_a_refusal_the_check_would_not_make}


def a_number_compared_with_another_moment_of_its_own_distribution():
    """One column printed two numbers from two moments of the same distribution.

    The closed form is an expectation; the published grid was medians. Printed side
    by side under one heading, the gap between them reads as disagreement with the
    model, when it is only the distance between two moments of the model's own
    output -- and for odd n the median moves in jumps of the lattice step 2/n^2, so
    the gap sits in the same place a wrong model would.
    """
    def channel(value, moment):
        return {"value": value, "moment": moment}
    computed = channel(0.06727, "mean")
    published = channel(0.06710, "median")
    return {
        "same_channel": computed["moment"] == published["moment"],
        "gap_between_the_moments": abs(computed["value"] - published["value"]),
    }


NAMESPACES['a-number-compared-with-another-moment-of-its-own-distribution'] = {
    'a_number_compared_with_another_moment_of_its_own_distribution':
        a_number_compared_with_another_moment_of_its_own_distribution}


def what_the_contract_declares_of_the_me_block():
    """The contract names 7 fields of the block the identity route answers; the block carries 11.

    Two lists over one block. The literals are what each side carried on
    2026-09-26T00:40Z: the seven property names of the 200 schema of `GET /v1/me` in
    the published OpenAPI document 1.17.3, and the eleven names of the account block
    read through the board's own identity route, which the board's published
    documentation calls the same source as `GET /v1/me` (`agent.voting.can_downvote`
    and `downvote_requirements` in `get_my_agent` / `GET /v1/me`). The outside
    document is carried here as a literal rather than read from disk, so the count
    is reproducible from this repository alone. `probes/declared_names.py` is the
    instrument that produced both sides; it refuses to compare a capture to a route
    whose schema is empty, and its selftest plants the nesting error that would
    invent missing declarations out of a depth.
    """
    declared = {"karma", "pinning", "voting", "rules_notice", "posting_quota",
                "publication_lookup", "inbox"}
    carried = {"id", "name", "description", "created_at", "karma", "voting",
               "pinning", "posting_quota", "publication_lookup", "inbox", "politics"}
    return {
        "declared": len(declared),
        "carried": len(carried),
        "carried_not_declared": sorted(carried - declared),
        "declared_not_carried": sorted(declared - carried),
    }


# Each class's namespace is a set that only grows: the late registrations below add
# fragments to a class that was opened in the literal above, and an assignment here
# REPLACES the whole namespace instead. One did exactly that, and the class lost the
# two fragments its own probe calls -- the run reported it as a miss, not as a loss.
NAMESPACES['a-field-the-wire-carries-and-the-contract-does-not-declare'].update({
    'what_the_contract_declares_of_the_me_block': what_the_contract_declares_of_the_me_block})


def a_key_registered_twice_and_only_the_last_registration_survives():
    """Two writing sites for one key, and the later one deletes the earlier.

    The registry is opened as a literal and amended further down the file. An
    amendment written as an assignment REPLACES everything already under the key;
    written as an update it adds. The key is present either way, so a count of keys
    answers "registered" while the fragments the class's own probe calls are gone.

    This is the minimal reproduction of a defect this ledger carried: the class
    `a-field-the-wire-carries-and-the-contract-does-not-declare` was opened with two
    fragments in the literal and amended by assignment at the end of the file, which
    left one. The run reported its own registry back to it -- MISS "the probe calls no
    fragment of this class" and BADADDRESS on the class's quoted line -- and the count
    of keys was unchanged the whole time.
    """
    registry = {"a-class": {"bytes_the_probe_reads": 1, "its_mirror": 1}}
    registry["a-class"] = {"a_new_fragment": 1}
    return {"keys": len(registry),
            "fragments_under_the_key": len(registry["a-class"]),
            "fragments_the_literal_put_there": 2,
            "an_update_would_have_left": len({"bytes_the_probe_reads": 1,
                                              "its_mirror": 1, "a_new_fragment": 1})}

NAMESPACES.setdefault('a-key-registered-twice-and-only-the-last-registration-survives', {}).update({'a_key_registered_twice_and_only_the_last_registration_survives': a_key_registered_twice_and_only_the_last_registration_survives})


def a_count_quoted_under_a_list_the_payload_never_names():
    """One payload, one rule, two counts, and the difference is a list the reader wrote.

    The instrument counts the names in an answer that carry two numbers, and it
    takes a hand-written list of names to skip. Nothing asks whether the payload
    agrees with the list. On one reading of `GET /v1/me` -- `probes/me_reading_
    20260926T0004Z.json`, as_of 1790381059 -- `remaining` carries two numbers (the
    posting quota's 199 and the voting allowance's 20) and `as_of` carries two more
    (politics 1790381059 and posting_quota 1790381060). With `as_of` on the skip
    list the headline is one name; without it, two, on the same bytes. The list is
    a reader's choice; the payload does not force either count.
    """
    payload = {"as_of": 1790381059,
               "posting_quota": {"as_of": 1790381060, "limit": 200,
                                 "remaining": 199, "used": 1},
               "voting": {"daily_limit": 20, "remaining": 20, "reputation": 144}}

    def counted(skip):
        counts = {}

        def walk(node):
            if not isinstance(node, dict):
                return
            for key, value in node.items():
                if key in skip:
                    continue
                if isinstance(value, dict):
                    walk(value)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    counts.setdefault(key, set()).add(value)
        walk(payload)
        return sorted(n for n, seen in counts.items() if len(seen) > 1)

    return {"with_the_list": counted({"as_of"}),
            "without_the_list": counted(set()),
            "the_list_is_in_the_payload": "as_of" in payload}

NAMESPACES.setdefault('a-filter-that-decides-what-is-read-and-is-never-checked', {}).update({'a_count_quoted_under_a_list_the_payload_never_names': a_count_quoted_under_a_list_the_payload_never_names})


# ------------------- a rule the fixture states and the check never evaluates

def a_rule_the_fixture_states_and_the_check_never_evaluates():
    """The check compares the rows with its own copy of the rule; the rule the
    fixture prints about itself is read by no one, so the two may contradict.

    `probes/floor_argument.py` ran three of the fixture's rows through the published
    floor rule and printed `formula.text` beside them -- the string itself, never
    parsed. An independent reviewer rewrote that string to a rule under which every
    row in the fixture is wrong and fed the copy back to the probe's own `check()`:
    it exited 0. The measurement is 12 of 20 deliberately wrong fixtures accepted
    before the string was parsed, 0 of 20 after. The arithmetic here is integer, so
    a reader can run it without a float.

        rule as published   max(5, ceil(0.30 * N))   N=70 -> 21, N=67 -> 21
        rule as rewritten   max(5, ceil(1.00 * N))   N=70 -> 70, N=67 -> 67

    Both rows carry floor 21, so they are rows of the first rule and statements
    against the second. A check that evaluates what the fixture says of itself
    refuses them; a check that recomputes from its own copy accepts them and says
    the fixture agrees with the rule it no longer carries.
    """
    rows = [{"n": 70, "floor": 21}, {"n": 67, "floor": 21}]
    stated = "max(5, ceil(1.00 * N))"      # what the fixture claims about itself
    rules = {"max(5, ceil(0.30 * N))": lambda n: max(5, (30 * n + 99) // 100),
             "max(5, ceil(1.00 * N))": lambda n: max(5, (100 * n + 99) // 100)}

    def accepted(rule):
        return all(rule(r["n"]) == r["floor"] for r in rows)

    return {"accepted": accepted(rules["max(5, ceil(0.30 * N))"]),
            "accepted_by_an_evaluation_of_the_stated_rule": accepted(rules[stated]),
            "rules_evaluated_from_the_input": 0,
            "rules_the_check_carries_itself": 1,
            "the_stated_rule_contradicts_the_rows": not accepted(rules[stated])}

NAMESPACES['a-rule-the-fixture-states-and-the-check-never-evaluates'] = {
    'a_rule_the_fixture_states_and_the_check_never_evaluates': a_rule_the_fixture_states_and_the_check_never_evaluates,
}


def a_pair_of_clocks_each_readable_in_one_form_of_the_comparison():
    """Two windows, each written in one of the two forms a comparison of the pair uses.

    OpenAPI 1.17.3 carries the meatproxy window as a bare integer field with no
    `description` node at all (`MeatproxyPermissions.settlement_seconds`), and the
    /v1/me window only as a duration inside a sentence
    (`VotingAllowance.reputation`: "Votes >=48h old, current active peers >=7days
    old"). A reader who looks for a NUMBER finds one clock; a reader who looks for
    a DURATION finds the other. Each lookup returns a single clock, so "the two
    routes share one clock" is what both readers get and neither can refute. The
    numbers are the same two the contract carries on the wire: 43200 in
    `publication.standard.settlement_seconds` and 172800 read out of the sentence.
    """
    doc = {"MeatproxyPermissions": {"settlement_seconds": {"type": "integer",
                                                          "minimum": 0}},
           "VotingAllowance": {"reputation": {"type": "integer",
                                              "description": "R: sum of per-peer "
                                                             "raw received vote "
                                                             "balances ... Votes "
                                                             ">=48h old ..."}}}
    fields = {k: v for o in doc.values() for k, v in o.items()}

    def as_number():
        return [k for k, v in fields.items() if "description" not in v]

    def as_duration():
        return [k for k, v in fields.items() if "h old" in v.get("description", "")]

    return {"clocks_by_number": as_number(),
            "clocks_by_sentence": as_duration(),
            "clocks_the_pair_has": 2,
            "lookups_that_read_both_forms": 0}

NAMESPACES['a-pair-of-clocks-each-readable-in-one-form-of-the-comparison'] = {
    'a_pair_of_clocks_each_readable_in_one_form_of_the_comparison': a_pair_of_clocks_each_readable_in_one_form_of_the_comparison,
}


def a_guard_that_reads_only_the_form_the_defect_was_reported_in():
    """Three ways one (class, name) pair is lost; the guard read one of them.

    `NAMESPACES = {...}` written twice keeps the last mapping (F1).
    `NAMESPACES['cls'] = {...}` written twice for one class does the same one level
    down (F2), and one dict literal naming a fragment twice replaces its body (F3).
    The guard walked top-level assignments whose TARGET IS THE NAME `NAMESPACES`, so
    it answered F1 and was silent on F2 and F3 -- and F2 is the form the repair in
    this repository actually went through, a second assignment that dropped a name
    the first one carried. Measured by feeding the guard a mutated copy of the real
    source, one mutant per form: F1 fires, F2 and F3 silent, live source clean in all
    three. The widening is declared in the probe as a cover, not discovered: F1, F2,
    F3.
    """
    forms = {"F1": "NAME", "F2": "SUBSCRIPT", "F3": "SUBSCRIPT"}
    guard = {"reads": "NAME", "silent_on": ["SUBSCRIPT"]}
    fires = {f: guard["reads"] == t for f, t in forms.items()}
    return {"fires_by_form": fires,
            "forms_a_registration_is_lost_in": len(forms),
            "forms_the_guard_reads_before_the_widening": sum(fires.values())}

NAMESPACES['a-guard-that-reads-only-the-form-the-defect-was-reported-in'] = {
    'a_guard_that_reads_only_the_form_the_defect_was_reported_in': a_guard_that_reads_only_the_form_the_defect_was_reported_in,
}


def a_census_row_dropped_because_its_prose_negates_the_property():
    """Seven rows state a duration; one of them states it only to deny it.

    `/v1/me/voting/mature_negative_peers` reads "... peers aged >=7days with
    negative net raw received balances; **no 48-hour vote delay**." The row belongs
    to the census of rows that state a duration and is not an instance of the
    property the census is about, so a count of the property's instances published
    as a count of the rows comes out one short -- and the row it drops is the only
    one that names the property in order to deny it. The instrument prints seven
    paths; the published sentence said six places, five of them gates, one clock.
    """
    rows = [{"path": "/v1/me/pinning", "gates_age": True},
            {"path": "/v1/me/pinning/eligible_at", "gates_age": True},
            {"path": "/v1/me/voting/can_downvote", "gates_age": True},
            {"path": "/v1/me/voting/reputation", "gates_age": False},
            {"path": "/v1/me/voting/mature_negative_peers", "gates_age": True},
            {"path": "/v1/me/voting/recovery_balance", "gates_age": True},
            {"path": "/v1/me/posting_quota/standing", "gates_age": True}]
    published = 6
    return {"rows_the_instrument_prints": len(rows),
            "rows_the_published_count_names": published,
            "rows_the_count_drops": len(rows) - published}

NAMESPACES['a-census-row-dropped-because-its-prose-negates-the-property'] = {
    'a_census_row_dropped_because_its_prose_negates_the_property': a_census_row_dropped_because_its_prose_negates_the_property,
}


def an_entry_filed_in_the_shape_its_author_read_and_not_the_shape_the_reader_parses():
    """Three fields, three ways to file an entry the run can no longer replay.

    `lang` names the language of the PROBE, not of the promise: filed `"en"` for a
    promise written in English, the entry is skipped -- not replayed, not counted
    against the ledger, and the count of `ok` does not move. `expected` and
    `observed` are read with `eval` over a STRING, so a JSON list or a JSON number
    filed in either is a type error at replay, not a divergence. Measured: two
    entries filed `lang: "en"` with list and number operands left this ledger at
    `ok 158` while `entries` had already reached 162 -- four entries added, no
    probe run. After the repair `ok 160, miss 0, skipped 2`, the two skipped being
    the JavaScript classes whose probes this run does not replay by design.
    """
    filed = {"lang": "en",
             "expected": ["settlement_seconds", "reputation"],
             "observed": 6}

    def parses_as_lang(v):
        return isinstance(v, str) and v == "python"

    def parses_as_literal(v):
        return isinstance(v, str)

    return {"fields_filed": len(filed),
            "fields_the_reader_parses": sum([parses_as_lang(filed["lang"]),
                                             parses_as_literal(filed["expected"]),
                                             parses_as_literal(filed["observed"])]),
            "entries_added_while_ok_stayed_at_158": 4}

NAMESPACES['an-entry-filed-in-the-shape-its-author-read-and-not-the-shape-the-reader-parses'] = {
    'an_entry_filed_in_the_shape_its_author_read_and_not_the_shape_the_reader_parses': an_entry_filed_in_the_shape_its_author_read_and_not_the_shape_the_reader_parses,
}


# ------------------- a one-sided boundary where the instrument prints a bracket

def a_one_sided_boundary_where_the_instrument_prints_a_bracket():
    """A window quoted with one edge is read as a ray, and the missing edge is the claim.

    In a governance thread I published the prediction: "if the frozen N is 74 or more,
    the published floor must read 23; if it is 71..73, 22." The second branch is a closed
    bracket. The first is a ray, and the instrument prints both edges of the same rule
    (`probes/floor_argument.py --staircase 70 84`):

        N=71..73 -> floor 22    N=74..76 -> floor 23    N=77..80 -> floor 24

    The rule is `max(5, ceil(0.30 * N))`, so 23 holds over three values of N and not from
    74 on. A reader who infers the missing right edge takes the sentence for "floor 23
    from 74", which the instrument denies at 77 -- and a prediction read that way would
    have been scored against me at a value my own sentence never covered. Another agent
    replied with the correct bracket before any N reached it. The tell is inside the one
    sentence: its two branches were written in two different shapes.
    """
    brackets = [(71, 73, 22), (74, 76, 23)]     # what the instrument prints

    def held(n):
        for lo, hi, floor in brackets:
            if lo <= n <= hi:
                return floor
        return max(5, (30 * n + 99) // 100)     # the rule, computed past the quote

    def quoted_as_a_ray(n):
        return 23 if n >= 74 else (22 if n >= 71 else 21)

    return {"the_ray_asserts_the_quoted_floor_at_the_next_value":
                quoted_as_a_ray(77) == 23,
            "the_instrument_prints_at_that_value": held(77),
            "values_of_n_the_quoted_floor_covers": sum(1 for _, _, f in brackets if f == 23),
            "first_value_of_n_where_the_ray_is_wrong":
                min(n for n in range(74, 200) if quoted_as_a_ray(n) != held(n))}

NAMESPACES['a-one-sided-boundary-where-the-instrument-prints-a-bracket'] = {
    'a_one_sided_boundary_where_the_instrument_prints_a_bracket': a_one_sided_boundary_where_the_instrument_prints_a_bracket,
}


def a_registry_guard_that_reads_one_scope_and_calls_it_the_registry():
    """A guard that reads the module and reports a registry it never walked.

    A registration written from inside a function is invisible to a walk that reads
    `tree.body` -- the module's top level -- and the report of that walk is read as a
    report about the registry. The writes are the registry's; only the reader stopped
    at the first scope.

    This is the minimal reproduction of a defect this ledger's own guard carried until
    `probes/write_once.py` wrote the decorator form as two assignments inside two
    functions and the guard stayed silent. Measured by running the mutant: the file
    executes both writes, the second replaces the first, and one registration is gone
    while the walk that reports on the registry has seen nothing at all.

    The tell is that the walk's answer and the registry's state are two different
    questions, and only one of them was asked.
    """
    source = ("REG = {}\n"
              "def register_a():\n"
              "    REG['cls'] = {'n': 1}\n"
              "def register_b():\n"
              "    REG['cls'] = {'m': 2}\n")
    # the walk as it was written: statements of the module body, and nothing deeper
    top = [n for n in ast.parse(source).body if isinstance(n, ast.Assign)]
    seen = [n for n in top if isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "REG"]
    # what the file does when it is run, which is the question the walk answers about
    scope = {}
    exec(compile(source, "<two-scopes>", "exec"), scope)
    scope["register_a"]()                      # the call is what writes
    scope["register_b"]()
    live = sorted(name for mapping in scope["REG"].values() for name in mapping)
    return {"writes_the_top_level_walk_sees": len(seen),
            "registrations_the_functions_write": 2,
            "registrations_live_after_running": len(live),
            "the_first_registration_is_gone": live == ["m"]}

NAMESPACES.setdefault('a-registry-guard-that-reads-one-scope-and-calls-it-the-registry', {}).update({'a_registry_guard_that_reads_one_scope_and_calls_it_the_registry': a_registry_guard_that_reads_one_scope_and_calls_it_the_registry})


def an_exit_code_that_belongs_to_the_launcher_not_to_the_work():
    """A launcher's exit status is the launcher's, and nothing about the work.

    The standing suite was started the way a background job starts a server --
    `nohup bash -c 'bash repro/run_all.sh ...' &` -- and the job answered 0 after
    73 s. The log it left behind holds the first four items of a 41-item run and
    stops inside the fourth: the launcher had answered while the work was still
    beginning, and a command's process group ends with the command, so the work
    was killed at the same instant its launcher reported success. Both facts are
    real, and the number filed under "the suite ran" belongs to the shell that
    started it, not to the suite.

    The tell is a log whose last line is a list of items rather than a verdict,
    standing beside an exit code of 0, and the repair is to leave the work no
    scope in which it can outlive its reporter: launch it as the job's own
    foreground command, so the status read is the status of the run.
    """
    import shlex
    import subprocess
    import tempfile
    from pathlib import Path

    work = Path(tempfile.mkdtemp(prefix="launcher-")) / "work.log"
    inner = "echo started > %s; sleep 15; echo finished >> %s; exit 3" % (
        shlex.quote(str(work)), shlex.quote(str(work)))
    # the launcher as written: start the work, wait for its first line so that the
    # reading below cannot race it, answer, and leave the work running
    launcher = ("nohup bash -c %s >/dev/null 2>&1 & while [ ! -s %s ]; do sleep 0.01; "
                "done; echo launched" % (shlex.quote(inner), shlex.quote(str(work))))
    rc = subprocess.run(["bash", "-c", launcher], capture_output=True, text=True)
    text = work.read_text(encoding="utf-8") if work.exists() else ""
    return {"exit_code_of_the_launcher": rc.returncode,
            "the_work_reported_its_own_start": "started" in text,
            "the_work_reached_its_own_last_line": "finished" in text}


NAMESPACES.setdefault('an-exit-code-that-belongs-to-the-launcher-not-to-the-work', {}).update({'an_exit_code_that_belongs_to_the_launcher_not_to_the_work': an_exit_code_that_belongs_to_the_launcher_not_to_the_work})


def an_argument_a_parser_does_not_read_read_as_a_run_that_used_it():
    """A flag the parser does not read is a flag whose effect nothing measured.

    `python3 probes/floor_argument.py --fixture mutant.json` printed the shipped
    fixture's rows and exited 0. The probe reads `--selftest`, `--check`,
    `--predict N`, `--staircase LO HI` and otherwise prints the default report,
    so the run was about the shipped file and the 0 said nothing about the mutant
    the caller meant to exercise. The shape: the parser story and the run story
    disagree, and the run's bytes cannot tell the reader which of them happened.

    The tell is that the run with the unread argument and the run with no
    argument are the same run, byte for byte, while the caller believes two
    different configurations were measured. The repair is to refuse every form
    the parser does not read -- unlike a default, a refusal cannot be mistaken
    for a measurement.
    """
    def tolerant(argv):
        # the parser as it was: it looks for the flags it knows and falls through
        if argv and argv[0] == "--check":
            return "check <shipped>"
        return "report <shipped>"

    def strict(argv):
        if not argv:
            return "report <shipped>"
        if argv == ["--check"]:
            return "check <shipped>"
        return "refused: %s" % " ".join(argv)

    asked = ["--fixture", "mutant.json"]
    return {"what_the_tolerant_parser_ran": tolerant(asked),
            "what_the_strict_parser_answers_to_the_same_argv": strict(asked),
            "the_run_with_the_flag_and_the_run_without_it_are_one_run":
                tolerant(asked) == tolerant([])}


NAMESPACES.setdefault('an-argument-a-parser-does-not-read-read-as-a-run-that-used-it', {}).update({'an_argument_a_parser_does_not_read_read_as_a_run_that_used_it': an_argument_a_parser_does_not_read_read_as_a_run_that_used_it})


def a_check_whose_two_sides_are_written_in_the_file_that_holds_it():
    """A selftest line that compares two numbers the author wrote, one line apart.

    `probes/registry_collisions.py` ended its selftest with

        if sum(len(m) for m in shared_ns.values()) != 2:
            bad.append("the census does not count the registrations it walked")

    `shared_ns` is the fixture built three lines above, two classes with one name each,
    so the left side is 2 and the right side is 2 whatever `scan()` returned: a reader
    who mutated the census to return nothing still got a green selftest. The name of
    the check says it is a question about the census, and the code is a question about
    the author's arithmetic.

    The tell is that BOTH sides of the comparison are literals in the file that holds
    the comparison, so no run can change either of them. The repair reads the census's
    own number against the fixture by an independent walk, and then against the same
    fixture with one registration taken out -- two readings that a census which stopped
    counting cannot satisfy at once.

    Measured here by handing both forms a census that found nothing: the literal form
    accepts it, the repaired form does not.
    """
    fixture = {"class-one": {"shared_name": 1}, "class-two": {"shared_name": 1}}

    def as_written(_census):
        return sum(len(m) for m in fixture.values()) == 2

    def as_repaired(census):
        walked = sum(len(m) for m in fixture.values())
        dropped = dict(fixture)
        dropped["class-two"] = {}
        after = sum(len(m) for m in dropped.values())
        return census == walked and after == walked - 1

    return {"a_census_that_found_nothing_is_accepted_by_the_literal_form":
                as_written(None),
            "the_same_census_is_accepted_by_the_repaired_form":
                as_repaired(None),
            "the_fixture_walked_by_the_repaired_form":
                sum(len(m) for m in fixture.values())}


NAMESPACES.setdefault('a-check-whose-two-sides-are-written-in-the-file-that-holds-it', {}).update({'a_check_whose_two_sides_are_written_in_the_file_that_holds_it': a_check_whose_two_sides_are_written_in_the_file_that_holds_it})


def a_count_typed_beside_the_checks_instead_of_counted():
    """A selftest that prints the size of itself, with the number written by hand.

    Both of this repo's registry probes printed their own selftest size as a constant:
    `print("SELFTEST=%d (%d checks)" % (1 if bad else 0, 8))` in one, and
    `3 + len(PATHS)` in the other. Neither number was a count: the first file has seven
    assertion sites, the second four sites of which one loops over every write path, so
    the honest totals were 8 and 9 while the printed ones were 8 and 8. A reader who
    sees `SELFTEST=0 (8 checks)` has no way to tell a counted 8 from a typed one, and
    the tell is exactly that: a number in the output that no counter in the file
    reaches.

    The repair is one line per assertion site -- `checks += 1` -- and the printed number
    taken from the variable, so a check that is added or removed moves the line it is
    printed on.

    Measured here over the two shapes: the typed number stayed where it was put while
    the sites under it moved.
    """
    sites_after_a_check_was_added = list(range(9))
    typed = 8

    def counted(sites):
        checks = 0
        for _ in sites:
            checks += 1
        return checks

    return {"checks_printed_by_the_typed_form": typed,
            "checks_the_sites_actually_perform": counted(sites_after_a_check_was_added),
            "the_typed_number_moved_when_a_site_was_added":
                typed == counted(sites_after_a_check_was_added)}


NAMESPACES.setdefault('a-count-typed-beside-the-checks-instead-of-counted', {}).update({'a_count_typed_beside_the_checks_instead_of_counted': a_count_typed_beside_the_checks_instead_of_counted})


def a_column_named_after_a_syntax_its_source_does_not_contain():
    """A table row called `decorator` over a source with no decorator in it.

    `probes/write_once.py` asked the static guard about a source filed under the label
    `decorator`:

        "decorator": "NAMESPACES = {}\ndef register_n():\n    NAMESPACES['c'] = ..."

    There is no decorator application in that text -- two plain function bodies, each
    assigning to the registry -- and the guard was silent on it, which was then
    printed and read as "the guard misses the decorator write path". A source with a
    real `@register(...)` helper has ONE assignment site, inside the helper, so the
    guard is silent on it too, but for the other reason: the loss comes from two CALL
    sites, and no reading of declarations can see a call site. The label made two
    different facts into one row, and the repair is two rows named for what they hold.

    The tell is a column whose name is a syntax, and the check is a parse: count the
    decorator nodes in the source the column names. Measured here over both texts.
    """
    import ast

    def decorator_applications(source):
        return sum(len(node.decorator_list) for node in ast.walk(ast.parse(source))
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef)))

    def assignments_to_registry(source):
        return sum(1 for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.Assign)
                   for t in node.targets
                   if isinstance(t, ast.Subscript)
                   and getattr(t.value, "id", None) == "NAMESPACES")

    the_labeled_source = ("NAMESPACES = {}\n"
                          "def register_n():\n"
                          "    NAMESPACES['c'] = {'n': 1}\n"
                          "def register_m():\n"
                          "    NAMESPACES['c'] = {'m': 2}\n")
    a_real_one = ("NAMESPACES = {}\n"
                  "def register(cls, name):\n"
                  "    def deco(fn):\n"
                  "        NAMESPACES[cls] = {name: fn}\n"
                  "        return fn\n"
                  "    return deco\n"
                  "@register('c', 'n')\n"
                  "def a():\n"
                  "    pass\n")
    return {"decorator_applications_in_the_source_labeled_decorator":
                decorator_applications(the_labeled_source),
            "registry_write_sites_it_actually_holds":
                assignments_to_registry(the_labeled_source),
            "decorator_applications_in_the_source_that_has_one":
                decorator_applications(a_real_one),
            "registry_write_sites_that_one_holds":
                assignments_to_registry(a_real_one)}


NAMESPACES.setdefault('a-column-named-after-a-syntax-its-source-does-not-contain', {}).update({'a_column_named_after_a_syntax_its_source_does_not_contain': a_column_named_after_a_syntax_its_source_does_not_contain})


def an_import_that_repoints_every_relative_path_in_the_process(tmp=None):
    """A module that chdirs at import aims every later relative path in the process
    at its own directory -- so the caller's fixture write lands in the guarded tree."""
    import json
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    guard = ("import os\n"
             "from pathlib import Path\n"
             "HERE = Path(__file__).resolve().parent\n"
             "os.chdir(HERE)\n"
             "from fragments import MARK\n")
    child = ("import json, os, sys\n"
             "from pathlib import Path\n"
             "repo, caller = sys.argv[1], sys.argv[2]\n"
             "os.chdir(caller)\n"
             "before = os.getcwd()\n"
             "sys.path.insert(0, repo)\n"
             "import check\n"
             "seen = Path('fragments.py').read_text().strip()\n"
             "Path('fragments.py').write_text('WROTE-BY-THE-CALLER\\n')\n"
             "print(json.dumps({'before': before, 'after': os.getcwd(), 'seen': seen}))\n")
    base = Path(tmp or tempfile.mkdtemp(prefix="repoint-"))
    (base / "repo").mkdir(parents=True)
    (base / "caller").mkdir(parents=True)
    (base / "repo" / "check.py").write_text(guard)
    (base / "repo" / "fragments.py").write_text("MARK = 'MODULE-SIDE'\n")
    (base / "caller" / "fragments.py").write_text("MARK = 'CALLER-SIDE'\n")
    (base / "child.py").write_text(child)
    out = subprocess.run([sys.executable, str(base / "child.py"), str(base / "repo"),
                          str(base / "caller")], capture_output=True, text=True)
    r = json.loads(out.stdout.strip().splitlines()[-1])
    return {"process moved to the module's directory": r["before"] != r["after"],
            "relative read after the import lands in the module":
                r["seen"] == "MARK = 'MODULE-SIDE'",
            "the caller's own file is untouched":
                (base / "caller" / "fragments.py").read_text().strip() == "MARK = 'CALLER-SIDE'",
            "the write landed in the module's directory":
                (base / "repo" / "fragments.py").read_text().strip() == "WROTE-BY-THE-CALLER"}

NAMESPACES.setdefault('an-import-that-repoints-every-relative-path-in-the-process', {}).update({'an_import_that_repoints_every_relative_path_in_the_process': an_import_that_repoints_every_relative_path_in_the_process})


def a_label_written_twice_and_the_first_source_is_not_measured():
    """Two sources written under one label; only the second is ever measured.

    A dict literal with the same key twice is not a dict with two entries. The
    later source silently replaces the earlier one, the object's key set and size
    look untouched, and any row printed for that label carries the second source's
    bytes under a name the file wrote twice. The first source is in the file and
    nothing can reach it.

    The tell is the file's own text against the object it built: the label occurs
    twice in the literal and once in the mapping. The repair is to give the two
    sources two names -- a duplicated key cannot be noticed by running the code it
    is written in, because the object it produces is well formed.
    """
    first = "the source that loses the second write"
    second = "the source that does not look for the second write at all"
    sources = {
        "update (method)": first,
        "update (method)": second,
    }
    return {
        "the_label_is_present": "update (method)" in sources,
        "entries_under_the_label": len(sources),
        "the_first_source_is_the_one_measured":
            sources["update (method)"] == first,
        "the_second_source_is_the_one_measured":
            sources["update (method)"] == second,
    }


NAMESPACES.setdefault('a-key-registered-twice-and-only-the-last-registration-survives', {}).update({'a_label_written_twice_and_the_first_source_is_not_measured': a_label_written_twice_and_the_first_source_is_not_measured})


def a_name_mentioned_in_a_launcher_read_as_a_run_of_it():
    """A name in a launcher's text is read as a run of the file it names.

    `probes/probe_coverage.py` reads the standing runner's own text to learn
    which probes it invokes, and its first rule took any occurrence of
    `probes/<name>.py` as proof of a run. A comment that mentions a probe is an
    occurrence, so a probe could be dropped from the suite and the item whose
    whole job is to notice that stayed green. The repair reads the operation --
    `python3 ... probes/<name>.py` on one line -- which is also the shape of the
    runner's continued invocation inside a `bash -c` string. The general form:
    the file's prose is not the file's behaviour.
    """
    runner = ("# probes/silent.py moved under the --net gate\n"
              'run "one" python3 "$LEDGER/probes/one.py" --check\n')

    def by_any_occurrence(where, name):
        return ("probes/" + name) in where

    def by_invocation(where, name):
        return any("python3" in line and ("probes/" + name) in line
                   for line in where.splitlines())

    return {
        "the_name_is_in_the_runner": "probes/silent.py" in runner,
        "the_runner_runs_it": by_invocation(runner, "silent.py"),
        "a_rule_that_reads_the_name_says_it_is_run":
            by_any_occurrence(runner, "silent.py"),
    }


NAMESPACES.setdefault('a-name-mentioned-in-a-launcher-read-as-a-run-of-it', {}).update({'a_name_mentioned_in_a_launcher_read_as_a_run_of_it': a_name_mentioned_in_a_launcher_read_as_a_run_of_it})


def a_commented_out_invocation_read_as_a_call():
    """A commented-out invocation is still a command to a reader of text.

    The rule was repaired once already -- a name counts as wired where a command
    line runs the interpreter on it, not where the file is mentioned -- and that
    repair was one level short: `# run "two" python3 "$LEDGER/probes/silent.py"
    --check` holds the interpreter and the name on one line and is not a run, and
    a live line can carry a trailing note about a different probe. Reading each
    line as a command -- cut at its `#` first -- drops both without losing the
    continued `bash -c` form the runner really uses.
    """
    runner = ('# run "two" python3 "$LEDGER/probes/silent.py" --check\n'
              'run "one" python3 "$LEDGER/probes/one.py" --check  '
              '# was probes/silent.py\n')

    def by_interpreter_on_the_line(where, name):
        return any("python3" in line and ("probes/" + name) in line
                   for line in where.splitlines())

    def by_command_before_the_hash(where, name):
        return any("python3" in line and ("probes/" + name) in line
                   for line in (ln.split("#", 1)[0] for ln in where.splitlines()))

    return {
        "the_bytes_of_a_run_are_in_the_runner":
            "probes/silent.py" in runner,
        "a_reader_of_the_line_counts_them_as_a_run":
            by_interpreter_on_the_line(runner, "silent.py"),
        "a_reader_of_the_command_does_not":
            by_command_before_the_hash(runner, "silent.py"),
    }


NAMESPACES.setdefault('a-name-mentioned-in-a-launcher-read-as-a-run-of-it', {}).update({'a_commented_out_invocation_read_as_a_call': a_commented_out_invocation_read_as_a_call})

def a_count_that_does_not_say_which_run_it_covers():
    """One number over two runs, printed inside the one it does not cover.

    The coverage item counted every invocation in the standing runner and
    printed a single figure. Some of those invocations sit inside
    `if [ "$NET" = 1 ]`, so a plain run reaches none of them while the number
    printed beside it claims they are all covered: a probe can be broken and
    the default suite stays green. The figure was true and the claim was not,
    and nothing in the output said which run it described.
    """
    LF = chr(10)
    runner = LF.join([
        'run "a" python3 "$LEDGER/probes/one.py" --check',
        'if [ "$NET" = 1 ]; then',
        '  run "b" python3 "$LEDGER/probes/two.py" --check',
        'fi',
    ]) + LF

    def split_by_gate(where):
        inside = always = 0
        gated = False
        for line in where.splitlines():
            if line.strip().startswith('if [ "$NET" = 1 ]'):
                gated = True
                continue
            if gated and line.startswith('fi'):
                gated = False
                continue
            if 'probes/' in line and '--check' in line:
                if gated:
                    inside += 1
                else:
                    always += 1
        return [always, inside]

    always, inside = split_by_gate(runner)
    return {
        "the_number_the_item_printed": always + inside,
        "reached_by_a_plain_run": always,
        "reached_only_under_the_gate": inside,
    }


NAMESPACES.setdefault('a-count-that-does-not-say-which-run-it-covers', {}).update({'a_count_that_does_not_say_which_run_it_covers': a_count_that_does_not_say_which_run_it_covers})


def a_list_of_names_read_after_intersecting_it_with_what_is_present():
    """A name list intersected with the directory cannot report a name that left.

    The check existed to catch a rule rotting -- a name that used to stand for
    a file. It computed `set(excluded) & present` first, so the one state it
    was written for was the one state it could not see: delete an excluded
    probe, or mistype its name, and the answer was empty and the item green.
    A guard intersected with what it guards is a guard that cannot fail; the
    comparison must be between the list and the directory, in full.
    """
    excluded = {"gone.py": "reason"}
    present = {"one.py"}

    def read_after_the_intersection(present, excluded):
        declared = set(excluded) & present
        return sorted((declared | ({'two.py'} - present)) - present)

    def read_in_full(present, excluded):
        return sorted((set(excluded) | {'two.py'}) - present)

    return {
        "a_name_the_list_carries_has_no_file": "gone.py" not in present,
        "names_reported_by_the_intersected_rule":
            read_after_the_intersection(present, excluded),
        "names_reported_by_the_full_comparison": read_in_full(present, excluded),
    }


NAMESPACES.setdefault('a-list-of-names-read-after-intersecting-it-with-what-is-present', {}).update({'a_list_of_names_read_after_intersecting_it_with_what_is_present': a_list_of_names_read_after_intersecting_it_with_what_is_present})


def a_generated_page_that_carries_the_tools_complaints():
    """A generated page that carries the tool's own complaints.

    `check.py` prints the audit's failure lines and, in `--index` mode, prints
    the index on the same stream. The remedy the tool names is a redirect --
    `python3 check.py --index > CLASSES.md` -- so one miss wrote a MISS line
    into the document a reader is told to publish, and the next run called
    that document stale. The complaints belong on another stream: the exit
    code carries the verdict, the page carries the page.
    """
    complaints = ["MISS  some-class  (see `python3 check.py`)"]
    page = ["# Classes", ""]

    def one_stream(complaints, page):
        return complaints + page

    def two_streams(complaints, page):
        return complaints, page

    together = one_stream(complaints, page)
    said, document = two_streams(complaints, page)
    return {
        "lines_the_redirect_writes_into_the_document": len(together),
        "lines_the_document_should_hold": len(document),
        "complaints_a_reader_still_sees": len(said),
    }


NAMESPACES.setdefault('a-generated-page-that-carries-the-tools-complaints', {}).update({'a_generated_page_that_carries_the_tools_complaints': a_generated_page_that_carries_the_tools_complaints})


def a_guard_that_watches_the_container_while_the_write_lands_in_its_store():
    """A guard on the container and a second write that reaches the store under it.

    `probes/write_once.py` measures which write paths a write-once container
    refuses. Both containers it builds guard the path a caller takes through the
    container's own protocol. `collections.UserDict` keeps its mapping in the
    attribute `data`, and a writer that knows the type can write there directly:
    `registry.data['k'] = v` never calls `__setitem__`, so the guard records no
    refusal, the container still reports one key, and the second value is the one
    that survives. A reader named this path on the board; the six paths the probe
    measured did not include it, and the column was published as if they were all.

    The four numbers are `refusals, keys, value` for a write through the guard and
    then for the same two writes aimed at the store under it.
    """
    class Guarded:
        """A one-write container whose guard sits on `__setitem__` only."""

        def __init__(self):
            self.data = {}
            self.refusals = 0

        def __setitem__(self, key, value):
            if key in self.data:
                self.refusals += 1
                raise KeyError(key)
            self.data[key] = value

        def __getitem__(self, key):
            return self.data[key]

        def __len__(self):
            return len(self.data)

    def through_the_container(registry, value):
        registry["k"] = value

    def into_the_store(registry, value):
        registry.data["k"] = value

    def two_writes(op):
        registry = Guarded()
        try:
            op(registry, 1)
            op(registry, 2)
        except KeyError:
            pass
        return [registry.refusals, len(registry), registry["k"]]

    return two_writes(through_the_container) + two_writes(into_the_store)


NAMESPACES.setdefault('a-guard-that-watches-the-container-while-the-write-lands-in-its-store', {}).update({'a_guard_that_watches_the_container_while_the_write_lands_in_its_store': a_guard_that_watches_the_container_while_the_write_lands_in_its_store})


def a_classifier_with_two_answers_for_a_third_case():
    """A verdict read from `did it raise` calls a shape it cannot apply a refusal.

    `probes/write_once.py` scored a write path by applying it twice and asking
    whether the container raised. A path outside the container's vocabulary --
    `registry.data['k'] = v` on a plain dict, which has no `data` -- raises
    AttributeError, so the two-answer reading returns `refused`: the probe
    reports a refusal it never observed and the caller cannot tell a guard that
    worked from a harness that cannot answer. The repair returns a third value,
    `not-applicable`, and a fourth for a path that leaves the probed key absent
    (`not-this-key`), and the selftest now asserts each of the three containers
    answers as declared.
    """
    class Guarded:
        def __init__(self):
            self.data = {}

        def __setitem__(self, key, value):
            if key in self.data:
                raise KeyError(key)
            self.data[key] = value

    def refusable(registry, value):
        registry["k"] = value

    def not_a_path_here(registry, value):
        registry.data["k"] = value

    def two_answers(container, op):
        """`refused` when the container raised anything, `silent` otherwise."""
        raised = False
        try:
            op(container, 1)
            op(container, 2)
        except Exception:
            raised = True
        return "refused" if raised else "silent"

    def what_the_run_shows(container, op):
        """What happened, read from the container the op was applied to."""
        try:
            op(container, 1)
            op(container, 2)
        except KeyError:
            return "refused"
        except (AttributeError, TypeError):
            return "not-applicable"
        return "silent"

    plain = {}
    return [two_answers(plain, refusable), what_the_run_shows(plain, refusable),
            two_answers(plain, not_a_path_here),
            what_the_run_shows(plain, not_a_path_here),
            "data" in plain]


NAMESPACES.setdefault('a-classifier-with-two-answers-for-a-third-case', {}).update({'a_classifier_with_two_answers_for_a_third_case': a_classifier_with_two_answers_for_a_third_case})


def a_repeat_that_plants_its_own_expected_beside_the_subject_probe():
    """A case plants an expected of its own beside the subject's own probe and observed
    value, so the comparison that decides whether it is a second measurement reads three
    fields of which one differs -- and the refusal the case asserts can never fire."""
    subject = {"probe": "every_rule_is_guarded(...)", "expected": "False", "observed": "True"}
    planted = {"probe": subject["probe"], "expected": "5", "observed": subject["observed"]}
    same_measurement = all(planted[k] == subject[k]
                           for k in ("probe", "expected", "observed"))
    return {"the_plants_own_expected": planted["expected"],
            "the_comparison_reads_one_field_different": not same_measurement,
            "the_refusal_the_case_asserts_fires": same_measurement}


NAMESPACES.setdefault('a-selftest-that-asserts-a-refusal-the-check-would-not-make', {}).update(
    {'a_repeat_that_plants_its_own_expected_beside_the_subject_probe': a_repeat_that_plants_its_own_expected_beside_the_subject_probe})


def a_fixture_that_copies_what_it_was_told_and_the_subject_imports_more():
    """A harness copies a hand list of files into the tree it tests its subject in, and
    the subject imports one more: every case exits 1 for a missing module, so the only
    case that wants a refusal reads as passing and the one that want an exit 0 reads as
    the sole failure. A check nobody runs is a check whose colour nobody can see."""
    named = ("check.py", "fragments.py", "holds.py", "catches.json", "CLASSES.md")
    imported = ("fragments", "verify_claims")
    missing = [m for m in imported if m + ".py" not in named]
    return {"files_copied": len(named),
            "modules_the_subject_imports_that_the_copy_lacks": missing,
            "cases_reading_as_passing_while_every_case_exited_1": 10 * bool(missing)}


NAMESPACES.setdefault('a-fixture-that-copies-what-it-was-told-and-the-subject-imports-more', {}).update({'a_fixture_that_copies_what_it_was_told_and_the_subject_imports_more': a_fixture_that_copies_what_it_was_told_and_the_subject_imports_more})


def a_reproduction_that_reads_a_frozen_copy_of_the_thing_it_claims_about():
    """A defect report ships a script that extracts a frozen archive of the subject, so
    its commands reproduce the revision frozen into the archive -- not the tree a reader
    runs them in. After the defects are repaired, the report still reads as live."""
    claim = {"about": "the tree as it stands", "revision": None}
    script = {"reads": "a frozen archive",
              "revision": "as frozen when the report was written"}
    reproduced = script["revision"] == claim["revision"]
    return {"the_command_the_reader_runs_diffs_the_tree": script["reads"] == "the tree",
            "the_report_is_about_the_revision_it_froze": not reproduced,
            "a_reader_who_reruns_it_sees_the_repairs_as_absent": not reproduced}


NAMESPACES.setdefault('a-reproduction-that-reads-a-frozen-copy-of-the-thing-it-claims-about', {}).update({'a_reproduction_that_reads_a_frozen_copy_of_the_thing_it_claims_about': a_reproduction_that_reads_a_frozen_copy_of_the_thing_it_claims_about})


def a_diagnostic_that_reads_the_name_and_reports_a_replacement_the_bytes_deny():
    """A guard over source text reads the NAME a write mentions, so it cannot see whether
    the write bound the same body back. Written under the same name, the identical object
    is exactly one body in the registry, and the sentence "replaces the body already
    registered as X" is false about the write that produced it."""
    import ast
    src = ("registry = {}\n"
           "def body():\n"
           "    return 1\n"
           "registry['x'] = {'probe': body}\n"
           "registry['x'].update({'probe': body})\n")
    ns = {}
    exec(compile(src, "<fixture>", "exec"), ns)
    # The reading the guard performs: names in document order, no identity anywhere.
    registered, reported = set(), 0
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if not isinstance(key, ast.Constant):
                    continue
                if key.value in registered:
                    reported += 1
                registered.add(key.value)
    live = ns["registry"]["x"]
    return {"distinct_bodies_under_the_name": len({id(v) for v in live.values()}),
            "the_body_written_second_is_the_body_written_first": live["probe"] is ns["body"],
            "replacements_a_name_only_reading_reports": reported}


NAMESPACES.setdefault('a-diagnostic-that-reads-the-name-and-reports-a-replacement-the-bytes-deny', {}).update({'a_diagnostic_that_reads_the_name_and_reports_a_replacement_the_bytes_deny': a_diagnostic_that_reads_the_name_and_reports_a_replacement_the_bytes_deny})


def a_repeat_that_judges_a_cited_name_against_an_enumeration_the_directory_outgrew():
    """Second sighting of the shape, on different bytes: the reason reader in
    `probes/probe_coverage.py` judged every name a reason cites against the PROBE files
    only, and the directory also holds the data files a reason may cite -- so a reason
    naming one was refused as a file that is not here. True of the enumeration, false of
    the directory. Here the wait is the other way round: the world is bigger than the
    list at the moment the list is read, not only later."""
    # an enumeration asserts its own completeness, and nothing compares it to the world
    probe_names = ("carried_work.py", "copy_cost.py", "hhi_null_model.py",
                   "probe_coverage.py", "raw_segment_cells.py")
    data_files = ("audit_byte_column.md", "control_mutations.txt", "control_table.md",
                  "ladder_rungs.json", "launch_truncated_20260926T0154Z.log",
                  "lookup_alphabet_out.txt", "lookup_boundary_out.txt",
                  "lookup_refusal_body.bin", "lookup_refusal_out.txt",
                  "lookup_variants_out.txt", "me_block_20260926T0040Z.json",
                  "me_reading_20260925T2255Z.json", "me_reading_20260926T0004Z.json",
                  "meatproxy_capabilities_20260926T0111Z.json",
                  "name_denominator_20260926T0025Z.json",
                  "name_denominator_two_clocks_20260926T0027Z.json",
                  "permission_instant.json", "permission_instant_meatproxy.json",
                  "politics_n_20260925T2315Z.json", "reading_me_20260925T2340Z.json",
                  "reading_meatproxy_20260925T2340Z.json", "reset_readings.json",
                  "v1_prefix_door.json")
    judge_holds = set(probe_names)
    cited = "ladder_rungs.json"
    refused = cited not in judge_holds
    return {"judged_against": "the probe files only (%d)" % len(judge_holds),
            "data_files_the_directory_holds": len(data_files),
            "citations_refused_though_the_file_is_here": int(refused)}


NAMESPACES.setdefault("a-fixture-that-copies-what-it-was-told-and-the-subject-imports-more", {}).update(
    {"a_repeat_that_judges_a_cited_name_against_an_enumeration_the_directory_outgrew": a_repeat_that_judges_a_cited_name_against_an_enumeration_the_directory_outgrew})
