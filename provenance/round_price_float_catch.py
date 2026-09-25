def round_price(x):
    """Round x to 2 decimal places, exact to the cent."""
    return round(x, 2)


def main() -> None:
    print("control", round_price(19.99))
    assert round_price(19.99) == 19.99
    fact = round_price(2.675)
    print("promised 2.68                         ", 2.68)
    print("fact                                  ", fact)
    assert fact == 2.67
    print("kill                                  binary float + bankers round")


if __name__ == "__main__":
    main()
