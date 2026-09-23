# libdetourcrowd 1.6.0 HarmonyOS 适配笔记

## 上游与交付范围

- 上游：`recastnavigation/recastnavigation` v1.6.0
- 源码归档：`https://github.com/recastnavigation/recastnavigation/archive/refs/tags/v1.6.0.tar.gz`
- SHA-256：`d48ca0121962fa0639502c0f56c4e3ae72f98e55d88727225444f500775c0074`
- 许可证：Zlib
- Conan 包名/版本：`libdetourcrowd/1.6.0`
- 交付库：`libDetourCrowd.a`、`libDetour.a`
- CMake 目标：`libdetourcrowd::libdetourcrowd`
- 依赖：无外部依赖；Linux/OHOS 链接 `m`

上游工程在构建期完整编译 Recast、Detour、DetourCrowd、DetourTileCache、DebugUtils 及 Tests，
打包期只保留 DetourCrowd、Detour 和对应头文件，避免把不属于本拆分包的静态库及 CMake 导出文件带入交付物。

## HarmonyOS 适配

- Conan host profile：`os=OHOS`、`os.version=6.0`、`compiler=clang`、`compiler.version=15`、`compiler.libcxx=libc++`
- 已验证架构：`x86_64`
- 验证设备：HarmonyOS 6.0 PC 虚拟机，`hdc` 目标 `127.0.0.1:5555`
- DevEco 官方工具链默认选择 arm64，因此配方和消费者测试同时设置 `OHOS_ARCH` 及 `CMAKE_C_COMPILER_TARGET`、`CMAKE_CXX_COMPILER_TARGET`、`CMAKE_ASM_COMPILER_TARGET`。
- 鸿蒙特有测试：`test_ohos.cpp` 要求 `__OHOS__` 宏，写入并读取 `TMPDIR` 下的标记文件，再执行 `dtNavMesh`/`dtCrowd` 分配初始化；结果标记为 `OHOS-CHECK-OK`。

## 上游测试审计

- 上游 Catch2 测试目标：`Tests`
- CTest 注册项：1 个 `Tests`
- 功能用例：30 个（Detour 1 个，Recast 29 个）
- HarmonyOS x86_64 实际运行：43/43 通过，804 assertions；其中包含上游启用的 13 个 benchmark 用例。
- 上游修补：`Tests/Recast/Tests_Recast.cpp` 在 C++17 下将 `span == NULL` 改为 `span == nullptr`。

## Conan 验证结果

已执行：

```text
conan create archives/l/libdetourcrowd/1.6.0 \
  -pr:b=default \
  -pr:h=.superpowers/sdd/2026-09-21-libdetourcrowd-1.6.0/ohos-x86_64-local \
  -s:b arch=x86_64 --build=missing
```

结果：

- 上游测试：43 discovered / 43 executed / 43 passed
- 普通消费者测试：1/1 通过，输出 `CHECK-OK`
- 鸿蒙专属消费者测试：1/1 通过，输出 `OHOS-CHECK-OK`
- 两个消费者可执行文件均通过 hdc 发送到虚拟机并在设备端运行

## 产物说明

- `conanfile.py`：源码校验、CMake 构建、HDC 上游测试、裁剪和包元数据
- `conandata.yml`：官方源码及 SHA-256、补丁声明
- `patches/`：C++17 可移植性补丁
- `test_package/`：真实链接/API 消费者测试及 HarmonyOS 专属测试
- `manifest.yaml`：版本级构建与知识记录
