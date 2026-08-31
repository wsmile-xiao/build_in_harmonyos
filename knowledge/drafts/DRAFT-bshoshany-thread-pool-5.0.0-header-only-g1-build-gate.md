# DRAFT-bshoshany-thread-pool-5.0.0-header-only-g1-build-gate

> Contributor: bshoshany-thread-pool-5.0.0 适配（pc3-32, R02 正式 Adapt）| Status: Draft | Updated: 2026-08-30
> Source: archives/b/bshoshany-thread-pool/5.0.0

## 现象

bshoshany-thread-pool 5.0.0 是单文件 header-only C++ 库（`include/BS_thread_pool.hpp`），
上游无 CMake/meson/autotools 项目（用脚本 `compile_cpp.py` 驱动测试）。R02 中运行
`ohc-run.py conan-verify` 时：

```text
❌ conanfile.py 缺少: build() 方法
❌ G1 失败，请先生成完整配方: ohc-run.py conan-init <软件> <版本>
```

配方已含 `source()` / `package()` / `package_info()` / `export_sources()`，
仅缺 `build()`，G1 完整性门禁即 FAIL 并阻止后续 G0-G5/L2/L4/L5 继续。

## 根因分析

conan-verify 的 **G1 配方完整性门禁**把 `build()` 方法列为 conanfile.py 的必填项。
header-only 无构建系统的 C++ 库按直觉"无需编译"常省略 `build()`，直接导致 G1 FAIL。
该门禁是结构检查，不看是否有实际编译步骤；只要方法缺失就判定配方不完整。

## 解决方案

header-only / 无构建系统库在 conanfile.py 中提供 **no-op `build()`**：

```python
def build(self):
    # Header-only library: no compilation step; headers are packaged as-is.
    # build() exists to satisfy G1 recipe-completeness gate (no-op for
    # single-header libraries without a CMake/meson/autotools project).
    pass
```

`package()` 照常用 `conan.tools.files.copy` 复制头文件到 `include/`。

## 验证证据

- 修复前：`conan-verify` 日志 `G1: FAIL`，`conanfile.py 缺少: build() 方法`。
- 修复后：`conan-verify` exit 0，`G1: PASS` → `G0 PASS`、`G2 conan create PASS`
  （含 test_package `./test_bs_thread_pool` → `PASS: BS::thread_pool ...`）、
  `G3 PASS`、`G4 PASS`、L2/L4/L5 通过。
- 完整日志：`archives/b/bshoshany-thread-pool/5.0.0/reports/conan-verify-report.md`
  （本轮 R02 生成，G1-G5 全 PASS）。

## 适用边界

- 仅适用 **header-only 无 CMake/meson/autotools 构建系统**的 C++ 库（如单头文件库、
  纯头文件模板库）。有 CMake 项目的库照常写真实 `build()`（CMake configure/build/test）。
- 与**数据/资源型包**（E241/E255/E281，无 C++ 编译、`settings=None`、`package_type` 不设）
  不同：header-only C++ 库保留 `settings` 与 `package_type = "header-library"`，
  只需补 no-op `build()` 即可过 G1。
- `apply_conandata_patches` 在 `source()` 中调用，不在 `build()` 里（header-only 无编译）。

## 恢复条件 / 查重差异

- 既有条目 E241/E255/E281：数据/资源型包（无 C++ 编译、settings=None），不覆盖
  header-only C++ 库需保留 settings + no-op build() 过 G1 的模式。
- E311：Conan source-folder 隔离（no_copy_source 语义），不同主题。
- DRAFT-conan-copy-keep-path-nesting：copy() 的 pattern/keep_path 嵌套，不同主题。
- 无同 stem 冲突草稿；本条目为 header-only 无 CMake 库配方完整性（G1 build() 门禁）
  的首个明确记录。
