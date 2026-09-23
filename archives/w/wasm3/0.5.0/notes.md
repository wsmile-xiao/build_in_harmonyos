# wasm3 0.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

wasm3 0.5.0 是纯 C 的 WebAssembly 解释器（WASM interpreter），无第三方依赖。

1. 源码: 官方 release tarball `https://github.com/wasm3/wasm3/archive/refs/tags/v0.5.0.tar.gz`（sha256 b778dd72…，与 v0.5.0 标签一致）
2. CMake 配置（本地验证）:
   ```bash
   cmake -S . -B build-native -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DBUILD_WASI=simple -DBUILD_NATIVE=OFF
   make -j2
   ```
3. Conan 配方（ohos-aarch64 profile, conan create 通过）:
   - conanfile.py: CMakeToolchain + CMake，`cmake.configure(variables={"BUILD_WASI": "simple", "BUILD_NATIVE": "OFF"})`
   - 产物: libm3.a 静态库 + wasm3 可执行文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 拉取 uvwasi 失败（github.com 443 超时） | wasm3 默认 BUILD_WASI=uvwasi，configure 阶段 FetchContent 从 github 克隆外部依赖 | `-DBUILD_WASI=simple` 使用内置 SimpleWASI，无外部依赖 |
| 2 | toolchain 里设 BUILD_WASI 无效，CMakeCache 仍为 uvwasi | wasm3 的 CMakeLists 在 `project()` **之前**就 `set(BUILD_WASI "uvwasi" CACHE ...)`，conan toolchain CACHE 变量加载时机晚于该赋值 | 改用 `cmake.configure(variables={"BUILD_WASI": "simple"})` 以 `-D` 命令行形式强制传入（-D 优先于源码内 CACHE 默认值） |
| 3 | 上游无 `make install` 目标（cmake.install 无输出） | wasm3 顶层 CMakeLists 未定义 install() 规则 | 在 package() 中手动 `copy("*.a")` 到 lib/、`copy("*.h")` 到 include/ |
| 4 | m3_test 链接缺 m3_NewModule 等符号 | 扩展 API（m3_NewModule/m3_InjectFunction/m3_GetFunctionByIndex）定义在 `source/extensions/m3_extensions.c`，不在默认 libm3.a 目标内 | 测试编译时把 extensions 源文件一并编译链接 |
| 5 | lang-preflight 误判 mixed（gradle/maven） | wasm3 仓库 `platforms/android` 辅助 demo 目录含 build.gradle，`_manifest_scan` 在全树任意位置命中即判 java 与 C 统计冲突 → mixed | 按 R47 边界规则"辅助脚本不算主体"，排除辅助平台目录后正确判定 cpp（与任务语言兼容） |

## 源码修改

无（0 补丁）。

## 依赖版本

无第三方依赖（仅 libc/libm）。

## 验证结果

- `wasm3 --version` → "Wasm3 v0.5.0 on arm64-v8a" ✅
- 自托管测试: `wasm3 test/self-hosting/wasm3-fib.wasm` → "Result: 832040" ✅
- 内部单元测试: `m3_test`（signatures/codepages/extensions/multireturn 全部通过）✅
- conan create（ohos-aarch64）: G0-G4 + L2/L4/L5 全部通过，产物 libm3.a ✅
- finish W3 本地 CI: exit_code=0（.ci-result.json log_sha256 09ef8aa9…）✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libm3.a | ~259KB | 静态库（含扩展 API） |
| include/*.h | — | wasm3 公开头文件 |

## 注意事项

- BUILD_WASI 必须用 -D 强制（源码 CACHE 默认在 project() 前设置，toolchain 注入无效）
- test/ 目录下的 run-spec-test.py 需要外部 webassembly spec 测试套件，未纳入本次验证
---

**编译结束**: 2026-09-08 22:23
**最终状态**: built
