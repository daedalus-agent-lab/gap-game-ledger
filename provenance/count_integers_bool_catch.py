def count_integers(items):
    """Count how many elements in items are integers.

    Booleans and non-integer types are excluded from the count.
    """
    return sum(1 for x in items if isinstance(x, int))


def main() -> None:
    print("control", count_integers([10, "20", 30.5, 40, None, [50]]))
    assert count_integers([10, "20", 30.5, 40, None, [50]]) == 2
    fact = count_integers([True, False, 1])
    print("promised 1                            ", 1)
    print("fact                                  ", fact)
    assert fact == 3
    print("kill                                  bool is a subclass of int")


if __name__ == "__main__":
    main()
