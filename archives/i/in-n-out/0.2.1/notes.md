# in-n-out 0.2.1 adaptation candidate

## Source and scope

- Fixed PyPI sdist: 26,026 bytes; SHA-256 `43cde2b7de981d41a6d70618a2b7bd989481095922a53ead4dc75f2bbd5dffea`.
- The source is a typed pure-Python library with no runtime dependencies. The Conan package includes the `src/in_n_out` Python modules, `py.typed`, BSD-3-Clause license, and upstream `PKG-INFO` as dist-info metadata so `__version__` resolves to `0.2.1`. The license is included both in Conan's `licenses/` directory and under `dist-info/licenses/` as declared by the upstream metadata; upstream tests and documentation are not packaged.
- The contest task is tagged `cpp` while the source project is Python. Disclose the mismatch; eligibility and score are not established by this adaptation.
- The unmodified upstream `tests/` directory contains nine `test_*.py` files and registers 122 pytest items. On the Windows host, 121/122 passed, one collected test skipped because optional `toolz` was absent, and two collection-level items skipped. This host result is separate from the target result below.
- The test package `MANIFEST.yml` records the unmodified upstream pytest suite and the package consumer separately; skips remain visible and are not counted as passes.

## OpenHarmony target validation

On 2026-10-01, the H1-003 run used official framework base `255e5069639b3be244f4988c966a5120bd5608f2` and the original seven candidate files. Its local validation commit was `e62b4d437e0707ea02aa98b3eebe91b40ec3f13b`. Conan G1/G2/G3 and `conan create` passed. The actual `test_package` imported from the packaged Conan path and completed one dependency-injection consumer scenario with eight assertions. W3 checked the seven candidate paths in `prdiff` mode and recorded `.ci-result.json` with `exit_code=0`.

On 2026-10-01, separate H1-004 ran the unmodified upstream pytest suite on OpenHarmony aarch64 / Python 3.12.9 using the same fixed sdist and private offline Python test dependencies. The target collected 122 items and reported **122 passed, 0 failed, 2 collection-level skipped, pytest RC0**. `tests/test_benchmarks.py` requires an explicit `--benchmark` option; `tests/typesafety/__init__.py` marks the pytest-mypy plugin checks flaky. Neither skip is counted as a pass. All 23 extracted original source files matched the fixed sdist before and after testing. The test dependencies were isolated to that run; they are not runtime requirements of the Conan package. H1-004 did not rerun Conan or W3.

The H1-003 overall `finish` returned 1 after W3. `finalize-archive` returned 2, reporting a missing software-level README alongside legacy packaging/release/debug artifacts and a notes warning; `gen_summary` raised `'str' object has no attribute 'append'`; the legacy submit preflight asked for test-report, packaging and staging material. The README is supplied at the software level in this contribution. Deprecated packaging/tar/staging artifacts and state markers are not fabricated. The original H1-003 finish failure remains recorded; W3 and the package consumer retain their own passing results. H1-003 itself did not run upstream pytest because its system Python lacked it; H1-004 supplied the separate target run.

This version is `built`: Conan validation succeeded and no package upload has occurred. Official PR CI, AI review, merge and scoring are separate pending events.
