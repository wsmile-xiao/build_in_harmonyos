# VERIFY_RESULT — cfgv 3.4.0

## 1. 编译状态

**成功** ✅

`conan create archives/c/cfgv/3.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr` 退出码 0，产出纯 Python 包 cfgv.py。

---

## 2. 本地编译证据

完整日志：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.cfgv-verify.log`（155 行）

### 2.1 源码获取（日志第 59 行）

```
cfgv/3.4.0: Source https://github.com/asottile/cfgv/archive/refs/tags/v3.4.0.tar.gz retrieved from local download cache
```

源码 tarball（SHA256 `a8a4e4ad5618b6e65af563b14f46ccb1e45f5725c3b733d0ba15bb2a3b5bf9fd`）预置到 Conan 下载缓存 `core.sources:download_cache=/storage/Users/currentUser/builds/conan-src-cache`，`get()` 命中缓存，无 GitHub 网络访问。

### 2.2 本地 pip install 构建（日志第 63-88 行）

```
cfgv/3.4.0: Building from source
cfgv/3.4.0: RUN: /storage/Users/currentUser/usr/local/bin/python3 -m pip install . --prefix=.../b/build/package --no-deps
Building wheel for cfgv (pyproject.toml): started
Building wheel for cfgv (pyproject.toml): finished with status 'done'
Successfully installed cfgv-3.4.0
```

### 2.3 site-packages 产出（日志第 98-107 行）

```
cfgv/3.4.0: package(): Packaged 1 '.py' file: cfgv.py
cfgv/3.4.0: package(): Packaged 6 files
cfgv/3.4.0: cfgv installed: .../p/lib/python3.12/site-packages/cfgv.py
```

### 2.4 无远程下载确认

日志中 `Download (ohpcd)` / `Retrieving package ... from remote` 出现次数：**0**。`-nr` 标志确保完全本地构建。

---

## 3. conan create 结果

| 项目 | 值 |
|------|-----|
| 命令 | `conan create archives/c/cfgv/3.4.0 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=missing -nr` |
| exit code | **0** |
| Recipe revision | `245a406d1263b2494a401269f3780db8` |
| Package ID | `199b501a334fc7fce69568b5806901bfdcee316a` |
| conan 缓存 | `conan list "cfgv/*"` → Local Cache 中有 `cfgv/3.4.0` |

---

## 4. test_package 执行结果

test_package 分两层测试：先运行 7 个独立 smoke test 覆盖核心 API，再通过
桥接运行器原封不动执行上游 `tests/cfgv_test.py` 的 71 个测试函数（含 24 个
`@pytest.mark.parametrize` 展开，共 95 个子测试），满足规则 4 条件 2「上游
测试实际执行」。

### 4.1 Smoke test（test.sh 第 1-113 行）

```
=== cfgv 3.4.0 Smoke Test ===
Test 1: Module import + MISSING sentinel         → cfgv imported, MISSING sentinel OK
Test 2: ValidationError str                      → PASS
Test 3: validate Map/Required success            → PASS
Test 4: validate missing key raises ValidationError → PASS
Test 5: Optional default + apply/remove_defaults → PASS
Test 6: check_one_of rejection                   → PASS
Test 7: Array validate                           → PASS
=== All 7 tests PASSED ===
```

### 4.2 上游测试套件（run_upstream_tests.py + pytest_shim.py）

```
=== Upstream cfgv_test.py (rule-4 condition-2) ===

=== Upstream cfgv_test.py: 95/95 passed, 0 failed, 0 errored ===

=== Smoke 7/7 + Upstream 95/95 ALL PASSED ===
```

- 上游测试函数数：71（来源 `tests/cfgv_test.py`）
- `@pytest.mark.parametrize` 展开：24（16 个装饰器，部分多参数）
- 上游子测试总数：95
- 上游通过数：95（100%）
- 桥接实现：`pytest_shim.py`（纯 stdlib）注册为 `pytest` 模块，
  实现 `raises`/`fixture`/`mark.parametrize`；`run_upstream_tests.py`
  加载上游测试、展开 parametrize、解析 fixture，逐个调用 `test_*` 函数。
- 无需联网安装 pytest。

### 4.3 测试通过率汇总

| 层级 | 用例数 | 通过 | 通过率 | 失败 |
|------|--------|------|--------|------|
| Smoke test | 7 | 7 | 100% | 0 |
| 上游测试套件 | 95 | 95 | 100% | 0 |
| **合计** | **102** | **102** | **100%** | **0** |

---

## 5. 失败分析（过程中的两次修复）

| 问题 | 原因 | 修复 |
|------|------|------|
| GitHub 源码下载超时 | CI 无 GitHub 外网（ConnectTimeoutError） | tarball 预置到 Conan 下载缓存 `core.sources:download_cache`，`get()` 命中本地缓存 |
| `ModuleNotFoundError: No module named 'setuptools'` | 配方原用 `--no-build-isolation`，构建 Python（/usr/local/bin/python3）未预装 setuptools | 去掉 `--no-build-isolation`，让 pip 自动创建隔离环境并从配置的 pypi.cnb.cool 源下载构建依赖（同 pyparsing 方案） |

两者均非上游代码缺陷，属 CI 环境适配问题，修复后编译+测试全通过。

---

## 6. 是否需要打回重做

**否**。编译成功 ✅，本地编译（非远程下载）✅，测试通过率 100% ✅，缓存已建立 ✅。

---

## 7. 验证流程摘要

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 预置源码缓存 | tarball → conan-src-cache/s/（按 URL sha256 命名 + .json） | ✅ |
| 2. 本地构建 | `conan create ... --build=missing -nr` | exit 0，cfgv.py 产出 |
| 3. 测试验证 | conan create 内嵌 test_package | smoke 7/7 + 上游 95/95 PASS |
| 4. 缓存确认 | `conan list "cfgv/*"` | cfgv/3.4.0 in Local Cache |

完整日志路径：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.cfgv-verify.log`
