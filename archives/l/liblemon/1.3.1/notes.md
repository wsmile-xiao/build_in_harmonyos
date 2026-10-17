# liblemon 1.3.1 适配笔记

## 编译环境
- 构建系统: CMake 4.1.2 + Ninja 1.12.1
- 编译日期: 2026-09-08
- 编译器: clang/clang++
- 目标: HarmonyOS PC arm64
- 状态: built and target-validated

## 编译步骤

Conan 使用 OHOS arm64 profile 生成 CMake toolchain，应用 5 个可重放补丁，
使用 Ninja 编译共享库、42 个上游测试与工具，对目标 ELF 签名后在真机
执行 CTest 和 Conan test_package。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |

| 1 | OHOS 上游 42 个测试启动失败 | ConanToolchain 在生成阶段覆盖配方子目录的 CMakeCache 设置，最终 shared-link rule 中仍无 SONAME | 在 recipe `generate()` 中通过 `CMakeToolchain.cache_variables` 同时绑定 `CMAKE_SHARED_LINKER_FLAGS` 和 `_RELEASE`，使选项在 toolchain 生成时进入 CMakeCache |
| 2 | OHOS package 阶段缺少 `LEMONConfig.cmake` | Conan 的 `settings.os` 为 `OHOS`，但目标 CMake 4.1.2 的 `CMAKE_SYSTEM_NAME` 实际为 `HarmonyOS`，仅匹配 `OHOS` 的源码条件不生效 | 将 SONAME 与 config 安装的 CMake 条件都扩展为 `OHOS` 或 `HarmonyOS` |
| 3 | 签名阶段找不到 `liblemon.so` | `OUTPUT_NAME liblemon` 又被 CMake 添加默认 `lib` 前缀，实际生成 `libliblemon.so` | 把 target `OUTPUT_NAME` 设为 `lemon`，使文件名和 SONAME 都为 `liblemon.so` |
| 4 | Consumer 链接器报 `unable to find library -lliblemon` | Conan `cpp_info.libs` 使用了已带 `lib` 前缀的 stem，链接器因此搜索 `libliblemon.so` | OHOS 下的 `_library_stem()` 返回 `lemon`，产生 `-llemon`并匹配实际 `liblemon.so` |
| 5 | Consumer 签名阶段报 `required OHOS tool was not found: readelf` | SDK 只提供 `llvm-readobj`，test_package 未同步主 recipe 的工具 fallback | test_package 先尝试 `readelf`，失败后改用 `readobj --sections`，签名前后均用同一入口核验 `.codesign` |
|---|------|------|----------|
| 1 | CMake 4 在配置阶段拒绝 `CMP0048 OLD` | CMake 4 已移除该策略的 OLD 行为，上游 1.3.1 固定请求 OLD | 在源码层改为受 `POLICY CMP0048` 保护的 NEW 行为，并重新验证完整 CTest 清单 |

## 源码修改

- `CMakeLists.txt`: 将 `CMP0048` 从已移除的 OLD 行为改为受版本保护的 NEW 行为。
- 补丁文件仅由 `refresh-patch --auto` 从 `.orig`/`.work` 双轨生成。

## 依赖版本

- 无外部 Conan 依赖
- OHOS SDK: 26.0.0.18
- Conan: 2.29.1

## 验证结果

```bash
conan create archives/l/liblemon/1.3.1 --build=liblemon/1.3.1 -pr:h <ohos-profile> -pr:b <ohos-profile>
# target result: upstream CTest 42/42, state 3/3, consumer 1/1 with 6 assertions
```

## 交付物

- `lib/liblemon.so`
- `include/lemon/`
- `lib/pkgconfig/lemon.pc`
- `share/lemon/cmake/LEMONConfig.cmake`
- `bin/lgf-gen`, `bin/dimacs-to-lgf`, `bin/dimacs-solver`

## 注意事项

CMake 目标身份为 `HarmonyOS`，Conan 配方身份为 `OHOS`。两者不能互相替代，
并且必须分别回读 CMakeCache、linker argv、DT_SONAME 和 consumer `-l` 名称。
