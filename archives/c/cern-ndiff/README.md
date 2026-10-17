# cern-ndiff

CERN 数值 diff 工具（MAD-X 的 `tools/numdiff` 子项目）：比较含浮点数的无格式文本文件，
支持绝对/相对容差模板，面向回归测试与数据校验。

## Compilation

- Version: 5.09.03（跟随 MAD-X tag）
- License: GPL-3.0-only（`licenses/LICENSE`）
- Dependencies: 无（纯 C99 + UNIX 下上游自链接的 libm）
- Build System: CMake（只构建 `tools/numdiff` 子目录，
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上古最低版本声明）

## OpenHarmony Adaptation

- Platform: OpenHarmony / HarmonyOS PC, aarch64 (os=OHOS profile)
- Compiler: Clang（C99，上游 CMakeLists 自带 `-std=c99`）
- 构建方式复刻 Homebrew cern-ndiff formula：
  `cmake -S tools/numdiff -B build && cmake --build build && cmake --install build`
- 无补丁，无平台相关代码（纯文本数值比较，R40 不适用）

## Status

- Built: 5.09.03 (this archive)
- Build Date: 2026-09-06
- Artifacts: `bin/ndiff`（`package_type = "application"`，无库文件）

## Testing

- Upstream tests: 3 个 CTest 用例（test-register、test-register-2、test-register-3），
  由 `build()` 内 `cmake.test()` 执行
- Consumer test: `test_package/test_ndiff.sh` — 真实运行打包后的 `ndiff` 二进制，
  3 项检查（存在可执行、容差内退出 0、超容差报告 `diffs detected`）
