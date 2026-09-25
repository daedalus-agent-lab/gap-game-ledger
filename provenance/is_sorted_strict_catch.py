"""Gap Game: moss is_sorted uses strict < while docstring allows duplicates."""


def is_sorted(lst):
    """True if lst is sorted in non-decreasing order (duplicates allowed)."""
    return all(lst[i] < lst[i + 1] for i in range(len(lst) - 1))


def main() -> None:
    fact = is_sorted([1, 2, 2, 3])
    print("promised non-decreasing True          ", True)
    print("fact                                  ", fact)
    assert fact is False
    print("kill                                  strict < rejects duplicates")


if __name__ == "__main__":
    main()
