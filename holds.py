"""Optional promise-holds callbacks. A missing hook is not a pass.

None  — out of the hook's stated domain (not success).
True  — value satisfies the reviewed reading of the promise.
False — value is well-typed for the domain and does not satisfy it.

The checker does not infer a contract from a docstring. The hook is
agent-authored and self-reviewed. Adding a hook that is wrong is worse
than having none. Register the callback and its non-value arguments;
check.py passes the selected ledger entry's parsed expected/observed.
"""


def truncate_holds(text, limit, suffix, value):
    """Reviewed reading: keep the original prefix, include the suffix
    inside the limit, leave short inputs unchanged, returned length
    agrees with the string. Domain: Python str lengths, nonnegative
    int limit, suffix that fits. None means outside that domain.
    """
    if type(text) is not str or type(suffix) is not str or type(limit) is not int:
        return None
    if limit < 0 or len(suffix) > limit:
        return None
    if type(value) is not tuple or len(value) != 2:
        return False
    out, size = value
    if type(out) is not str or type(size) is not int or size != len(out):
        return False
    if len(text) <= limit:
        return out == text
    prefix_len = limit - len(suffix)
    return (
        size == limit
        and out[:prefix_len] == text[:prefix_len]
        and out[prefix_len:] == suffix
    )


HOLDS = {
    "suffix-stacked-on-full-slice": {
        "fn": truncate_holds,
        "prefix": ("hello world", 5, "..."),
    },
}
