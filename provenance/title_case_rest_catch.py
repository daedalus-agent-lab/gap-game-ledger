"""Gap Game: moss title_case — str.title lowercases the rest (class v944)."""


def title_case(s: str) -> str:
    """Capitalize the first letter of every word.
    The rest of each word's letters are left untouched."""
    return s.title()


def main() -> None:
    print("control", title_case("hello world"))
    assert title_case("hello world") == "Hello World"
    fact = title_case("hELLO")
    print("promised rest untouched               ", "HELLO")
    print("fact                                  ", fact)
    assert fact == "Hello"
    fact2 = title_case("don't")
    print("fact apostrophe                       ", fact2)
    assert fact2 == "Don'T"
    print("kill                                  str.title; same class as v944")


if __name__ == "__main__":
    main()
