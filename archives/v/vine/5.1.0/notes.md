# Vine 5.1.0 adaptation notes

- Fixed source: PyPI `vine-5.1.0.tar.gz`, SHA-256 `8b62e981d35c41049211cf62a0a1242d8c1ee9bd15bb196ce38aefd6799e61e0`.
- The package is pure Python, has no runtime dependencies, and has no native `configure`/`make` build. Conan packages the upstream modules and exposes them through `PYTHONPATH`.
- The sole source patch changes `test_synchronization.py`'s barrier fixture hook from `setup()` to `setup_method()` for pytest 9. It changes no Vine runtime code, assertions, or test coverage. Exact patch SHA-256: `2e20d78cf2e1fd9f23bfcc3249206e75cf14e26712e45f49c7ef6c2f63721d76`.
- Local validation on Python 3.11.0rc2 / pytest 9.0.2 passed all 42 upstream tests.
- H1-004 applied the patch to the exact source successfully. G0 `clean-verify` then returned RC 1 at `./configure: No such file or directory`; this legacy configure/make step does not fit the pure-Python sdist. Keep the RC and `getcwd` warning disclosed; do not claim G0 passed or add a fake configure script.
- H1-004 W3 selected exactly the 11 candidate paths. Conan setup/build returned RC 0 and the OpenHarmony aarch64 package consumer checks passed 6/6.
- H1-004 Python had no pytest, so a separate fixed private test request was run once on H1. Its archived `pytest.stdout` reports 42 passed in 0.30s and stderr is empty. The outer runner then returned RC 1 while attempting bare `python3 --version` to write `result.json`; the pytest subprocess RC was not persisted. Report the observed output without claiming pytest RC 0 or runner success. The raw evidence is independently rechecked in `evidence/h1-pytest-v2/RESULT.md` and its 555-entry archive manifest.
- The platform task is labeled `cpp`, while the pinned source is Python. Keep the platform label unchanged and leave applicability to official review. The required software-level README/manifest paths conflict with PF9's five-segment check; do not remove them or bypass preflight.
- H1-003's earlier patch-hunk failure and `gen_summary` duplicate-key exception are historical framework findings. H1-004 corrected the source hunk and did not rerun full `finish`; no deprecated packaging/tar output or staging marker was fabricated.
