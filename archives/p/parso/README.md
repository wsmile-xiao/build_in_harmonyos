# parso

`parso` is a Python parser that supports error recovery and round-trip parsing.

This archive packages the upstream `parso` Python modules and grammar data as a Conan dependency for OpenHarmony PC aarch64.

The Conan package exposes its module directory through `PYTHONPATH`; it has no native library or executable.

The version recipe and package consumer checks live under `0.8.7/`.

On OpenHarmony PC aarch64 with Python 3.12.9, H1-003 verified the clean source build and install, Conan package creation, and four consumer scenarios. The official finish command returned RC 1 because of framework-wide knowledge metadata and legacy submit-precheck findings; see `0.8.7/notes.md` and `0.8.7/reports/test-report.md` for the exact results and limits.
