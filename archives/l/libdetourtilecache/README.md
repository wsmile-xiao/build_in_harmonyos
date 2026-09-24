# libdetourtilecache

## 简介

libdetourtilecache 是 Recast Navigation 的 DetourTileCache 导航网格瓦片缓存库，提供压缩瓦片、瓦片添加/删除以及临时障碍物生命周期管理等 API，适合需要动态更新导航网格的应用程序。

本归档只交付 `DetourTileCache` 静态库和对应头文件，不包含示例程序或命令行工具。CMake 消费者可使用目标 `libdetourtilecache::libdetourtilecache`。

## HarmonyOS 适配

- 使用上游 v1.6.0 的官方 CMake 工程构建，关闭 Demo 和 Examples，保留上游 Tests。
- 默认生成静态库；公开头文件依赖 `libdetour/1.6.0`，配方将该依赖的头文件和链接关系传递给消费者。
- OHOS 目标按 `os in (Linux, OHOS)` 处理数学库依赖，并使用 `ci/conan/profiles/ohos-aarch64` 中的 HarmonyOS 6.0 配置。
- 测试消费者在 `CMAKE_SYSTEM_NAME=OHOS` 时额外验证 `TMPDIR` 指向的目录可写，覆盖 HarmonyOS 运行时临时目录约束。
- Windows 主机上的 DevEco Studio Clang shell wrapper 不可直接作为 CMake 编译器执行；配方在交叉构建时自动切换到同一 SDK 的原生 `clang.exe`/`clang++.exe`，并设置 OHOS target 和 sysroot。

## 依赖

- `libdetour/1.6.0`

## 上游与许可证

- 上游仓库：https://github.com/recastnavigation/recastnavigation
- 许可证：Zlib

## 已编译版本

| 版本 | 日期 | 状态 |
|------|------|------|
| 1.6.0 | 2026-09-21 | built |
