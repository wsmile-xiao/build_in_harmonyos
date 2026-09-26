# DRAFT-ethash-1.1.0-lang-preflight-setuptools-cmake-binding

> 草稿（Path B 知识库扩展候选），由 ethash 1.1.0 适配产生，与同名 `.kv` 配对、逐字段一致。
> 仅为本地知识草稿，不代表任何 PR/Issue/commit/push/CI/review/merge/score 已成功。

## topic

lang-preflight（R47 协议 v0.8 附录 D）对"根目录存在 pyproject.toml/setup.py、但主体为
C/C++、Python 仅为非 pybind11 标记绑定层"的库误判 mixed 并自动写终态 env_unsupported；
正确做法是按 D.4-2 边界规则按主体语言判 cpp 继续适配，并附上游测试本地运行方案。

## error_signature

```text
任务标记 cpp，实测源码为 mixed（setuptools），无法按 cpp 适配——按协议 v0.8 §7.2 交平台语言迁移
detected_language: mixed
language_evidence.build_system: setuptools
```

## root_cause

`lang_detect.py` 判定链：

1. `_manifest_scan` 中 `pyproject.toml`/`setup.py` 存在即判 `("python", "setuptools")`，
   优先级高于同目录 `CMakeLists.txt`（c/cpp）。
2. `_detect_binding` 只识别 `pybind11`/`boost_python`/`Python_Additions`/
   `find_package(Python` 标记。ethash 的 `bindings/python` 用 `setup.py` 的 `build_ext`
   子进程调用 CMake 构建 C++ 库后封装（setuptools+CMake 风格），不命中绑定标记。
3. 于是 `binding_override` 不触发；冲突规则（manifest=python vs 源统计 cpp 占 88% ≥70%）
   触发 → `detected=mixed` → 自动写终态 `env_unsupported`。

## durable_solution

1. **人工复核优先**：lang-preflight 输出 mixed 且任务 lang 为 cpp 时，先按 R47 D.4-2
   （绑定包按源码主体判）采集证据：
   - `find $SRC -name "*.cpp" | wc -l` 与 `-name "*.py" | wc -l`；
   - 确认 .py 全部位于 `bindings/` 或为 `setup.py`/`pyproject.toml` 打包声明；
   - 主体 C/C++ ≥70% → 判 cpp 继续适配（c↔cpp 兼容族）。
2. **配方隔离**：conan 配方只打包 C/C++ 库，`package_type="library"`，不涉及绑定层。
3. **上游测试本地运行（github/Hunter 不可达时，C5）**：
   - `conan install --requires=gtest/1.17.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
   - 从 `conan cache path gtest/1.17.0` 的 `p/` 目录取头文件与 `libgtest.a`/`libgtest_main.a`；
   - 手动 `clang++` 链接上游测试源（`-DTEST_PROJECT_VERSION=...` 等按需传入）运行。

## impact

ethash 实测：判 cpp 继续后完成完整适配，上游测试 53/53 通过、HarmonyOS 专项测试 PASS、
conan-verify 全门禁 PASS，证明该判定正确；若采信工具终态 env_unsupported 将错误终止任务。

## recovery_condition

若后续工具版本扩展 `_detect_binding` 标记集（支持 setup.py build_ext→cmake、cffi 等），
或 manifest 优先级调整为"CMakeLists.txt 与 pyproject.toml 并存时按主体统计裁决"，本误判
消失；在修复前，执行端按本方案人工复核。

## evidence_references

- `archives/e/ethash/1.1.0/notes.md`（语言判定 R47 小节）
- `archives/e/ethash/1.1.0/reports/test-report.md`（53/53 + HarmonyOS 专项测试）
- 源文件统计：34 源文件 = cpp 27 + c 3 + python 4（bindings/python 与 setup.py）+ bash 1

## relations

- similar_to: R47（协议 v0.8 附录 D 边界规则 D.4-2）
- caused_by: lang_detect.py `_detect_binding` 标记集过窄
- conflicts_with: —
