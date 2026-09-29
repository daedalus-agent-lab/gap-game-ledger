"""Lexical FAIL-id comparison; input strings are data, never executed."""
IMPLEMENTED = True

import re
from collections.abc import Mapping

_TOKEN = re.compile(r"FAIL\[([A-Z0-9-]+)\]")

def _read(files):
    if not isinstance(files, Mapping) or not files:
        raise ValueError("nonempty mapping required")
    result = {}
    for path, source in files.items():
        if type(path) is not str or type(source) is not str:
            raise ValueError("plain string path and source required")
        sites = set()
        for number, line in enumerate(source.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            sites.update((token, number) for token in _TOKEN.findall(line))
        if not sites:
            raise ValueError("file has no recognized ids")
        result[path] = sites
    return result

def unemitted_ids(producers, consumers):
    """Return (False, {}) for invalid/unreadable inputs or ordinary exceptions.

    Whole comment lines are ignored. This is a lexical vocabulary check,
    not Python execution, reachability analysis, or proof that print ran.
    """
    try:
        emitted = _read(producers)
        named = _read(consumers)
        vocabulary = {token for sites in emitted.values() for token, _ in sites}
        answer = {
            "emitted": {path: sorted({token for token, _ in sites})
                        for path, sites in emitted.items()},
            "named": {path: sorted({token for token, _ in sites})
                      for path, sites in named.items()},
            "unemitted": {
                path: [[token, line] for token, line in sorted(sites)
                       if token not in vocabulary]
                for path, sites in named.items()
            },
        }
        return True, answer
    except Exception:
        return False, {}
