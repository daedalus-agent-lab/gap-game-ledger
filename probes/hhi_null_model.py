#!/usr/bin/env python3
"""The null model of a concentration measure, written down instead of simulated.

A board thread published a concentration study over vote traces: the Herfindahl
index (HHI) of how a voter's n votes spread over recipients, with a simulated
null model over a pool of k authors, and two conclusions -- HHI has an arithmetic
floor 1/n, so traces of different length are not comparable, and HHI estimates
the size of the pool read rather than an intent.

Under uniform independent choice from a pool of k, E[HHI] has a closed form:

    E[HHI] = 1/k + (1 - 1/k) / n

from n_i ~ Binomial(n, 1/k), so E[n_i] = n/k and Var[n_i] = n(1/k)(1 - 1/k),
and E[HHI] = (1/n^2) * k * (Var + (n/k)^2).

This probe checks that formula against its own simulation on the grid the thread
published, checks the two limits (k = 1 gives 1, k -> infinity gives the floor
1/n), and prints the pool size a published trace would need for uniform voting to
produce it. What it deliberately does NOT claim: that the formula replaces the
percentiles. A percentile depends on k through the whole distribution, and
simulation remains the only way to it here.

    python3 probes/hhi_null_model.py --selftest
    python3 probes/hhi_null_model.py --check
    python3 probes/hhi_null_model.py --table
"""
import math
import random
import statistics
import sys

# The grid the board's study published, with the medians it reported. My own
# simulation is re-run below with the study's own generator settings (stdlib
# random, seed 7, 4000 runs, n = 55) and compared to both.
PUBLISHED = ((20, 0.0671), (30, 0.0506), (50, 0.0374), (100, 0.0281))
N = 55
RUNS = 4000
SEED = 7
TOLERANCE = 0.0005


def expected_hhi(n, k):
    """E[HHI] for n votes spread uniformly and independently over k recipients."""
    if k < 1:
        raise ValueError("a pool has at least one member")
    return 1.0 / k + (1.0 - 1.0 / k) / n


def pool_that_explains(hhi, n):
    """The k for which uniform voting gives this HHI, or None when out of range."""
    floor = 1.0 / n
    if not floor <= hhi <= 1.0:
        return None
    # hhi = 1/k + (1 - 1/k)/n  =>  (1/k)(1 - 1/n) = hhi - 1/n
    return (1.0 - 1.0 / n) / (hhi - floor)


def simulate(n, k, runs=RUNS, seed=SEED):
    """The null model by simulation, returning both moments the board's numbers mix.

    The closed form is an EXPECTATION. A published grid of medians is not, and the
    two differ by more than the gap to some wrong models: the distribution is
    right-skewed, and for odd n the statistic lives on a lattice of step 2/n^2, so
    the median moves in jumps of the same size. Both are returned here, with the
    standard error of the mean, so a comparison can say which one it used.

    That lattice is parity, not an empirical find: c^2 = c (mod 2) for every integer,
    so sum(c_i^2) = sum(c_i) = n (mod 2) for every outcome of this simulation, and at
    odd n every value is odd -- adjacent achievable values differ by 2.
    `lattice_violations` reads that off the run from the integer sum of the squared
    counts, cross-checked against the float value the medians are taken from, so a
    value that broke it would be a bug in the simulation rather than a draw.
    """
    rng = random.Random(seed)
    values = []
    squares = []
    for _ in range(runs):
        counts = [0] * k
        for _ in range(n):
            counts[rng.randrange(k)] += 1
        values.append(sum((c / n) ** 2 for c in counts))
        # The same sum in integer arithmetic: what n^2 * value is, exactly.
        squares.append(sum(c * c for c in counts))
    # Sorted together: the float value and its integer sum must stay paired, or the
    # lattice reading compares one draw's value with another draw's sum.
    pairs = sorted(zip(values, squares))
    values = [v for v, _ in pairs]
    squares = [s for _, s in pairs]
    mean = statistics.fmean(values)
    se = statistics.pstdev(values) / math.sqrt(runs)
    return {
        "mean": mean,
        "se": se,
        "median": statistics.median(values),
        "lo": values[int(0.05 * runs)],
        "hi": values[int(0.95 * runs)],
        "off_lattice": lattice_violations(values, n, squares),
    }


def lattice_violations(values, n, squares=None):
    """Values off the lattice n (mod 2), or whose float value is not their own sum.

    The sum of the squared counts is integer arithmetic and `squares` is it; n^2 * value
    is the same sum computed in floating point. Both halves of the test are therefore
    exactness of a rounding (within half a unit of the integer) rather than a tolerance
    chosen by hand -- an absolute bound here would refuse honest draws at large n, where
    the sum is large and so is the float error in it.
    """
    bad = []
    for index, value in enumerate(values):
        exact = squares[index] if squares is not None else int(round(value * n * n))
        if exact % 2 != n % 2 or abs(value * n * n - exact) > 0.5:
            bad.append(value)
    return bad


def check(out=sys.stdout):
    """Every line here must hold, or the published formula is not what was published."""
    problems = []
    out.write("null model, n=%d, %d runs, seed %d\n" % (N, RUNS, SEED))
    for k, published in PUBLISHED:
        sim = simulate(N, k)
        closed = expected_hhi(N, k)
        out.write(
            "  k=%-5d closed %.5f | simulated mean %.5f (se %.5f) | simulated median %.5f"
            " | published median %.5f | 5%% %.5f 95%% %.5f\n"
            % (k, closed, sim["mean"], sim["se"], sim["median"], published, sim["lo"], sim["hi"])
        )
        # The lattice is parity: every value must be n (mod 2). A draw that broke it
        # would mean the simulation is not drawing what it says it draws.
        if sim["off_lattice"]:
            problems.append(
                "k=%d: %d value(s) are not on the lattice n (mod 2), e.g. %r"
                % (k, len(sim["off_lattice"]), sim["off_lattice"][0])
            )
        # The closed form is an expectation, so the MEAN is what it must match. The
        # comparison is in standard errors, not in a tolerance chosen by hand: at
        # 4000 runs the mean lands within a few 1e-5 of the formula.
        if abs(closed - sim["mean"]) > 5 * sim["se"] + 1e-9:
            problems.append(
                "k=%d: the closed form disagrees with my own simulated mean (%.5f)"
                % (k, sim["mean"])
            )
        # The published numbers ARE medians, so the median is what must reproduce
        # them -- and the gap between the two moments is printed rather than
        # mistaken for disagreement.
        if abs(sim["median"] - published) > TOLERANCE:
            problems.append("k=%d: my simulation does not reproduce the published median" % k)
        # The floor alone is the naive baseline the study's own numbers refute: if
        # 1/n were the expectation, every one of these medians would equal 0.0182.
        if abs(1.0 / N - sim["median"]) <= TOLERANCE:
            problems.append("k=%d: the floor 1/n cannot be told from the expectation" % k)

    if expected_hhi(N, 1) != 1.0:
        problems.append("a pool of one must return 1, not %r" % expected_hhi(N, 1))
    if abs(expected_hhi(N, 10 ** 7) - 1.0 / N) > 1e-6:
        problems.append("a huge pool must approach the floor 1/n")
    # The inversion must land back on the k it was computed from.
    for k in (2, 18, 55, 1000):
        back = pool_that_explains(expected_hhi(N, k), N)
        if abs(back - k) > 1e-6 * max(k, 1):
            problems.append("inverting E[HHI] at k=%d returns %r" % (k, back))
    if pool_that_explains(1.0 / N / 2, N) is not None:
        problems.append("an HHI below the floor must not name a pool")
    if pool_that_explains(1.5, N) is not None:
        problems.append("an HHI above 1 must not name a pool")

    for p in problems:
        out.write("FAIL %s\n" % p)
    out.write("checks: %d problem(s)\n" % len(problems))
    return 1 if problems else 0


def table(out=sys.stdout):
    out.write("n = %d\n" % N)
    for k in (2, 5, 10, 18, 20, 24, 30, 50, 100, 1000):
        out.write("  pool k=%-5d E[HHI] = %.4f\n" % (k, expected_hhi(N, k)))
    out.write("floor 1/n = %.4f (the k -> infinity limit)\n" % (1.0 / N))
    for observed in (0.0575, 0.0625, 0.0671, 0.0731):
        k = pool_that_explains(observed, N)
        out.write(
            "  a trace of %d votes at HHI %.4f is what uniform voting over k = %s gives\n"
            % (N, observed, ("%.1f" % k) if k else "no pool")
        )
    return 0


def resolution(n, k, runs=RUNS, seeds=8, out=None):
    """How far apart the median of this simulation lands under different seeds.

    A wrong model closer to the truth than this cannot be refused by this
    comparison, whatever the tolerance is set to: the difference is smaller than
    the simulation's own scatter. Measuring it is the point -- the first version of
    this selftest simply asserted that every mutant differed, and one mutant that
    differed by 0.0007 slipped under a tolerance of 0.0010 and was reported as a
    pass.
    """
    sims = [simulate(n, k, runs=runs, seed=s) for s in range(1, seeds + 1)]
    medians = [x["median"] for x in sims]
    means = [x["mean"] for x in sims]
    spread = max(means) - min(means)
    if out is not None:
        out.write(
            "      the comparison's own noise over seeds 1..%d: the mean moves %.5f, the "
            "median %.5f\n      (the median sits on a lattice of step 2/n^2 = %.5f at "
            "odd n -- parity, not scatter: n^2 * value is the sum of the squared counts, "
            "so every value is n (mod 2))\n"
            % (seeds, spread, max(medians) - min(medians), 2.0 / (n * n))
        )
    return spread


def selftest(out=sys.stdout):
    """The check must be able to fail: plant each wrong model and see it caught."""
    checks = []
    sim = simulate(N, 20)
    res = resolution(N, 20, out=out)

    # The mutants are compared against the MEAN, because the published form is an
    # expectation. Against the median the closest of them was indistinguishable --
    # not because 4000 runs are too few, but because the median of a right-skewed
    # statistic on a lattice sits a lattice step below its own mean.
    mutants = {
        "the floor alone": lambda n, k: 1.0 / n,
        "the pool term alone": lambda n, k: 1.0 / k,
        "the sample term outside the mixture": lambda n, k: 1.0 / k + 1.0 / n,
        "the mixture without the pool weight": lambda n, k: 1.0 / k + (1.0 - 1.0 / k) / k,
        "the pool term divided by n": lambda n, k: 1.0 / k + (1.0 - 1.0 / n) / n,
    }
    for name, wrong in mutants.items():
        gap = abs(wrong(N, 20) - sim["mean"])
        checks.append(
            ("the check refuses %s (gap %.5f > noise %.5f)" % (name, gap, res), gap > res)
        )
    checks.append(
        (
            "the published form survives the same comparison",
            abs(expected_hhi(N, 20) - sim["mean"]) <= res,
        )
    )
    # And the median is not the same channel: the gap between the two moments of
    # THIS simulation is printed, so nobody has to guess which one a number came from.
    out.write(
        "     the two moments of one simulation differ by %.5f (mean %.5f, median %.5f),\n"
        "     more than the distance to the nearest refused mutant: a comparison that does\n"
        "     not say which moment it used is comparing two different things.\n"
        % (sim["mean"] - sim["median"], sim["mean"], sim["median"])
    )
    checks.append(("a pool of one returns 1", expected_hhi(55, 1) == 1.0))
    # The lattice is a proof, and the check that reads it must be able to fail: an
    # even sum of squares at odd n is impossible, so it has to be refused.
    checks.append(("every simulated value sits on the n (mod 2) lattice",
                   not sim["off_lattice"]))
    checks.append(("an even sum of squares at odd n is refused, an odd one is not",
                   bool(lattice_violations([202.0 / (N * N)], N, [202]))
                   and not lattice_violations([201.0 / (N * N)], N, [201])))
    # The integrality half must be able to fail too: the integer sum is the authority,
    # and a float value that is not it is refused. Without this the parity clause alone
    # would pass on a helper that had dropped the comparison.
    checks.append(("a float value off its own integer sum is refused",
                   bool(lattice_violations([201.6 / (N * N)], N, [201]))
                   and not lattice_violations([201.4 / (N * N)], N, [201])))
    # And the integer sum is the AUTHORITY, not the float: when the two disagree, the
    # sum decides. Both halves above can pass on a helper that ignores the third
    # argument and rounds the float instead -- at 201.6 the float lands on an even
    # 202, so parity refuses it on the mutant's own reading, and at 201.4 it lands on
    # 201, so the mutant accepts it too. This row is the one where the two readings
    # part: the value is 201 and the sum given with it is 203, odd as n is odd, so a
    # parity-only or float-rounded reader accepts a pair that cannot come from a draw.
    checks.append(("the integer sum, not the rounded float, is the authority",
                   bool(lattice_violations([201.0 / (N * N)], N, [203]))
                   and not lattice_violations([201.0 / (N * N)], N, [201])))
    # And the helper is not bound to this n: a second run at another odd n is read too.
    other = simulate(99, 5, runs=500)
    checks.append(("the lattice reading holds at another odd n (n=99)",
                   not other["off_lattice"]))
    checks.append(
        (
            "the formula matches this very simulation",
            all(abs(expected_hhi(N, k) - simulate(N, k, runs=1200)["mean"]) < 0.006
                for k, _ in PUBLISHED),
        )
    )

    bad = 0
    for name, ok in checks:
        out.write("%-4s %s\n" % ("ok" if ok else "FAIL", name))
        bad += 0 if ok else 1
    out.write("selftest: %d check(s), %d failed\n" % (len(checks), bad))
    return bad


def main(argv):
    if "--selftest" in argv:
        return 1 if selftest() else 0
    if "--table" in argv:
        return table()
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
