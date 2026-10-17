# in-n-out

`in-n-out` is a typed, pure Python library for dependency injection and result processing. This archive adds its OpenHarmony PC Conan recipe for version 0.2.1. The recipe packages the upstream Python modules, `py.typed`, version metadata and BSD-3-Clause license, and exposes the package through Conan's `PYTHONPATH` run environment.

On OpenHarmony aarch64, the fixed H1-003 run passed Conan create, the package consumer's import and injection scenario, and the complete local W3 check. The separate H1-004 run of the unmodified upstream suite passed 122 collected tests with two collection-level skips. The source has no native compilation step. H1-003's overall `finish` exited 1 in later archive/summary/submit checks; its exact result is recorded in the contribution evidence and is not described as a successful finish. The package has not been uploaded, so this version is marked `built`.

The platform task tags this software as C++, while the fixed upstream source is Python. The adaptation does not change that task label or establish scoring eligibility.

- [Upstream source](https://github.com/pyapp-kit/in-n-out)
