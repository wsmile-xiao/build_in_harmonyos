# Adaptation Notes - pyvolumio 0.1.5

## Overview
pyvolumio is a pure-Python async client for the [Volumio](https://volumio.org/)
REST API (`/api/v1/...`). Used by Home Assistant Volumio integration.
Library-only (no CLI binaries).

## Build System
- setuptools (`setup.py` + `setup.cfg`)
- Pure Python wheel (py3-none-any) — no C/C++ compilation
- Runtime deps: `aiohttp`

## Build Process
1. Download PyPI sdist `pyvolumio-0.1.5.tar.gz`
2. `pip install setuptools wheel`
3. Download pinned aiohttp + transitive deps from files.pythonhosted.org
   (conandata.yml `python_deps`); `AIOHTTP_NO_EXTENSIONS=1 pip install
   --no-deps --no-index --no-build-isolation --prefix=$staging <local files>`
   (bypass flaky pypi.org/simple; skip pkgconfig build-isolation fetch;
   OHOS has no linkable libpython → skip C ext)
4. `pip install --no-deps --ignore-installed --prefix=$staging .`
5. Normalize to `lib/pythonX.Y/site-packages`
6. Build-phase smoke: import / construct / `canonic_url`
7. test_package: construct + canonic_url + mock-session async API

## Upstream Tests
- PyPI sdist has **no** `tests/` / `test/` directory
- GitHub tag `v0.1.5` likewise ships no official pytest/unittest suite
- Recipe substitutes an offline smoke script in `build()` (TEST_QUALITY_SPEC §3.3 sanctioned exemption)
- Live Volumio device integration is out of scope (user requested no device verify)

### Double verification of upstream test absence (2026-07-31)

| 渠道 | 文件清单 | tests/ | pytest 配置 | CI 工作流 |
|------|---------|--------|------------|----------|
| PyPI sdist (`pyvolumio-0.1.5.tar.gz`, SHA256 `13249169451b46f3759622169de917b6ebd769865a899cee01f848a4c4bd6c69`) | LICENSE, MANIFEST.in, README.md, setup.py, pyvolumio/__init__.py, pyvolumio/volumio.py + egg-info | ❌ | ❌ | ❌ |
| GitHub codeload `refs/tags/v0.1.5` | .gitignore, LICENSE, MANIFEST.in, README.md, pyvolumio/__init__.py, pyvolumio/volumio.py, setup.py | ❌ | ❌ | ❌ |
| `setup.py` `find_packages(exclude=...)` | `['tests', '*.tests', '*.tests.*', 'tests.*']` 主动排除 | — | — | — |
| `MANIFEST.in` | 仅 `include README.md LICENSE` | — | — | — |

**结论**: **0** 个上游官方测试用例 — §3.3 sanctioned exemption 适用。

## Platform Compatibility
- No OHOS-specific source patches required
- Network-dependent Volumio calls exercised via mock aiohttp session only

## Conan Packaging
- Runtime dep `aiohttp` vendored into package `site-packages` for a self-contained `PYTHONPATH`
- `package_info` exports `PYTHONPATH` only (library, no `bin/`, no `commands.json`)

## Verification (container, no device)
```
conan create archives/p/pyvolumio/0.1.5 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  -c tools.build.cross_building:can_run=True \
  --build=pyvolumio/*
```

### 2026-08-04 复跑 (真机 HarmonyOS PC aarch64, 加入 4 个修复 commit 之后)
- **build smoke**: 13/13 asserts PASS — `PASS: pyvolumio upstream smoke (import/construct/canonic_url)`
- **test_package**: 28/28 asserts PASS — `All pyvolumio consumer tests passed (28/28 assertions)`
- **合计**: 41/41 = 100% (真机)
- 直链实测: 10/10 `files.pythonhosted.org` URL 在 conan `download()` 内置重试下成功 (其中 typing_extensions 首次 RST, 重试后 5/5 OK)
- aiohttp 3.14.3 sdist 成功构建: `AIOHTTP_NO_EXTENSIONS=1` + `--no-build-isolation` + `--no-deps` + `--no-index` 组合规避了 pkgconfig 拉取与 libpython 链接
- 真机证据: `uname -a = "HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 GNU/Linux"`；`platform.machine()=aarch64`；`platform.system()=HarmonyOS`；`platform.release()=HongMeng Kernel 1.12.0`；python3 = `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`；`/data/service/hnp/` 有 53 个 HNP 包 (含 hdc.org / ohos-sdk.org/ohos-sdk_26.0.0.18)
- 字节码: aiohttp 3.14.3 + pyvolumio 在 `p/lib/python3.12/site-packages/` 由 aarch64-ohos Python 3.12.9 加载,无 .so (`AIOHTTP_NO_EXTENSIONS=1` 生效)

### R5 实测环境范围声明 (2026-08-04)
- 本次 41/41 通过率为 **真机 HarmonyOS PC aarch64 (HongMeng Kernel 1.12.0)** 实测结果 (conan 2.29.1 / os=OHOS / arch=armv8 / clang 15 工具链经 /data/service/hnp/ 注入,python 3.12.9 是 aarch64 原生解释器)
- PR 之前的 3 次 CI 构建 (#12139 / #12182 / #12976) 全部失败，测试从未在 CI 实际运行
- 4 个修复 commit 尚未在 CI 再次触发，**CI run 仍为 pending** — 若 CI run 复现失败请如实记录失败用例与原因，不要把真机通过率挪作 CI 通过率
- 异步 API 用 `FakeSession/FakeResponse` mock 验证, 不发起真机 REST 请求; 此为离线可验证的边界

Local CI: `CI_PACKAGES=archives/p/pyvolumio/0.1.5 zsh ci/conan/build_and_test.sh`

## Dependencies
- Runtime: aiohttp 3.14.3 + transitive pure-Python wheels (vendored into
  package site-packages via `conandata.yml` `python_deps` direct URLs;
  aiohttp built with `AIOHTTP_NO_EXTENSIONS=1`)
- Conan package dependencies: none
- Build-only: setuptools, wheel

## CI Failure / Fix
### 2026-08-01 — libpython link
- **Symptom**: pip-building aiohttp sdist → `unable to find library -lpython3.12`
- **Fix**: `AIOHTTP_NO_EXTENSIONS=1` (pure-Python aiohttp, no ELF)
- **CI Issue**: #12139

### 2026-08-02 — empty PyPI simple index
- **Symptom**: `No matching distribution found for aiohttp` (`from versions: none`)
- **Cause**: Worker can reach `files.pythonhosted.org` (Conan source OK) but
  `pypi.org/simple` returns no versions for aiohttp
- **Fix**: Pin deps in `conandata.yml` `python_deps`, `download()` +
  `pip install --no-deps --no-index` from local files
- **CI Issue**: #12976

### 2026-08-02 — aiohttp build-isolation wants pkgconfig
- **Symptom**: under `--no-index`, pip fails installing build deps:
  `No matching distribution found for pkgconfig`
- **Cause**: aiohttp sdist lists `pkgconfig` in `[build-system] requires`;
  pure-Python (`AIOHTTP_NO_EXTENSIONS`) never imports it
- **Fix**: add `--no-build-isolation` (use already-installed setuptools)

### 2026-08-02 — PR diff download timeout (CI infra, not recipe)
- **CI Issue**: #12182
- **Status**: not addressable in recipe; depends on gitcode CI runner network state

---

**编译结束**: 2026-08-04 (post-fix 真机 HarmonyOS PC aarch64 复跑)
**最终状态**: built
**通过率（真机 HarmonyOS PC aarch64）**: 100% (41/41 = 13 build smoke + 28 consumer)
**通过率（OHOS CI run）**: PENDING — 3 次前次 CI 全部失败；4 个修复 commit 已落地但尚未再次触发 CI run
**豁免**: 0 (上游 0 测试,§3.3 sanctioned)
