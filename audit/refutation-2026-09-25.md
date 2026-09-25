<!-- An independent audit performed by a reader told to break this ledger.
     Kept here unedited except for local paths, so the refutation travels with
     the repair: a report that only says what was wrong, without the commands
     that showed it, cannot be re-run or disputed. Section 3 is a limitation the
     ledger's own docstrings already declare; it is not registered as a class. -->

# Refutation report — gap-game-ledger, cold clone, 2026-09-25

**Clone** (cold, `--depth 1`, never the leader's working tree):

```
$ mkdir -p audit-work && cd audit-work
$ git clone --depth 1 https://github.com/daedalus-agent-lab/gap-game-ledger.git repo
$ cd repo && git log --oneline -1
5bb89c01be6a86877cf674149ebaeb713e75f1ab Print the tree each item read, and refuse to certify a reading taken across two
```

HEAD = `5bb89c01be6a86877cf674149ebaeb713e75f1ab`. Everything below was run inside copies of that clone
(`attack1/`, `copy1/`, `copy1b/`, `mut/*`); the working tree that produced the ledger was not touched.

Baseline, for contrast:

```
$ cd repo && python3 check.py; echo exit=$?
exit=0
entries 138  ok 136  miss 0  skipped 2
distinct class fragments 136/136  (class fragments only: no class is another class under a new name)
fingerprint control ok  20 pairs over 16 rules of the policy (15 guarded, 1 declared without a pair), each pair answering as its rule requires
reported instances 179 (repeats 41: 41 replayed by this script, 0 label-only)
instances with a public citation 58/179 (58 of them quote a line of the fragment)  (cited, not shown to be independent)
index    CLASSES.md is current
```

---

## 1. "Every class fragment is distinct in a way the fingerprint can see"

**REFUTED** — for the guarantee, not for the count. Two fragments whose answers differ (`41` against
`NameError`) get **one** fingerprint, and check.py's own collision test names them one piece of logic.
`check.py` guards the bare name (`eval(...)`), the attribute spelling (`builtins.eval(...)`,
check.py:129–137) and frame paths (`f_locals`, check.py:117–127), but not a reader built from a string
at the call — `getattr(builtins, "eval")`, the same reach under a third spelling. The dead-store pass
sees no name and no attribute from its reader sets, drops the store, and two different lies become one
AST. Raw:

```
$ cd audit-work/attack1 && python3 collision_through_check.py
answer(lie_with_the_store)    = 41
answer(lie_without_the_store) = NameError
fingerprint(a) == fingerprint(b): True
class_collisions -> 2 primaries; ['probe-class-b.lie_without_the_store has the logic of probe-class-a.lie_with_the_store']
```

(`collision_through_check.py` calls the clone's own `check.fingerprint` and `check.class_collisions`,
with the two fragments registered under two synthetic class names; receipt v1241.)

The same blind spot is quoted against a second sighting — a repeat that really is a different lie is
refused as "the class probe again" (receipt: run below):

```
$ python3 repeat_gate.py
answer(lie_read_by_a_caller) = ['secret']
answer(lie_nothing_reads)    = []
fingerprint equal: True
evaluate -> ('miss', "repeat 'second-sighting': lie_nothing_reads fingerprints like lie_read_by_a_caller; that is the class probe again, not a second sighting")
```

**Scope, measured.** I re-ran the shipped count and also fingerprinted *every* fragment in every
namespace (232 fragments, not only the 136 primaries). Five fingerprint values are shared, and none of
them is a live class-vs-class collision: the three `dist` duplicates and the two `with_appended`
duplicates are the same function object reused in two namespaces; `reverse-slice-on-negative-index.clip`
/ `take` are two names inside one class; `merge_counts` vs `merge_dicts` is the one real
different-promises-same-logic pair and the ledger already carries it in `declined` as
`DUPE … dict-update-overwrites-first`. So the printed 136/136 is a true count over the primaries of this
tree; what it is **not** is a statement that the pairs it counted are different lies — the instrument it
counts with cannot see that difference, as the pair above shows.

Also worth naming: the count's universe is 136 of 138 entries. `default-string-sort` and
`samevaluezero-vs-deep-equality` are `lang=javascript` and are skipped, so no fingerprint covers them
at all.

---

## 2. "A repeat (instance) is a second sighting, not a restatement"

**REFUTED.** The gate's whole power to separate "a second sighting" from "the class probe again" is the
**wording** of the `promise`/`fact` strings. I injected one repeat into `zero-length-tail-returns-all`
whose bytes, probe, `expected` and `observed` are the class's own, and whose `fact` is byte-identical to
the class's; only the `promise` was a paraphrase. `check.py` exits 0 and counts it (receipt v1242):

```
$ cd audit-work/copy1   # pristine clone + the one injected repeat; CLASSES.md regenerated
$ python3 check.py; echo exit=$?
exit=0
second claim on the same bytes 4: a-coverage-check-drawn-from-the-covered-set/the-count-names-its-universe, clamp-no-range-validation/clamp-nan-passes-through, zero-length-tail-returns-all/same-bytes-reworded, a-control-pair-fixed-by-a-difference-the-rule-never-touches/a-pair-credited-by-a-break-that-does-not-break-its-rule  (a repeat whose fragment IS the class fragment, carrying a different promise: the registry is keyed by the shape of the lie, not by the fragment, and a keyed-by-fragment registry drops the second claim without saying so)
reported instances 180 (repeats 42: 42 replayed by this script, 0 label-only)
```

`179 -> 180`: the restatement is counted as an instance. Put the `promise` back into the class's own
words — nothing else changed, same file, same fragment, same probe — and the same record is refused:

```
$ cd audit-work/copy1b
$ python3 check.py; echo exit=$?
MISS  zero-length-tail-returns-all   repeat 'same-bytes-reworded' replays last_n, the class fragment itself, and makes the class's own claim: that is the class probe, not a second sighting
exit=1
```

So the difference between an accepted instance and a refused restatement is a reworded sentence about
the same bytes, and nothing in the run tells a reader which of the two they are looking at. The
`second claim on the same bytes` line prints it, but printing is not gating: the instance stays in the
count either way (it is still `reported instances 180` in the refused run above).

For "an instance that cites another" I searched the shipped ledger for addresses used more than once:
four addresses are shared, and each is one message cited by a class and by a repeat belonging to a
*non*-owning class (e.g. `a475e0bc…` = class `a-quotation-reissued-as-a-computation` and repeat
`the-view-is-left-out-of-the-key/the-digest-of-the-door-quoted-without-the-function-that-built-it`); no
entry cites its own address. That part of the claim I could not break — see the last section for why it
cannot be settled from the repo at all.

---

## 3. "check.py exit 0 means the record is consistent"

**REFUTED.** Three single-field mutations, each in a fresh copy of the pristine clone, with
`python3 check.py --index > CLASSES.md` run afterwards (the documented way to refresh the index). Full
evidence: `audit-work/evidence/claim3.txt`. The plain outputs:

```
## M1  promise of truncating-floor-division rewritten to the behaviour the fragment actually has
$ cd mut/promise && python3 check.py; echo exit=$?
exit=0
entries 138  ok 136  miss 0  skipped 2
index    CLASSES.md is current

## M2  address of zero-length-tail-returns-all replaced by a fabricated message id
$ cd mut/address && python3 check.py; echo exit=$?
exit=0
entries 138  ok 136  miss 0  skipped 2
instances with a public citation 58/179 (58 of them quote a line of the fragment)
$ python3 -c 'import check; print(check.address_resolves("00000000-0000-0000-0000-000000000000"))'
True

## M3  first_seen of truncating-floor-division replaced (index NOT regenerated)
$ cd mut/first_seen && python3 check.py; echo exit=$?
exit=0

## M4  CONTROL: expected of truncating-floor-division set equal to observed
$ cd mut/expected_eq_observed && python3 check.py; echo exit=$?
exit=1
MISS  truncating-floor-division   ledger's expected == observed; that is not a divergence
```

Why M1 and M2 are *demonstrably* wrong, not just "unverified":

* M1 — the ledger's `promise` is defined in CONTRIBUTING.md as "the docstring's extra claim, quoted".
  The fragment's docstring is `"""Integer floor division of a by b."""` and its behaviour is
  `floor_div(-7, 2) = -3`, i.e. truncation toward zero. After the mutation the ledger's promise field
  says "the quotient truncated toward zero" — it now agrees with the code and contradicts the docstring
  it claims to quote, so the entry is no longer a lie at all, while the run stays green and still prints
  `ok` for it.
* M2 — after the mutation the entry's citation is `00000000-0000-0000-0000-000000000000`. Nothing in
  the run resolves an address: `address_resolves` is a UUID regex (`check.py:969-981`), it answers
  `True` for the fabricated id, and the citation counter keeps reporting `58/179` with the note "cited,
  not shown to be independent".
* M3 — `first_seen` is neither printed by `render_index` nor read by any check, so it can be rewritten
  with no index refresh at all and the run is green and silent.

The control M4 shows the run is not vacuous: `expected == observed` *is* caught, and an unrefreshed
edit to a *rendered* field (promise, address, fact, probe, note, aliases) prints `STALE` and exits 1 —
so exit 0 does mean "the index matches the ledger and every probe replays". It does not mean the prose
fields are true, and the citation the whole "public registry" rests on is one of those fields.

---

## What my check could not reach

* **Every address and citation is taken on trust.** Nothing in `check.py` performs a request; I fetched
  no board message either. So the truth of `58/179 instances with a public citation`, of every
  `address_quote`, and of the four shared addresses (§2) is untested here — a fabricated UUID and a real
  one are indistinguishable to the run, which is exactly what M2 shows.
* **The two skipped entries.** `default-string-sort` and `samevaluezero-vs-deep-equality` (both
  `lang=javascript`) are never replayed and never fingerprinted; the "distinct fragments" count does not
  cover them, so nothing in this report says anything about them.
* **Claim 1 is refuted as a guarantee, not as a count.** I did not enumerate the space of fingerprint
  collisions; one counterexample refutes "the fingerprint can see every difference", but I cannot say
  how many of the 136 counted fragments would still look distinct under a stronger instrument.
* **The declared gap and its covering row.** `R13 -> r_idempotence` is declared; the row lives in
  `verify_claims.py`, which I did not run, and I did not test that the erasure is idempotent.
* **The probes' semantics.** I checked that a probe replays its `observed` and that `observed !=
  expected`; I did not ask whether `observed` is what a real caller of the fragment would see (harness,
  imports, env), nor whether each `promise` matches the docstring it quotes — except for the one entry I
  mutated.
* **Everything else in the tree**: `holds.py`, `verify_claims.py`, `provenance.py` rows, `blind_*`,
  `pre_post.py`, `recover_labels.py`, `doors/`, `probes/` were read at most in outline and not run
  except as `check.py` invokes them. `CLASSES.md` staleness I tested only implicitly, through M3/M4.
* **The 5 shared fingerprint values** (§1) were found by fingerprinting namespace members directly; I
  did not run any probe of those fragments under real inputs beyond the two synthetic pairs above.

Command log and raw outputs: `audit-work/evidence/claim1.txt`, `claim2.txt`, `claim3.txt`;
scripts: `audit-work/attack1/{collision_through_check.py,repeat_gate.py,pair.py}`,
`audit-work/mutate.py`.
