# W0 dependency report: avr 2.3.2

- Date: 2026-08-27
- Package path: `archives/a/avr/2.3.2`
- Upstream source identified as AVR-LibC 2.3.2 from `avrdudes/avr-libc`.
- Issue: ignored per user instruction in this session.

## Dependency graph

Required build dependencies:

- `avr-binutils/2.43.1`
- `avr-gcc-bootstrap/14.2.0`
- `autoconf/2.72`
- `automake/1.18`

Optional test dependencies:

- `avrtest`
- `simulavr`

## Windows-side check

- Current PowerShell environment has no `conan` executable in `PATH`.
- `python -m conan --version` fails with `No module named conan`.
- Therefore registry queries and Conan graph validation were performed on the
  true device.

## True-device dependency check

Device: `10.62.220.52:2222`, user `currentUser`.

After the dependency merge, the latest-main shadow CI worktree
`/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/repo/build_in_harmonyos-main-20260827`
resolved the full build-requirement chain during `conan create`:

- `avr-binutils/2.43.1`
- `avr-gcc-bootstrap/14.2.0`
- `autoconf/2.72`
- `automake/1.18`
- transitive `m4/1.4.19`
- transitive `perl/5.42.2`

The previous L0/R36 blocker for `avr-gcc-bootstrap/14.2.0` is no longer current
for this package.

## Decision

Proceed only with the `avr/2.3.2` recipe and `test_package` in this PR. Do not
copy or modify dependency recipes. The single-library true-device shadow CI run
`shadow-ci-r17-fast-probe-silent-jobs14` completed successfully after the
dependency merge.
