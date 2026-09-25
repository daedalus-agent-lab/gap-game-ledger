def min_max(items):
    """Returns the minimum and maximum values from any iterable of numbers."""
    return min(items), max(items)


def main() -> None:
    print("control", min_max([3, 1, 2]))
    assert min_max([3, 1, 2]) == (1, 3)
    try:
        fact = min_max(iter([3, 1, 2]))
        print("fact on iterator                      ", fact)
    except ValueError as exc:
        print("promised (1, 3)                       ", (1, 3))
        print("fact                                  ", type(exc).__name__, exc)
        print("kill                                  min consumes the iterator; max sees empty")


if __name__ == "__main__":
    main()
