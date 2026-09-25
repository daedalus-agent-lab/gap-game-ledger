"""Gap Game catch for moss-lantern dedupe_adjacent.

Docstring: remove ALL duplicates, first occurrence.
Code: adjacent comparison only. Same class as earlier dedupe (v909).
"""


def dedupe_adjacent(items):
    """Remove all duplicate elements, keeping only the first occurrence
    of each value."""
    result = []
    for i, x in enumerate(items):
        if i == 0 or x != items[i - 1]:
            result.append(x)
    return result


def main() -> None:
    print("control", dedupe_adjacent([1, 1, 2, 2, 3]))
    assert dedupe_adjacent([1, 1, 2, 2, 3]) == [1, 2, 3]
    fact = dedupe_adjacent([1, 2, 1])
    print("promised all-dupes gone               ", [1, 2])
    print("fact                                  ", fact)
    assert fact == [1, 2, 1]
    print("kill                                  all duplicates / first occurrence")


if __name__ == "__main__":
    main()
