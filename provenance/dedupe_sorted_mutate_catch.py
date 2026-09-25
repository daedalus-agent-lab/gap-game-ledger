"""Gap Game: moss dedupe_sorted mutates the original list."""


def dedupe_sorted(items):
    """Remove consecutive duplicate values from a sorted list and return
    the result, without modifying the original list."""
    i = 0
    while i < len(items) - 1:
        if items[i] == items[i + 1]:
            del items[i + 1]
        else:
            i += 1
    return items


def main() -> None:
    print("control", dedupe_sorted([1, 1, 2, 3, 3]))
    src = [1, 1, 2]
    fact = dedupe_sorted(src)
    print("promised src unchanged                ", [1, 1, 2])
    print("fact src                              ", src)
    print("same object                           ", fact is src)
    assert src == [1, 2]
    assert fact is src
    print("kill                                  in-place del; same object returned")


if __name__ == "__main__":
    main()
