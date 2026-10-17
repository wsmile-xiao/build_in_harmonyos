# VERIFY_RESULT — pluggy 1.5.0

## 1. 编译状态

**成功** ✅

`conan create archives/p/pluggy/1.5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr` 退出码 0，产出纯 Python 包 pluggy/。

---

## 2. 本地编译证据

完整日志：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.pluggy-verify.log`（156 行）

### 2.1 源码获取（日志第 59 行）

```
pluggy/1.5.0: Source https://files.pythonhosted.org/packages/source/p/pluggy/pluggy-1.5.0.tar.gz retrieved from local download cache
```

源码 sdist（SHA256 `2cffa88e94fdc978c4c574f15f9e59b7f4201d439195c3715ca9e2486f1d0cf1`）预置到 Conan 下载缓存 `core.sources:download_cache=/storage/Users/currentUser/builds/conan-src-cache`，`get()` 命中缓存，无 GitHub 网络访问。

### 2.2 本地 pip install 构建（日志第 63-88 行）

```
pluggy/1.5.0: Building from source
pluggy/1.5.0: RUN: /storage/Users/currentUser/usr/local/bin/python3 -m pip install . --prefix=.../b/build/package --no-deps
Building wheel for pluggy (pyproject.toml): started
Building wheel for pluggy (pyproject.toml): finished with status 'done'
Successfully installed pluggy-1.5.0
```

### 2.3 site-packages 产出（日志第 98-107 行）

```
pluggy/1.5.0: package(): Packaged 8 '.py' files
pluggy/1.5.0: package(): Packaged 1 '.typed' file: py.typed
pluggy/1.5.0: pluggy installed: .../p/lib/python3.12/site-packages/pluggy/
```

### 2.4 无远程下载确认

日志中 `Download (ohpcd)` / `Retrieving package ... from remote` 出现次数：**0**。`-nr` 标志确保完全本地构建。

---

## 3. conan create 结果

| 项目 | 值 |
|------|-----|
| 命令 | `conan create archives/p/pluggy/1.5.0 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=missing -nr` |
| exit code | **0** |
| Recipe revision | `0d5146a84cd550ce2544700107056d91` |
| Package ID | `199b501a334fc7fce69568b5806901bfdcee316a` |
| conan 缓存 | `conan list "pluggy/*"` → Local Cache 中有 `pluggy/1.5.0` |

---

## 4. test_package 执行结果

### 4.1 test.sh 7 个断言（日志第 135-156 行）

```
=== pluggy 1.5.0 Smoke Test ===
Test 1: Module import + version                    → pluggy imported, version OK: 1.5.0
Test 2: HookspecMarker/HookimplMarker exist        → PASS
Test 3: PluginManager register + hook call 1:N     → PASS [-1, 3]
Test 4: add_hookspecs + call_historic              → PASS ['before', 'after']
Test 5: hook result flattening                     → PASS
Test 6: tryfirst/trylast ordering                  → PASS ['first', 'middle', 'last']
Test 7: hook spec arg mismatch raises              → PASS
=== All 7 tests PASSED ===
```

### 4.2 测试通过率

| 指标 | 值 |
|------|------|
| 测试用例总数 | 7 |
| 通过用例数 | 7 |
| 通过率 | **100%** |
| 失败数 | 0 |

---

## 5. 失败分析（过程中的修正）

| 问题 | 原因 | 修复 |
|------|------|------|
| GitHub 源码下载超时 + sha256 校验失败 | CI 无 GitHub 外网；GitHub archive tarball 与 PyPI sdist 内容不同 | 改用 PyPI sdist URL（files.pythonhosted.org），tarball 预置到 Conan 下载缓存，get() 命中本地缓存 |
| `No module named setuptools`（首次尝试） | 配方原用 `--no-build-isolation`，构建 Python 未预装 setuptools/setuptools-scm | 去掉 `--no-build-isolation`，让 pip 隔离环境从 pypi.cnb.cool 下载构建依赖（同 pyparsing/cfgv 方案） |
| Test 4: `call_historic() got an unexpected keyword argument 'arg'` | 我 test.sh 的 API 用法错误——pluggy 1.5.0 签名是 `call_historic(result_callback=None, kwargs=None)` | 改为 `call_historic(kwargs={'arg': ...})` |
| Test 7: `PluginValidationError` 未在调用时捕获 | pluggy 1.5.0 在 `register()` 时即抛 PluginValidationError（`_verify_hook`），非 hook 调用时 | try/except 包住 `pm.register(MImpl())` |

均为测试脚本 API 用法问题与 CI 环境适配，非上游代码缺陷，修正后编译+测试全通过。

---

## 6. 是否需要打回重做

**否**。编译成功 ✅，本地编译（非远程下载）✅，测试通过率 100% ✅，缓存已建立 ✅。

---

## 7. 验证流程摘要

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 预置源码缓存 | PyPI sdist → conan-src-cache/s/（按 URL sha256 命名 + .json） | ✅ |
| 2. 本地构建 | `conan create ... --build=missing -nr` | exit 0，pluggy/ 产出 |
| 3. 测试验证 | conan create 内嵌 test_package | 7/7 PASS |
| 4. 缓存确认 | `conan list "pluggy/*"` | pluggy/1.5.0 in Local Cache |

完整日志路径：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.pluggy-verify.log`
