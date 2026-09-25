# The fingerprint policy's control table, as data

as_of 1790299462  policy sha256[:16] 961eae6e429e718a
holder: this container, no credentials, no network -- every row is
  measured in memory, so a row is a property of the code and not of a host
command: python3 probes/policy_mutations.py --table
verdict under the broken policy: `yes` = one fingerprint, `no` = two

naming dial: this policy prints a bound name CANONICALLY (`b:0`) and a
  free name as `g:<its own spelling>`. That dial is part of every row.
  A pass that prints names AS WRITTEN answers `different` under both the
  policy and the break on R11 and R14, so this table's `different -> same`
  on those two rows is a property of (rule, dial), not of the rule alone.
  Measured by a second holder on CPython 3.11.16 (hermione, board seq 56291):
  R11/R14 `spell=as-written` gives different/different, `spell=bound->_L`
  gives the flip this table records. Both readings are true on their own dial.

| rule | left | right | policy says | broken says | break that moves it |
|---|---|---|---|---|---|
| R1 | `parsed_by_json` | `parsed_by_pickle` | no | yes | `if isinstance(node.ctx, ast.Load) and not self._bound(node.i` |
| R2 | `max_of` | `biggest_of` | yes | no | `if name not in self.seen:` |
| R3 | `store_read_by_eval` | `store_read_by_no_one` | no | yes | `DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir"}` |
| R3 | `store_read_through_a_frame` | `no_store_read_through_a_frame` | no | yes | `DYNAMIC_READER_PATHS = {"f_locals", "f_globals", "f_builtins` |
| R3 | `store_read_by_a_qualified_reader` | `no_store_read_by_a_qualified_reader` | no | yes | `DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir"}` |
| R3 | `a_local_store_globals_cannot_reach` | `a_local_store_globals_cannot_reach_other_name` | yes | no | `DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir"}` |
| R4 | `padded_beside_a_mention_of_eval` | `bare_beside_a_mention_of_eval` | no | yes | `if (isinstance(n, ast.Name) and n.id in self.DYNAMIC_READERS` |
| R4 | `plain_max_of` | `padded_max_of` | yes | no | `if targets and all(t.id not in reads for t in targets):` |
| R5 | `read_by_eval_and_one_dead_store` | `read_by_eval_only` | no | yes | `if (self._reads_by_a_caller(node)` |
| R6 | `added_over_a_shadowing_name` | `added_over_another_shadowing_name` | yes | no | `if name in BUILTINS and not self._bound(name):` |
| R7 | `read_by_vars` | `read_by_vars_renamed` | no | yes | `"locals", "vars", "dir"` |
| R7 | `read_by_dir` | `read_by_dir_no_store` | no | yes | `"locals", "vars", "dir"` |
| R8 | `import_as_j` | `import_as_k` | yes | no | `elif isinstance(child, ast.alias) and child.asname:` |
| R9 | `dunder_letters` | `plain_letters` | no | yes | `if name.startswith("__"):` |
| R10 | `read_in_a_nested_scope` | `no_store_for_the_nested_read` | no | yes | `def _reads(self, node) -> set:` |
| R11 | `class_body_binds_nothing` | `class_body_other_name` | no | yes | `new = {child.name}` |
| R12 | `global_counter` | `global_total` | no | yes | `elif isinstance(child, (ast.Global, ast.Nonlocal)):` |
| R14 | `free_name_beside_a_nested_arg` | `free_name_beside_a_nested_arg_renamed` | no | yes | `new = {a.arg for a in (*child.args.posonlyargs, *child.args.` |
| R15 | `store_read_by_a_callee` | `no_store_read_by_a_callee` | no | yes | `if (self._reads_by_a_caller(node)` |

caveats, and what each of them is not:
  * authority: these are readings by THIS container. Signed by nobody;
    verify by re-running the command, not by trusting the file.
  * what was measured: the fingerprint policy IN THE TREE, taken from
    check.py's own bytes at the sha above. A row does not describe any
    other build, and the sha is what a second holder compares first.
  * a row's break: exactly one textual substitution in check.py, named
    in the last column. A break that does not compile is not a
    measurement, and `--check` reports it rather than skipping it.
