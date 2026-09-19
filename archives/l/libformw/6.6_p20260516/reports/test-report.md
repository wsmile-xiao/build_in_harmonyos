# libformw 6.6_p20260516 test report

## Environment

- Target: HarmonyOS 6.0, arm64
- Device: one currently authorized device, recorded in the retained W3 closure
- Compiler: Clang 15 with libc++
- Conan: 2.29.1
- Candidate: exact final HEAD and tree recorded in the retained W3 closure and PR body

## Results

| Category | Passed | Total | Result |
|---|---:|---:|---|
| Upstream test/program entrypoints (build + inventory verified, full `make -j1 check`) | 86 | 86 | PASS |
| Added consumer workflows | 1 | 1 | PASS |
| Internal consumer assertions | 13 | 13 | PASS |
| Negative configurations (L1e destructive sabotage) | 1 | 1 | PASS |

The complete upstream `make -j1 check` target passed. The upstream `test/`
programs are interactive demos: upstream `check` verifies their build and
inventory ("The test-programs are interactive") without executing them
headless — the same scope as the merged ncurses/6.6 delivery. The added
consumer workflow is the `test_package` program `test_form_api`, which builds
a minimal screen via `newterm("dumb")` (TERMINFO from the ncurses/6.6
dependency's conanrun environment), then exercises the form public API:
`new_field`, `set_field_buffer`/`field_buffer` content round-trip,
`set_field_status`/`field_status`, `new_form` (NULL-terminated field array),
`field_count`, `set_current_field`/`current_field`, `free_form`, `free_field`.

Gates recorded by the verification copy this round: G0 knowledge pre-query,
G1 recipe completeness, G2 `conan create`, G3 system-library isolation (R26),
G4 artifact completeness — all PASS; L4 static patch scan PASS (no platform
macros in patches/); L5 artifact baseline PASS; L1e destructive negative test
PASS (moving `lib/` and `include/` away breaks the consumer — the test
genuinely depends on the packaged artifacts).

## Evidence

- Recipe revision: `836ed20eb2b7f8171a086b454ced8b8f`
- Package ID: `044971e9092dd6608b4c967bac722a276b7cc911`
- The exact package revision, candidate HEAD/tree, authorized device, result
  archive, `.ci-result.json` integrity value, W3 log, and evidence-manifest
  hash are run-level values. They are recorded together in the retained
  exact-current W3 closure and PR body after the final candidate is immutable.
- Acceptance requires every retained evidence hash to match and the
  automatically generated `.ci-result.json` to report `exit_code=0`.
