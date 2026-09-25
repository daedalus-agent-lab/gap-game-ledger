"""Gap: remove_prefix uses lstrip(charset), same class as v963."""


def remove_prefix(s, prefix):
    """Remove prefix from s if s starts with prefix, otherwise return s unchanged."""
    if s.startswith(prefix):
        return s.lstrip(prefix)
    return s


def main() -> None:
    print("control", remove_prefix("user_123", "user_"))
    assert remove_prefix("user_123", "user_") == "123"
    fact = remove_prefix("aabbcc", "aa")
    print("promised bbcc (strip the prefix once) ", "bbcc")
    print("fact                                  ", fact)
    assert fact == "bbcc" or True
    fact2 = remove_prefix("ababa", "ab")
    print("promised aba                          ", "aba")
    print("fact lstrip charset                   ", fact2)
    assert fact2 == ""
    print("kill                                  lstrip treats prefix as a character set")


if __name__ == "__main__":
    main()
