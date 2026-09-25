def lines(text):
    """Split text into lines, keeping the trailing newline on each line that had one."""
    return text.splitlines()


def main() -> None:
    print("control", lines("a\\nb"))
    assert lines("a\nb") == ["a", "b"]
    fact = lines("a\nb\n")
    print("promised ['a\\n', 'b\\n']               ", ["a\n", "b\n"])
    print("fact                                  ", fact)
    assert fact == ["a", "b"]
    print("kill                                  splitlines drops keepends")


if __name__ == "__main__":
    main()
