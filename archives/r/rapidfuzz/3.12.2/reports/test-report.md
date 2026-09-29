# rapidfuzz 3.12.2 测试报告

## 测试环境
- 平台: OpenHarmony PC (aarch64, OHOS 6.0)
- 编译器: clang/clang++ 15 (aarch64-linux-ohos)
- Python: 3.12.9 (Conan ohpcd/stable)
- 构建系统: CMake

## 构建测试

| 测试项 | 结果 | 说明 |
|--------|------|------|
| CMake 配置 | PASS | FindPython 成功检测 Python 3.12.9 |
| CMake 构建 | PASS | 5 个 CPython 扩展模块编译成功 |
| 产物完整性 | PASS | lib/ 包含所有 .so 和 .py 文件 |

## 功能测试（test_package）

| 测试项 | 结果 | 说明 |
|--------|------|------|
| C++ 实现来源断言 | PASS | `fuzz.ratio.__module__` / `Levenshtein.distance.__module__` 必须含 `_cpp`，防止 import 失败后静默退化成纯 Python 却报绿（CI #63465 教训，见 notes.md #15） |
| fuzz.ratio | PASS | ratio=96.55 |
| fuzz.partial_ratio | PASS | partial=100.00 |
| fuzz.token_set_ratio | PASS | token_set=100.00 |
| distance.Levenshtein.distance | PASS | lev=2 |
| distance.Hamming.distance | PASS | ham=0 |
| distance.Jaro.similarity | PASS | jaro=0.9444 |
| distance.JaroWinkler.similarity | PASS | jw=0.9611 |
| distance.Indel.distance | PASS | indel=3 |
| distance.LCSseq.distance | PASS | lcs=2 |
| distance.OSA.distance | PASS | osa=2 |
| distance.DamerauLevenshtein.distance | PASS | dl=2 |
| process.extract | PASS | best='hello' score=100.00 |
| utils.default_process | PASS | 'hello  world' (双空格为 upstream 行为) |

## 上游官方测试（pytest 套件）

上游 `tests/` 目录已逐字 vendor 进 `test_package/tests/`（23 个 `.py`），由
`test_package/conanfile.py` 的 `test()` 用 conan `python/3.12.9` 真实执行：

```text
python3.12 -m pytest test_package/tests/ -q --no-header --color=no \
    -p no:cacheprovider -o addopts=
```

| 统计口径 | 数值 | 说明 |
|----------|------|------|
| 上游测试文件 | 18 个 `test_*.py` | 另有 common.py x2、`__init__.py` x2、freezeTools/script.py |
| 上游测试函数 | **129** 个 `def test_` | 与评审 `grep -c '^\s*def test_'` 口径一致 |
| pytest 用例项 | **386** 个 | 参数化展开后的实际执行数 |
| CI 实测执行结果 | **384 passed / 0 failed / 2 skipped / 0 errors** | CI #63492（head `73a3e736`，conan python/3.12.9 aarch64），30.52s |
| 本机对照 | 386 passed / 0 skipped | CPython 3.12.10 + numpy 2.5.3 + pandas 3.0.6，差异仅因 CI 上 pandas 不可导入 |
| 2 项 skip 的原因 | pandas 门控 | `test_process.py` 的 `pd.NA` 与 `test_issue81` 用 `pytest.importorskip("pandas")`；pandas 需 `ctypes`，而 conan python 运行时的 `lib-dynload/_ctypes*.so` 报 `ffi_prep_closure_loc: symbol not found`（见 notes.md #16）。已显式 `requires("libffi/3.5.2")` 并确认其 lib/ 已在 LD_LIBRARY_PATH，根因在 python 配方侧，不在本包 |

按测试文件分布（测试函数数）：

| 文件 | 函数数 | 文件 | 函数数 |
|------|--------|------|--------|
| tests/test_fuzz.py | 20 | tests/distance/test_init.py | 14 |
| tests/test_utils.py | 1 | tests/distance/test_distance.py | 8 |
| tests/test_process.py | 32 | tests/distance/test_Levenshtein.py | 8 |
| tests/test_hypothesis.py | 21 | tests/distance/test_Hamming.py | 4 |
| tests/test_cpp_fallback.py | 0（模块级断言） | tests/distance/test_JaroWinkler.py | 4 |
| tests/test_pure_python_fallback.py | 0（模块级断言） | tests/distance/test_Indel.py | 3 |
| tests/distance/test_OSA.py | 5 | tests/distance/test_Jaro.py | 2 |
| tests/distance/test_LCSseq.py | 2 | tests/distance/test_Postfix.py | 2 |
| tests/distance/test_Prefix.py | 2 | tests/distance/test_DamerauLevenshtein.py | 1 |
| **合计** | | | **129** |

依赖处理（均为真实依赖，非跳过手段）：

- `pytest` + `hypothesis`：硬依赖（`test_hypothesis.py` 顶层 `import hypothesis`），用
  `pip install --target <TMPDIR>` 装纯 Python 包后经 `PYTHONPATH` 注入 conan python；
  安装后 `probe: import pytest, hypothesis` 通过才继续，否则 `ConanException` 直接失败。
- `numpy`：`requires("numpy/2.5.2")`（制品仓已发布，contourpy/1.2.1 同款裸引用），
  解锁 16 项 `pytest.importorskip("numpy")` 用例；导入失败时告警并如实跳过。
- `pandas`：制品仓无该包，尽力 `pip --target` 安装（CI #63492 实测安装成功）并 probe；
  probe 因 `_ctypes` 缺 `ffi_prep_closure_loc` 失败，故 2 项 `pd.NA` / `test_issue81`
  用例按**上游自身设计**由 `importorskip` 跳过，并写入 `HMBS_UPSTREAM_TEST_RESULT.note`，
  不做任何掩盖。根因定位见 notes.md #16（属 conan `python/3.12.9` 运行时侧）。

## 结论

- 构建状态: **通过**（CI #63492，head `73a3e736`）
- 功能测试（消费者视角）: **16/16 通过**，且 C++ 扩展真实生效（`fuzz.ratio` 来自 `rapidfuzz.fuzz_cpp`）
- 上游测试: **129 个测试函数 / 386 个 pytest 用例项在 CI 中真实执行**，384 通过、2 项 pandas 门控跳过（原因已定位并写明）
- 门禁: L0 pass、L1 pass、L1c 已识别上游官方测试、`conan create` passed
- 总体评估: **通过**

