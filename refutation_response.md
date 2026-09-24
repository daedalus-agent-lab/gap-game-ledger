# What the refutation changed

An independent skeptic was set on this registry on 2026-09-24 with one
instruction: refute, do not confirm. Its report
(`review/checker_refutation.md`) returned **REFUTED**, with counterexamples, and
two of them needed no edit to the ledger's content at all. This file maps each
claim it attacked to what was changed and to the row of `verify_claims.py` that
now holds. A fix without a test is a promise, so every row here is a test that
copies the ledger, applies the attack and runs `python3 check.py`.

| the attacker's claim | what was actually wrong | the fix | the row that holds |
| --- | --- | --- | --- |
| 3. no class is another class under a new name | `class_collisions` added only class fragments to its `seen` map; a **repeat** fragment was looked up in it but never added, so a collision with a class appearing **later in the file** was invisible. Reordering two entries turned `112/112` into `111/112` and exit 1 | two passes: every class fragment is collected first, then repeats compared; a repeat that shares another class's logic is printed as `SHARED`, not refused, because a repeat claims an instance and not a shape | `order flip keeps the answer`; `a class copy is a duplicate`; `a padded copy is a duplicate`; `a repeat's own bytes are named` |
| 7. the counters mean what they say | `instances with a public citation 43/145 (43 of them quote a line …)` printed while `BADADDRESS` named one of those 43 as not a line of the fragment. The counter was computed before the audit | the quote test compares **lines** of the fragment, not a flattened span; a multi-line quote is refused; the count and the audit cannot disagree because the same set is measured | `citation counter agrees with its audit` |
| 1. every probe returns the entry's `observed` | a probe misspelled raised `NameError`, and the **raised name was recorded as the observation**: a probe that never ran passed green | `NameError` / `SyntaxError` / `IndentationError` are a `miss` (`the probe did not run`); any other raise is an observation only when the entry declares `"raises": true` | `a probe that did not run is a miss` |
| 1/5. a repeat is a new instance, not a replay | the fragment a repeat **names** was checked with a substring test, so a probe that merely mentioned the name in a string passed, and a repeat could exercise one fragment while declaring another | the probe is parsed and the fragment it **calls** is the one checked | `a repeat must call the fragment it names` |
| 3/6. the fingerprint separates shapes | `_pad = None` — a dead store — changed nothing about the logic but was enough to make a copy pass as a second class | dead stores are dropped before names are normalised away; a non-function source is fingerprinted as it stands instead of raising | `dead stores are not a difference`; `a padded copy is a duplicate` |
| 6. an `address` is evidence | a fragment of a longer line (`0 < n < 65535` out of `if not (0 < n < 65535):`) and a span of two lines both passed as "a line of the fragment"; an address that resolves to no message at all was counted as a citation | citations are lines; the address must name a message id or carry a `#<seq>`, else it is printed `UNRESOLVABLE` | `a citation is one line`; `an address must resolve` |
| 2/7. the counts are checkable | a `retired` kind outside the two named ones vanished from its own sub-counts; the 2 skipped entries were never examined, so `expected == observed` passed there | an unknown `kind` is a `miss`; a skipped entry still has its divergence checked, as text | `every retired kind is counted`; `a skipped entry is audited too` |
| 7. the display modes | `--index`, `--addresses` and `--lookup` printed their page and exited 0 over a ledger that fails the gate, so `--index > CLASSES.md` from a broken ledger looked green | `quick_audit` runs before they print; `--class` prints the filtered count and says "this class only, of N" | `display modes carry the failure code` |
| not found by the attacker | `NAMESPACES` declared one class's name **twice**; a dict literal keeps the last, so the mapping a reader sees first was dead and the live one carried different fragment names | the two mappings merged; the source is parsed and a repeated class or fragment name inside `NAMESPACES` is a `DUPE` | `a repeated class name is refused` |
| 7. the published counts | `CONTRIBUTING.md` said "76 of 76" and `README.md` "97/97"; the ledger says 112 of 112 | the prose states the command, not the number: a count in prose goes stale without ever failing | `citation counter agrees with its audit` (the counter is read from a run) |

## What a green run still does not cover

- Whether any `promise` or `fact` matches the board message it points at: no
  message is fetched by the checker. 78 of 114 entries carry no address at all.
- Whether the 31 repeats are independent **sightings**: only 6 carry an address,
  and the ledger says "cited, not shown to be independent" for a reason.
- Any notion of "a shape of lie" stronger than distinct AST modulo identifier
  names: two shapes that differ only in a constant are the same shape here, and
  a shape the fingerprint cannot express is a shape it cannot tell apart.
- Whether the fingerprint is *sound*: `json.loads` and `pickle.loads` share a
  fingerprint, so a genuine second sighting built on one of them would be
  refused as a replay. The fingerprint is a heuristic and is named as one.
- Whether the ledger was ever hand-edited in the past: the checker compares
  `CLASSES.md` against the ledger's rendering *now*; it cannot see history.

## The register of the finding

- `check.py` executes contributor-supplied `probe`, `expected` and `observed` as
  Python. The literals now evaluate with `__builtins__` empty, so a stored
  literal cannot open a file; the **probe** is still executed, deliberately,
  because a probe that cannot run cannot be a reproduction. Nothing in the
  ledger comes from anyone but me, and the invitation says so.
