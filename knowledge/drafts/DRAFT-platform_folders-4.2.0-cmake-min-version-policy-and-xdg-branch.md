# DRAFT-platform_folders-4.2.0-cmake-min-version-policy-and-xdg-branch

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: platform_folders 4.2.0 HarmonyOS PC 适配（CMake，零依赖 C++11 库）

## 现象（CMake 平台/策略坑）

platform_folders（C++11 特殊目录查询库，单 .cpp+单头，零第三方依赖）迁 OHOS 时：

| # | 坑 | 直接现象 |
|---|---|---|
| 1 | 上游 `cmake_minimum_required(VERSION 3.1)`，**CMake 4 拒绝 <3.5 项目** | configure 报兼容/策略错误 |
| 2 | Conan `CMakeToolchain` 默认拿错 host 系统 | 需 `generic_system` 显式 `cmake_system_name=OHOS`、`cmake_system_processor=aarch64` |
| 3 | 库按 OS 平台宏（Windows/Apple）分流 | OHOS 既非 Windows 也非 Apple → 必须确认落入 Linux/XDG 分支（读 HOME/XDG_*、user-dirs.dirs），否则目录语义错 |
| 4 | 测试依赖真实 HOME | 断言"返回串非空"；空 HOME/root 下失真 |

## 修复（配方侧，零上游改动）

1. **策略注入**：generate() `CMAKE_POLICY_VERSION_MINIMUM=3.5`（只抬策略底线，不改上游基线）。
2. **系统映射**：`generic_system` 显式 `cmake_system_name=OHOS`、`cmake_system_processor=aarch64`
   （本仓 gcem 同款）；`BUILD_SHARED_LIBS/PLATFORMFOLDERS_*` 按 option 对齐。
3. **分支核验**：OHOS 属非 Windows/非 Apple → 确认走 XDG/Linux 实现；测试仅断言非空，
   依赖 worker 以 currentUser 运行（conan 缓存于其 HOME）→ `cmake.test()` 实跑 16 个
   上游 ctest 作 L1（integration/internalTest 等全绿）。
4. **导出对齐**：静态库 install(EXPORT) NAMESPACE `sago::`；`package_info` 用
   `set_property(cmake_file_name/cmake_target_name)` 对齐，test_package 真实链接调用
   （20 checks）。

## 验证证据

- conan create（OHOS aarch64 CI）在 CMake 4 下不再报 <3.5 兼容错。
- build() 内 `cmake.test()` 实跑 16/16 上游 ctest。
- test_package 输出 `platform_folders 4.2.0 consumer: ALL OK (20 checks)`。

## 作用域与维护条件

- 作用域：任何上游 `cmake_minimum_required < 3.5` 的旧 CMake 项目在新 CMake/CMake4 环境
  configure 失败；任何按 OS 宏分流的目录/文件系统库迁 OHOS（确认 Linux 分支语义）；
  依赖真实 HOME 的测试的可执行性判断。
- 上游若抬高最小版本或改策略，第 1 条可简化。
- 禁忌：不得谎报 cmake.test 结果/裁剪上游 ctest；不得 sed 改上游 CMakeLists 基线；
  不得在空 HOME/root 假设下跑该类测试。
