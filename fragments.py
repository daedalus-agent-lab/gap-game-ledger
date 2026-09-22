"""Minimal reproductions of the lie-classes listed in catches.json.

These are NOT the authors' bytes. Each function is a smallest-possible
reproduction of a class that was killed in the game on the board, written
so that `check.py` can re-run the probe and confirm the divergence is real.
Where an author's original body differed in cosmetics, the class is what is
kept, not the spelling.
"""

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


# --------------------------------------------------------- class -> namespace

NAMESPACES = {
    "clamp-no-range-validation": {"clamp": clamp},
    "whitespace-only-tags-kept": {"split_tags": split_tags},
    "remove-while-iterating-skips-neighbours": {
        "remove_all": remove_all,
        "remove_outliers": remove_outliers,
    },
    "dedupe-sorted-set-reorders": {"dedupe_sorted": dedupe_sorted},
    "title-case-touches-rest-of-word": {"title_case": title_case},
    "dedupe-adjacent-vs-global": {"dedupe_adjacent": dedupe_adjacent},
    "greedy-tag-strip": {"strip_tags": strip_tags},
    "truncating-floor-division": {"floor_div": floor_div},
    "reverse-slice-on-negative-index": {"clip": clip},
    "insert-zero-reverses-order": {"partition": partition},
    "partial-window-not-included": {"sliding_window": sliding_window},
    "cursor-last-not-max": {"next_after": next_after},
    "pad-truncates-when-longer": {"pad_left": pad_left},
    "silent-drop-not-replace": {"to_ascii": to_ascii},
    "raise-not-returned-on-parse-failure": {"to_int": to_int},
    "strict-comparison-defeats-non-decreasing": {"is_sorted": is_sorted},
    "iterator-exhausted-twice": {"sum_and_count": sum_and_count},
    "row-alias-in-grid-build": {"touch_grid": touch_grid},
    "binary-search-not-first-occurrence": {"binary_search": binary_search},
    "intervals-touching-not-merged": {"merge_intervals": merge_intervals},
    "retry-swallows-final-exception": {"with_retry": with_retry, "fail_always": fail_always},
    "punctuation-kept-in-palindrome-test": {"is_palindrome": is_palindrome},
    "negative-number-palindrome": {"is_palindrome_number": is_palindrome_number},
    "charset-strip-vs-affix-removal": {"remove_prefix_suffix": remove_prefix_suffix},
    "config-error-type-mismatch": {"load_config": load_config, "ConfigError": ConfigError},
    "bankers-rounding-on-half": {"round_half_up": round_half_up},
    "extension-without-dot": {"get_extension": get_extension},
    "one-level-flatten": {"flatten": flatten},
    "rotate-without-modulo": {"rotate": rotate},
    "median-even-length": {"median": median},
    "zip-truncates-remainder": {"interleave": interleave},
    "kv-value-not-stripped": {"parse_kv_pairs": parse_kv_pairs},
    "default-flag-lies-about-default": {"is_palindrome_ignore_case": is_palindrome_ignore_case},
    "none-filtered-from-unique-count": {"count_unique": count_unique},
}
