"""Gap Game catch for moss-lantern round_half_up.

Docstring: nearest integer; ties toward +inf (0.5→1, -0.5→0).
Code: int(x + 0.5) — for negatives this is NOT nearest (e.g. -1.6).
"""


def round_half_up(x):
    """Round x to the nearest integer. Ties round toward positive
    infinity, so round_half_up(0.5) == 1 and round_half_up(-0.5) == 0.
    """
    return int(x + 0.5)


def main() -> None:
    print("control round_half_up(2.5)            ", round_half_up(2.5))
    assert round_half_up(2.5) == 3
    print("control round_half_up(0.5)            ", round_half_up(0.5))
    assert round_half_up(0.5) == 1
    print("control round_half_up(-0.5)           ", round_half_up(-0.5))
    assert round_half_up(-0.5) == 0
    # nearest integer to -1.6 is -2; int(-1.6+0.5)=int(-1.1)=-1
    promised = -2
    fact = round_half_up(-1.6)
    print("promised nearest to -1.6              ", promised)
    print("fact                                  ", fact)
    assert fact == -1
    print("kill                                  nearest integer (negatives)")


if __name__ == "__main__":
    main()
