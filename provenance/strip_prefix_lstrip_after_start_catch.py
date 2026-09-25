def strip_prefix(text: str, prefix: str) -> str:
    """Remove prefix from text if text starts with prefix, else return text unchanged."""
    if text.startswith(prefix):
        return text.lstrip(prefix)
    return text


def main() -> None:
    print("control", strip_prefix("https://example.com", "https://"))
    assert strip_prefix("https://example.com", "https://") == "example.com"
    fact = strip_prefix("https://hats.com", "https://")
    print("promised hats.com                     ", "hats.com")
    print("fact                                  ", fact)
    assert fact == "ats.com"
    print("kill                                  lstrip eats charset after the prefix")


if __name__ == "__main__":
    main()
