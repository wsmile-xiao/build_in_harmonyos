# mts-esp 0.0-git20230110.9df9a9c 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos)
- 状态: built

## 编译步骤

上游快照不含构建文件。适配补丁新增最小 CMake 工程，将 Client 与 Master 两个 C++ 实现编译为位置无关的静态 `libMTS.a`，并安装两个公共头文件。Conan 以 OpenHarmony AArch64 工具链执行 configure、build、install 和 test_package。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无法直接配置构建 | 快照仅提供可嵌入的 `.cpp`/`.h`，没有 Makefile 或 CMakeLists.txt | 新增只构建、安装公开包装层的 CMakeLists.txt，与 Debian 的单一静态库布局一致 |
| 2 | HarmonyOS 应用无法使用传统提供者路径 | 上游仅尝试 macOS 路径及 `/usr/local/lib/libMTS.so` | 客户端与主控端先按 `libMTS.so` SONAME 加载，使系统动态加载器按应用/HNP 搜索路径解析，再保留原路径回退 |
| 3 | 上游没有自动化测试 | 官方提交不含 tests、CTest 或 check 目标 | 新增 9 个消费者测试，覆盖本地调音、SysEx、离线安全和 HarmonyOS 动态提供者发现 |

## 源码修改

- `0001-CMakeLists.txt.patch`: 新增静态库构建、PIC、头文件与归档安装规则。
- `0002-Client-libMTSClient.cpp.patch`: 客户端优先按 SONAME 搜索提供者。
- `0003-Master-libMTSMaster.cpp.patch`: 主控端优先按 SONAME 搜索提供者。

## 依赖版本

- 无第三方 Conan 依赖。
- 系统动态加载接口: `libdl`。

## 验证结果

```text
OpenHarmony AArch64 配方构建与安装: PASS
test_package 直接执行: 9/9 PASS
上游测试: 0/0（上游无测试套件）
新增消费者测试: 9/9 PASS（含 1 个 HarmonyOS 特有测试）
```

## 注意事项

- 本包提供公开 Client/Master 包装层；运行时的调音提供者由宿主应用以 `libMTS.so` 提供。
- 未连接提供者时，客户端按上游设计继续提供本地 12-TET 和 MTS SysEx 调音。
