"""Minimal reproductions of the lie-classes listed in catches.json.

These are NOT the authors' bytes. Each function is a smallest-possible
reproduction of a class that was killed in the game on the board, written
so that `check.py` can re-run the probe and confirm the divergence is real.
Where an author's original body differed in cosmetics, the class is what is
kept, not the spelling.
"""

import datetime
import hashlib
import json


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


NAMESPACES = {
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
    "a-rim-sample-quoted-as-a-measurement-of-the-band": {
        "the_seam_agrees": the_seam_agrees, "edge_profile": edge_profile, "dist": dist},
    "a-name-declared-twice-and-the-caveat-on-one-copy": {
        "caveat_reachable_from_every_declaration": caveat_reachable_from_every_declaration,
    },
    "a-quotation-reissued-as-a-computation": {
        "printed_under_the_heading": printed_under_the_heading,
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