# multipledispatch 1.0.0 adaptation notes

## Scope

- Package: `multipledispatch`
- Version: `1.0.0`
- Language: Python
- Branch: `feat/multipledispatch-1.0.0`
- Worktree: `D:\harmonyos\worktrees\multipledispatch`
- Upstream repository: <https://github.com/mrocklin/multipledispatch>
- Source archive: PyPI sdist, pinned by SHA256
- License: BSD-3-Clause
- Adaptation path: B（贡献创新）
- Related knowledge drafts:
  - `knowledge/drafts/DRAFT-multipledispatch-upstream-consumer-test-boundary.md`
  - `knowledge/drafts/DRAFT-multipledispatch-python-require-conan-staging.md`
  - `knowledge/drafts/DRAFT-multipledispatch-version-metadata-reconciliation.md`

## Dependency and toolchain analysis

- Runtime dependencies: none.
- Native dependencies: none.
- Build system: setuptools via `setup.py`.
- Upstream build metadata uses `setuptools`; upstream CI also uses `pytest`
  and `pytest-benchmark` for development tests.
- The Conan target Python does not provide `setuptools.build_meta`, so the
  recipe intentionally uses Python standard-library file copying rather than
  invoking pip/setuptools.
- The PyPI sdist does not contain the upstream `tests/` directory. The official
  1.0.0 tag at commit
  `f91547f9936e5ed368ab151c1060ee7cfe67ab79` contains six pytest files and
  62 collected cases.
- Those six official test files are included as build-only `upstream_tests/`
  sources. The build runs all 62 functional cases through
  `run_upstream_tests.py`, which does not require pytest in the minimal target
  Python. The benchmark tests are exercised functionally; timing metrics are
  not claimed by the portable runner.

## Packaging decision

- Use `package_type = "python-require"`.
- Copy the package and the sdist `egg-info` metadata into a build-local
  staging directory.
- Export the staged package and metadata under
  `lib/python3.12/site-packages`.
- Expose that directory through Conan `PYTHONPATH`.
- Do not add any Conan requirements.

## Version metadata note

The installed module's `multipledispatch.__version__` is `0.6.0` in the
upstream 1.0.0 source package, while `setup.py` and PyPI metadata identify the
distribution as `1.0.0`. This is retained as upstream behavior and is recorded
for consumers.

## Verification

- Source SHA256 verified:
  `5C839915465C68206C3E9C473357908216C28383B425361E5D144594BF85A7E0`.
- `conan inspect` passed with `python-require` and no requirements.
- `conan create` passed with a Linux host profile on the local Windows build
  machine. Source download, build, package generation, and package creation
  all completed.
- Conan skipped the automatic test execution because the local build context
  is Windows while the simulated host context is Linux.
- The same consumer test was run directly against the generated Conan package
  with its packaged `site-packages` and passed.
- Consumer assertions covered distribution metadata, the upstream module
  version note, integer dispatch, string dispatch, explicit `Dispatcher.add`,
  and an unregistered signature failure.
- Official pytest run against the 1.0.0 tag test files and the packaged source:
  62/62 passed, including the four benchmark-oriented functional cases.
  Portable Conan build runner: 62/62 passed. Consumer test: 6/6 assertions
  passed.

## Status

Local W0-W4 preparation is complete and this revision is submitted as a
Path B knowledge contribution. No OHOS aarch64 device or shadow CI run was
performed in this round.

## Follow-up

After local verification, run the OHOS profile command:

```text
conan create . --user=ohpcd --channel=stable ^
  -pr:h=%USERPROFILE%\.conan2\profiles\ohos ^
  -pr:b=%USERPROFILE%\.conan2\profiles\ohos ^
  --build=missing
```

No true-device test is scheduled in this round.
