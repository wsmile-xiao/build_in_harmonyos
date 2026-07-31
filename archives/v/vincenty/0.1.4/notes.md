# vincenty 0.1.4 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-07-29
- Compiler: N/A
- Status: built

## Source audit

- Upstream repository: https://github.com/maurycyp/vincenty
- Tag: `0.1.4`
- Tag commit: `16d4fedea411bb7d711520098f79bd225e78f427`
- Source SHA256: `74b3c7b9c2a587d28efb30cd137db4163186f666323e1ab8a5386ce90878b6ca`
- The standard GitHub tag archive is used because it includes the
  Unlicense file, while the PyPI source distribution omits that file.

## Packaging

1. Download and verify the official tag archive.
2. Apply declared Conan patches. This version has no patches.
3. Run the 9 doctest examples embedded in `vincenty/__init__.py`.
4. Copy the pure Python module into
   `lib/python/site-packages/vincenty`.
5. Copy the Unlicense text into the package.
6. Run the consumer test against the packaged module through Conan's run
   environment.

## Dependencies

- Runtime dependency: Python 2 or Python 3.
- Conan package dependencies: none.

## Validation

- Upstream command:
  `python -m doctest -v vincenty/__init__.py`
- Consumer command:
  `python test_vincenty.py`
- The consumer test verifies import provenance and 13 API or numeric
  behaviours, for 14 assertions in total.
- Windows native Conan 2.29.1 / Python 3.14.5:
  - Upstream doctests: 9/9 passed.
  - Packaged consumer assertions: 14/14 passed.
- WSL Linux with the repository `ohos-aarch64` profile used for both host and
  build, OHOS-adapted Conan 2.29.1 / Python 3.10.20:
  - Forced source build, source hash verification, packaging, and test_package
    all passed.
  - Upstream doctests: 9/9 passed.
  - Packaged consumer assertions: 14/14 passed.
  - Repository `conan-verify`: PASS.
  - W3 local CI: L0 pass, L1 pass, L4 pass, L5 pass; L2 skipped because this is
    a library without a `bin/` directory.
  - R34 destructive negative test passed: moving the packaged `lib/` directory
    away made the consumer test fail, proving it uses the packaged artifact.

## Platform boundary

- The package contains architecture-independent Python source only.
- OpenHarmony execution still requires a compatible Python runtime.
- Physical OpenHarmony device execution was not performed locally.
- The anonymous Conan remote returned
  `system acceleration policy not enabled` during the W0 occupancy query, so
  remote version availability could not be independently confirmed.
---

**编译结束**: 2026-07-29 23:02
**最终状态**: built
