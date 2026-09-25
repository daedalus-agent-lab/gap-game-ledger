def clone_matrix(matrix):
    """Return an independent deep copy of matrix; mutating the clone never touches the original."""
    return [row[:] for row in matrix]


def main() -> None:
    print("control", clone_matrix([[1, 2], [3, 4]]))
    m = [[[1]], [[2]]]
    c = clone_matrix(m)
    c[0][0].append(9)
    print("promised m[0][0] [1]                  ", [1])
    print("fact                                  ", m[0][0])
    assert m[0][0] == [1, 9]
    print("kill                                  row[:] is one level, not deep")


if __name__ == "__main__":
    main()
