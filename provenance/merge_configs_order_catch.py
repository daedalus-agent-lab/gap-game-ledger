def merge_configs(base, override):
    """Merge two config dicts, with override taking precedence for conflicting keys."""
    return {**override, **base}


def main() -> None:
    print("control", merge_configs({"timeout": 60, "retries": 3}, {"timeout": 30}))
    fact = merge_configs({"a": 1}, {"a": 2})
    print("promised {'a': 2}                     ", {"a": 2})
    print("fact                                  ", fact)
    assert fact == {"a": 1}
    print("kill                                  last unpack wins; base last")


if __name__ == "__main__":
    main()
