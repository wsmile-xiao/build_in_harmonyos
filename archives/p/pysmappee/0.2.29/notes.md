# Adaptation Notes - pysmappee 0.2.29

## Overview
pysmappee is the official **Smappee** Python library wrapping the cloud/local REST API (v3) and MQTT interface.
Used as a dependency by the Home Assistant Smappee integration. Pure Python, no CLI binaries.

## Build System
- setuptools (`setup.py` + `setup.cfg` + `pyproject.toml`)
- Pure Python wheel (py3-none-any) — no C/C++ compilation
- Runtime deps: cachetools, paho-mqtt, pytz, requests, requests-oauthlib, schedule

## Build Process
1. Download PyPI sdist `pysmappee-0.2.29.tar.gz`
2. `pip install setuptools wheel` + runtime deps
3. `pip install --prefix=$staging` runtime deps, then `pip install --no-deps --prefix=$staging .`
4. Normalize to `lib/pythonX.Y/site-packages`
5. Build-phase smoke: helper/config/API symbols (upstream `test/` is empty)
6. test_package: import + helpers + construct API objects

## Upstream Tests
- **pysmappee 0.2.29 上游不提供任何自动化测试套件** (TEST_QUALITY_SPEC §3.3 上游无测试用例豁免路径)
  - sdist `test/` 目录仅含一个 0 字节 `__init__.py` (blob sha `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` = Git empty blob)
  - 无 `tests/` 目录、无 `noxfile.py` / `tox.ini` / `pytest.ini` / CI workflow
  - `setup.py` 用 `setuptools.find_packages(exclude=['test'])` 主动排除 test 包
  - `examples/example.py` 为 0 字节占位文件
- Recipe substitutes an offline smoke script in `build()` covering pure helpers and importable API symbols
- Cloud/MQTT integration against live Smappee services is out of scope (no device / no credentials)
- 完整证据 (GitHub API + PyPI sdist sha256) 见 `test_package/MANIFEST.yml::upstream_test_exemption` + `manifest.yaml::upstream_tests.evidence`

## Platform Compatibility
- No OHOS-specific source patches required
- Network-dependent API calls not exercised in this adaptation

## Conan Packaging
- Runtime deps vendored into package `site-packages` for a self-contained `PYTHONPATH`
- `package_info` exports `PYTHONPATH` only (library, no `bin/`, no `commands.json`)

## Verification (container, no device)
```
conan create archives/p/pysmappee/0.2.29 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  -c tools.build.cross_building:can_run=True \
  --build=pysmappee/*
```
Local CI: `CI_PACKAGES=archives/p/pysmappee/0.2.29 zsh ci/conan/build_and_test.sh`
- L0/L1/L4/L5 PASS (L2 skip: no bin/)
- Upstream tests: N/A (上游 0 tests, TEST_QUALITY_SPEC §3.3 豁免)
- Build-phase smoke: **10/10 PASS** (helper/config/API symbols)
- test_package: **26/26 PASS** (5 个函数覆盖 import + helpers + config + 构造 API 对象)
- L1e R34: sabotage lib/ → test fails (genuine dependency)

---

**编译结束**: 2026-07-31
**最终状态**: built (36/36 断言全部通过, 100% test pass rate, 0 patches)
