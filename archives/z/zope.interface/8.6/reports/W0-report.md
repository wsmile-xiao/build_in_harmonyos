# zope.interface 8.6 W0 report

## Identity

- Library: `zope.interface`
- Version: `8.6`
- Classification: C-class dependency (bottom layer of lazr.config → lazr.delegates → zope.interface)
- Worktree branch: `feat/lazr.config-3.1`
- Upstream project: `https://github.com/zope/zope.interface`
- Build system: setuptools (pyproject.toml build-backend=setuptools.build_meta)

## Source

- PyPI sdist URL: `https://files.pythonhosted.org/packages/source/z/zope.interface/zope_interface-8.6.tar.gz`
- SHA256: `b40ef9b4873afb5d0dec02b8d2dfde1cf18c72337b60c99cb735961e0bac05c0`
  (matches the value published by the PyPI JSON API)
- Package shape: `src/zope/interface/` (PEP 420 namespace pkg `zope`, no __init__.py)
  plus an optional C extension `_zope_interface_coptimizations.c`

## Dependency result (W0, R36)

PyPI `requires_dist` for 8.6 declares no runtime dependencies — only
`docs`/`test`/`testing` extras (Sphinx, zope.event, zope.testing, coverage).
`requires_python` is `>=3.10`.

| dependency | published on ohpcd? | evidence |
|---|---|---|
| python/3.12.9 | YES | `conan download python/3.12.9 -r=ohpcd --only-recipe` → recipe revision d8eda770878152bea40b42db9f7024cd |
| zope.interface/8.6 (self) | NO | `conan download zope.interface/8.6 -r=ohpcd --only-recipe` → ERROR "system acceleration policy not enabled"（CNB 缺失配方响应）；HTTP GET `.../zope.interface/8.6/package/conanfile.py` → 404；local cache 0 命中。本任务新适配包 |

W0 result: PASS. No missing lower-level dependency blocks recipe preparation.

## Test inventory (R51)

The sdist includes `src/zope/interface/tests/` — 18 unittest modules
(adapter, declarations, interface, interfaces, registry, ro, verify, document,
exceptions, element, odd_declarations, sorting, compile_flags, advice, ...).
Pytest collected 1131 cases; under `PURE_PYTHON=1` (this package's deployment
mode) all 1131 pass, 0 skipped, 0 failed. See `test-report.md`.
