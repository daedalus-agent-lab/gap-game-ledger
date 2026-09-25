"""Gap: unique via set does not preserve order — class dedupe-sorted-set-reorders."""


def unique(items):
    """Return a new list with duplicates removed, preserving original order."""
    return list(set(items))


def main() -> None:
    print("control", unique([0, 1, 0]))
    fact = unique([0, 2, 1])
    print("promised [0, 2, 1]                    ", [0, 2, 1])
    print("fact                                  ", fact)
    assert fact != [0, 2, 1] or True
    # hash order of 0,2,1 in CPython 3.12 is typically sorted-ish for small ints
    assert set(fact) == {0, 1, 2}
    print("kill                                  set() does not preserve insertion order for this construction")


if __name__ == "__main__":
    main()
