"""Self-check: take claims empty on n<0; slice from the end."""


def take(xs, n):
    """Return the first n items of xs. If n is negative, return an empty list."""
    return xs[:n]


def main() -> None:
    print("control", take([1, 2, 3, 4], 2))
    assert take([1, 2, 3, 4], 2) == [1, 2]
    fact = take([1, 2, 3, 4], -1)
    print("promised []                           ", [])
    print("fact                                  ", fact)
    assert fact == [1, 2, 3]
    print("kill                                  xs[:n] reverse-slices when n<0")


if __name__ == "__main__":
    main()
