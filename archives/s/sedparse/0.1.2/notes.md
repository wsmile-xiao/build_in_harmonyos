# sedparse 0.1.2 HarmonyOS adaptation notes

## Scope and classification

This archive packages sedparse 0.1.2 (GNU sed parser translated from C to
Python, GPL-3.0-only). Upstream project is a single self-contained Python
module with no runtime dependencies and no compiled extensions. This is a
path A (basic adaptation): validate and install the module plus a POSIX CLI
wrapper, run the full upstream test suite during build.

- Upstream homepage: https://github.com/aureliojargas/sedparse
- Upstream tag: 0.1.2 (commit 568aea87e7649ce91ec43721d668b8d2c8ec65e2)
- Applicant: yinuoguo, team: 干

## W0 dependency check

PyPI metadata for sedparse 0.1.2 declares `requires_dist: null` (no runtime
dependencies). The recipe itself has no `requires()` or `tool_requires()`,
so there is no dependency chain to publish first.

## Source and build analysis

- Official source: GitHub tag tarball
  `https://github.com/aureliojargas/sedparse/archive/refs/tags/0.1.2.tar.gz`
- Source SHA256: `81b5c55da8104e54dfdd9ff43b06bfea040f9dabd9453ba44f10cc211389495d`
  (verified locally: 49247 bytes; matches the Debian orig tarball record for
  sedparse 0.1.2, 49.2 kB).
- Why the tag tarball instead of the PyPI sdist: the PyPI sdist
  (`sedparse-0.1.2.tar.gz`, 18510 bytes, sha256
  `1ac98faedb52230dc077b2e0e2363268c06fc76f5e130ff9d976b05328884506`)
  ships only `sedparse.py`/`setup.py` with no `tests/` directory, so the
  upstream suite cannot run from it. The GitHub tag is the same official
  upstream revision and contains the full `tests/` suite plus README.
- Payload: `sedparse.py` (single module, `__version__ = "0.1.2"`) with a
  `console_scripts` entry point `sedparse = sedparse:entrypoint`.
- No compilation needed. `build()` byte-compiles the module, checks the
  version string, then runs the upstream suite. `package()` copies
  `sedparse.py` to `lib/python/site-packages`, `LICENSE` to `licenses/`,
  and installs a POSIX `bin/sedparse` wrapper (`exec python3 -m sedparse`).
- `package_id()` is cleared: the payload is architecture independent.
- `package_type` is `application` because the package ships the `sedparse`
  CLI (`cpp_info.bindirs = ["bin"]`); the module path is additionally
  exported via `PYTHONPATH` and `SEDPARSE_PACKAGE_ROOT` runenv entries.
- A software-level `commands.json` declares the `sedparse` tool counterpart.

## Test strategy

Upstream test inventory (tag 0.1.2, `tests/` directory):

- `test_errors.py`: 1 method (error catalogue loop over 30+ error cases)
- `test_misc.py`: 4 methods (expression count, global cleanup, -e/-f mixing, unicode)
- `test_output.py`: 2 methods (to_dict/to_json diet and full forms)
- `test_parser.py`: 14 methods (addresses, blocks, commands, comments, gotchas)
- `test_repr.py`: 4 methods (repr of structs)
- `test_str.py`: 5 methods (str of structs)
- Total: 30 unittest methods (`python_def`口径: `def test_` count across
  `tests/test_*.py` = 1+4+2+14+4+5 = 30).
- Extra upstream gates also executed in `build()`: `python -m doctest README.md`
  and the `tests/reference.sed` -> JSON regeneration check against the
  committed `tests/reference.json`. The `make test` clitest targets
  (`test_cmdline.md`, README clitest) need a network download of the clitest
  runner and are not executed; the unittest suite plus doctest plus reference
  check cover the parser behaviour deterministically.
- Local evidence (Windows, Python 3.11.9, tag tarball): `python -m unittest
  discover -s tests -v` reports `Ran 30 tests` with `OK`, zero failures.

The recipe `_run_upstream_tests()` parses the verbose unittest output line by
line (`... ok` / `... FAIL` / `... ERROR` / `... skipped` / expected
failure / unexpected success) for passed/failed/skipped and the `Ran N tests`
line for discovered, checks `passed + failed == executed`,
`executed + skipped <= discovered` and `executed <= discovered`, requires the
verbose total to equal `Ran N`, then emits `HMBS_UPSTREAM_TEST_RESULT` with
`framework: unittest`. Doctest and reference mismatches fail the build with
the tail of the real output; no counts are guessed or patched.

The consumer test (`test_package/test_sedparse.py`, 12 checks) imports the
installed module (asserting the file lives under `SEDPARSE_PACKAGE_ROOT` and
the version is 0.1.2), exercises `compile_string` / `to_dict` / `to_json` /
`str()` / `ParseError`, runs the CLI via `python -m sedparse -e` and `-f`,
and parses a multi-command block. `test()` runs it under `conanrun` and emits
`HMBS_TEST_PACKAGE_RESULT` with `discovered: 12, passedCount: 12`.

## Verification result

Pending HMBS preflight on HarmonyOS aarch64 (rule4 gate). After the run,
fill the real `executed/passed` numbers into `.hmbs/pr-body.md`; no test
numbers are claimed until the device log exists.

## Commands

Single-package build on the device (maintainer runs preflight automatically):

```sh
conan create archives/s/sedparse/0.1.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
