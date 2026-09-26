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
    """The null model by simulation: median, 5th and 95th percentile."""
    rng = random.Random(seed)
    values = []
    for _ in range(runs):
        counts = [0] * k
        for _ in range(n):
            counts[rng.randrange(k)] += 1
        values.append(sum((c / n) ** 2 for c in counts))
    values.sort()
    return (statistics.median(values), values[int(0.05 * runs)], values[int(0.95 * runs)])


def check(out=sys.stdout):
    """Every line here must hold, or the published formula is not what was published."""
    problems = []
    out.write("null model, n=%d, %d runs, seed %d\n" % (N, RUNS, SEED))
    for k, published in PUBLISHED:
        median, lo, hi = simulate(N, k)
        closed = expected_hhi(N, k)
        out.write(
            "  k=%-5d closed %.4f | simulated median %.4f | published median %.4f"
            " | 5%% %.4f 95%% %.4f\n" % (k, closed, median, published, lo, hi)
        )
        if abs(closed - median) > TOLERANCE * 2:
            problems.append("k=%d: the closed form disagrees with my own simulation" % k)
        if abs(median - published) > TOLERANCE:
            problems.append("k=%d: my simulation does not reproduce the published median" % k)
        if abs(closed - published) > TOLERANCE * 2:
            problems.append("k=%d: the closed form does not reproduce the published median" % k)
        # The floor alone is the naive baseline the study's own numbers refute: if
        # 1/n were the expectation, every one of these medians would equal 0.0182.
        if abs(1.0 / N - median) <= TOLERANCE:
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
    medians = [simulate(n, k, runs=runs, seed=s)[0] for s in range(1, seeds + 1)]
    if out is not None:
        out.write(
            "      resolution of this comparison: %.4f (median over seeds 1..%d)\n"
            % (max(medians) - min(medians), seeds)
        )
    return max(medians) - min(medians)


def selftest(out=sys.stdout):
    """The check must be able to fail: plant each wrong model and see it caught."""
    checks = []
    median = simulate(N, 20)[0]
    res = resolution(N, 20, out=out)

    mutants = {
        "the floor alone": lambda n, k: 1.0 / n,
        "the pool term alone": lambda n, k: 1.0 / k,
        "the sample term outside the mixture": lambda n, k: 1.0 / k + 1.0 / n,
        "the mixture without the pool weight": lambda n, k: 1.0 / k + (1.0 - 1.0 / k) / k,
    }
    for name, wrong in mutants.items():
        gap = abs(wrong(N, 20) - median)
        checks.append(("the check refuses %s (gap %.4f > resolution %.4f)" % (name, gap, res), gap > res))
    checks.append(
        (
            "the published form survives the same comparison",
            abs(expected_hhi(N, 20) - median) <= res,
        )
    )
    # A fifth mutant is deliberately NOT a check: it sits inside the resolution, so
    # this comparison cannot tell it from the published model. Saying so out loud is
    # more useful than a tolerance picked to make it pass.
    faint = abs((1.0 / 20 + (1.0 - 1.0 / N) / N) - median)
    out.write(
        "     a sixth mutant, 1/k + (1-1/n)/n, differs by %.4f -- inside the resolution, "
        "so\n     this comparison cannot refuse it; 4000 runs do not buy that separation.\n" % faint
    )
    checks.append(("a pool of one returns 1", expected_hhi(55, 1) == 1.0))
    checks.append(
        (
            "the formula matches this very simulation",
            all(abs(expected_hhi(N, k) - simulate(N, k, runs=1200)[0]) < 0.006 for k, _ in PUBLISHED),
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
