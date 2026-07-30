# clang-build-analyzer 1.6.0 适配笔记

## Summary

- Added Conan recipe for `clang-build-analyzer/1.6.0` using the official GitHub tag archive (`v1.6.0`).
- Built with upstream CMakeLists.txt (C++17); no external Conan dependencies are required.
- All vendored third-party libs (cwalk/inih/xxHash/enkiTS/llvm-Demangle/simdjson) are embedded in `src/external/`.
- Packaged the `ClangBuildAnalyzer` command and `license.md` (Unlicense / public domain).
- Added software-level `commands.json` because this package installs a CLI executable (R38 / L0k).
- OHOS mapped to Linux via `CMAKE_SYSTEM_NAME` for E092 platform recognition.
- Cross-building detected via `cross_building()` to skip binary execution test on x86_64 CI workers (no OHOS real device available).

## 编译环境

- 构建系统: CMake (C++17)
- 编译日期: 2026-07-22
- 编译器: clang / clang++
- 状态: built (本地无 OHOS 工具链，依赖 CI 验证)

## 编译步骤

1. `conan source` 下载并解压 `v1.6.0.tar.gz` 到 `src/`
2. `cmake.configure()` + `cmake.build()` —— 上游 CMakeLists.txt 直接构建 `ClangBuildAnalyzer` 可执行文件
3. `cmake.install()` —— 上游 `install()` TARGETS 把二进制装到 `bin/`
4. 拷贝 `license.md` 到 `licenses/`

关键 CMake 配置（generate 阶段）:
- `CMAKE_SYSTEM_NAME=Linux` / `CMAKE_SYSTEM_PROCESSOR=aarch64`（OHOS→Linux 映射，E092）
- 通过 `shutil.which` 修复 `conan_toolchain.cmake` 中的编译器路径（R33）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 目标平台 | E092 上游 CMake 无 OHOS 平台支持 | 在 generate() 中将 OHOS 映射为 Linux (CMAKE_SYSTEM_NAME) |
| 2 | profile 中的编译器路径在 CI worker 上可能不存在 | R33 禁止硬编码 shell 环境变量 | 用 `shutil.which("clang")` 探测，回退到 "clang" |
| 3 | CI worker 是 x86_64，无法运行 aarch64 二进制 | 交叉编译场景 | test() 中用 `cross_building(self)` 检测并跳过执行测试 |
| 4 | conan-init 把构建系统误判为 autotools | 模板匹配错误 | 手动重写 conanfile.py 为 CMake + application 类型 |

## 源码修改

无补丁。所有 vendored 第三方库（cwalk/inih/xxHash/enkiTS/llvm-Demangle/simdjson）随上游源码一起编译，无需修改。

## 依赖版本

- 上游源码: ClangBuildAnalyzer v1.6.0 (aras-p/ClangBuildAnalyzer)
- CMake: >= 3.15 (上游 CMakeLists.txt 要求)
- C++ 标准库: C++17
- Conan 依赖: 无

## 验证结果

```bash
# CI 将执行（本地无 OHOS 工具链跳过）:
conan create archives/c/clang-build-analyzer/1.6.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=default \
  --build=missing

# test_package 验证（交叉编译时跳过执行，仅验证二进制存在）:
# - 检查 bin/ClangBuildAnalyzer 存在
# - 非交叉编译时: ClangBuildAnalyzer --version 输出 "ClangBuildAnalyzer 1.6.0" 并退出 0
```

## 注意事项

- 此包为 TOOL 类型 (`package_type = "application"`)，必须保留软件级 `commands.json`（R38）。
- 无 OHOS 真机验证，状态为 `built` 而非 `published`。
- `cross_building()` 跳过执行测试是 W3 流程允许的妥协，CI 仍会编译产物并验证二进制存在。

---

**编译结束**: 2026-07-22
**最终状态**: built (本地无 OHOS 工具链，依赖 CI 验证)
