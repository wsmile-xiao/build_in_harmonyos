# lazr.delegates 2.1.1 W0 report

## Identity

- Library: `lazr.delegates`
- Version: `2.1.1`
- Classification: B-class dependency (middle layer of lazr.config → lazr.delegates → zope.interface)
- Worktree branch: `feat/lazr.delegates-2.1.1`
- Upstream project: https://github.com/lazr-developers/lazr.delegates (Launchpad: https://launchpad.net/lazr.delegates)
- Build system: setuptools (setup.cfg, src layout, pure Python)

## Source

- PyPI sdist URL: `https://files.pythonhosted.org/packages/6c/55/08f7e5ddb2452f9006186721cdae501906049d847d9611cafca1855d592b/lazr_delegates-2.1.1.tar.gz`
- SHA256: `aeceb2616e51b73f327fbf12c4ec2b7d7670cb820bd5e4f6851215fb796c02dc`
  (matches the value published by the PyPI JSON API; verified during conan-init)
- Package shape: `src/lazr/delegates/` under the `lazr` namespace package
  (`src/lazr/__init__.py` present — pkg_resources try/except with pkgutil.extend_path
  fallback, PEP 420 compatible), pure Python — no C extension, no compiled artifacts.
  Also ships `src/lazr.delegates.egg-info/` (distribution metadata, required at import
  time because `__init__.py` calls `importlib.metadata.version("lazr.delegates")`).

## Dependency result (W0, R36)

PyPI `requires_dist` for 2.1.1: runtime only `zope.interface`
(docs/test extras: Sphinx, zope.testing, zope.testrunner). `requires_python` is `>=3.8`.

| dependency | published on ohpcd? | evidence |
|---|---|---|
| python/3.12.9 | YES | `conan download python/3.12.9 -r=ohpcd --only-recipe` → recipe revision d8eda770878152bea40b42db9f7024cd |
| zope.interface/8.6 | YES (chain precedent) | local cache recipe revision b8563506c264593a8652addcc1e214d8 + OHOS armv8 clang15 Release binary 6b129b068851896169fae42d399fa922d239ce8a；`conan download zope.interface/8.6 -r=ohpcd --only-recipe` 亦命中 |
| lazr.delegates/2.1.1 (self) | NO | `conan download lazr.delegates/2.1.1 -r=ohpcd --only-recipe` → ERROR "system acceleration policy not enabled"（CNB 缺失配方占位响应）。本任务新适配包 |

W0 result: PASS. Dependency zope.interface/8.6 resolved from local cache; no
missing lower-level dependency blocks recipe preparation.

## Test inventory (R51)

The sdist includes `src/lazr/delegates/tests/` — 3 unittest modules
(test_api.py, test_passthrough.py, test_docs.py) plus doctests from
`src/lazr/delegates/docs/*.rst`. zope.testrunner collected **8 tests**;
all 8 passed, 0 skipped (see `test-report.md`).
