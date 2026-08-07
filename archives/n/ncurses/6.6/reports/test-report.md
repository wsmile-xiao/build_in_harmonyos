# ncurses 6.6 test report

## Environment

- Target: HarmonyOS 6.0, arm64
- Device: one currently authorized device, recorded in the retained W3 closure
- Compiler: Clang 15 with libc++
- Conan: 2.29.1
- Candidate: exact final HEAD and tree recorded in the retained W3 closure and PR body

## Results

| Category | Passed | Total | Result |
|---|---:|---:|---|
| Upstream test/program entrypoints | 86 | 86 | PASS |
| Added consumer workflows | 8 | 8 | PASS |
| Internal consumer assertions | 27 | 27 | PASS |
| Negative configurations | 2 | 2 | PASS |

The complete upstream `make -j1 check` target passed. The eight added workflows are
the two direct consumers plus `ncursesw6-config` and five pkg-config consumers. All
six metadata linker traces selected only package-local static archives.

## Evidence

- Recipe revision: `3dcfd3b6d759300e8997800cefe8c61f`
- Package ID: `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
- The exact package revision, candidate HEAD/tree, authorized device, result archive,
  W3 log, `.ci-result.json` integrity value, and evidence-manifest hash are run-level
  values. They are recorded together in the retained exact-current W3 closure and PR
  body after the final candidate is immutable.
- Acceptance requires every retained evidence hash to match and the automatically
  generated `.ci-result.json` to report `exit_code=0`.
