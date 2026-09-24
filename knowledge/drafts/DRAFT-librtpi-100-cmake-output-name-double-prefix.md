# DRAFT-librtpi-100b — CMake 包装库的 lib 双前缀错位（Library not found in package）

- 日期：2026-09-19
- 软件：librtpi 1.0.0（真机单包实测发现）
- 设备：HarmonyOS PC（LAN 10.62.178.77）
- 配套条目：`DRAFT-librtpi-100-cmake-output-name-double-prefix.kv`

## 现象

库本体构建、打包全部成功（`package(): Packaged 1 '.a' file: liblibrtpi.a`），
test_package 的 `find_package(librtpi CONFIG REQUIRED)` 阶段报：

```
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'rtpi' not found in package.  If 'rtpi' is a system library,
  declare it with 'cpp_info.system_libs' property
```

## 根因

- 配方 CMakeLists 用 `add_library(librtpi ...)`（与上游库名一致）；
- Unix 下 CMake 自动给产物加 `lib` 前缀 → 实际文件 `liblibrtpi.a`；
- 配方 `cpp_info.libs = ["rtpi"]` → CMakeDeps 在包 `lib/` 找 `librtpi.a` → 不存在。

"目标名以 lib 开头"的 CMake 包装配方（autotools-only 上游转 CMake 包装是
本仓库常见模式）必然踩中。

## 处理建议

1. `set_target_properties(librtpi PROPERTIES OUTPUT_NAME rtpi)` —— 产物回归
   上游命名 `librtpi.a` / `librtpi.so.1`（librtpi 1.0.0 已采用，真机验证通过）。
2. 或目标直接叫 `rtpi`，但需与 `cmake_target_name` 声明核对，避免新错位。
3. 通用自查：`cpp_info.libs` 的每个名字 L，包 `lib/` 必须有 `libL.a` 或
   `libL.so*`；打包后 `ls` 核对一遍即可在消费阶段前拦住。
