"""Self fragment: chunk into pairs, last leftover dropped vs promised singleton."""


def pairs(items):
    """Return consecutive pairs. A leftover last item becomes a one-element group."""
    return list(zip(items[::2], items[1::2]))


def main() -> None:
    print("control", pairs([1, 2, 3, 4]))
    assert pairs([1, 2, 3, 4]) == [(1, 2), (3, 4)]
    fact = pairs([1, 2, 3])
    print("promised [(1, 2), (3,)]               ", [(1, 2), (3,)])
    print("fact                                  ", fact)
    assert fact == [(1, 2)]
    print("kill                                  zip truncates leftover")


if __name__ == "__main__":
    main()
