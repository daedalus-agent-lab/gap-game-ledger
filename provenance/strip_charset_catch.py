"""Gap Game: moss remove_prefix_suffix uses strip charset not substring."""


def remove_prefix_suffix(s, chars):
    """Remove the substring `chars` from the start and end of s, if present."""
    return s.strip(chars)


def main() -> None:
    print("control", remove_prefix_suffix("__hello__", "__"))
    assert remove_prefix_suffix("__hello__", "__") == "hello"
    fact = remove_prefix_suffix("abXba", "ab")
    print("promised substring only               ", "Xba")  # remove prefix 'ab' only if exact
    # strip treats chars as a set: strips any of {a,b} from both ends
    print("fact                                  ", fact)
    assert fact == "X"
    print("kill                                  strip charset, not substring")


if __name__ == "__main__":
    main()
