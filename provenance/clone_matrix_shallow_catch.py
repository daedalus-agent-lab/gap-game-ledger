def clone_matrix(matrix):
    """Return an independent copy of matrix; mutating a row in the copy never affects the original."""
    return [row for row in matrix]


def main() -> None:
    print("control", clone_matrix([[1, 2], [3, 4]]))
    m = [[1, 2], [3, 4]]
    c = clone_matrix(m)
    c[0].append(99)
    print("promised m[0] [1, 2]                  ", [1, 2])
    print("fact                                  ", m[0])
    assert m[0] == [1, 2, 99]
    print("kill                                  shallow copy aliases rows")


if __name__ == "__main__":
    main()
