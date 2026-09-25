"""Gap: find_max claims None on empty; max() raises."""


def find_max(items):
    """Return the largest value in items, or None if items is empty."""
    return max(items)


def main() -> None:
    print("control", find_max([3, 7, 2]))
    assert find_max([3, 7, 2]) == 7
    raised = False
    try:
        fact = find_max([])
    except ValueError:
        raised = True
        fact = "ValueError"
    print("promised None                         ", None)
    print("fact                                  ", fact)
    assert raised
    print("kill                                  max([]) raises, no empty guard")


if __name__ == "__main__":
    main()
