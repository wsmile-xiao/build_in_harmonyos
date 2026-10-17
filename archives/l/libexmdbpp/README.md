# libexmdbpp

> grommunio 的 exmdb 线协议 C++ 实现

| 项目 | 信息 |
|------|------|
| 上游仓库 | https://github.com/grommunio/libexmdbpp |
| 许可证 | AGPL-3.0-or-later |
| 语言 | C++17 |
| 构建系统 | CMake (>= 3.14) |
| 产物类型 | 共享库（无命令行工具，无需 `commands.json`） |
| 适配状态 | 1.11 → published（HarmonyOS PC aarch64） |

## 简介

`libexmdbpp` 是继 Gromox 的 `exmdb_client` 之后的第二套 exmdb 线协议 C++ 实现，供 grommunio 使用。
它提供构建、序列化与解析 exmdb RPC 请求/响应的 C++ API：

- `exmdbpp::ExmdbClient` / `exmdbpp::queries::ExmdbQueries` — 与 exmdb_provider 建链并执行 RPC 调用
- `exmdbpp::requests::*` — 各类 RPC 请求（`GetStoreProperties`、`LoadContentTable` …）的序列化
- `exmdbpp::structures::*` — `TaggedPropval`、`Restriction`、`GUID`、`SizedXID` 等 exmdb 数据结构
- `exmdbpp::IOBuffer` — 线协议的二进制读写缓冲（默认小端）
- `exmdbpp::util::*` — GC 值 / EntryID / FILETIME 时间换算工具

上游额外提供基于 pybind11 的 Python 绑定 `pyexmdb`（可选构建），本次适配范围内未启用。

## HarmonyOS PC (OHOS aarch64) 适配要点

| 项 | 说明 |
|----|------|
| 依赖 | 无第三方依赖，仅需 C++17 标准库 |
| 源码补丁 | 1 个（`ulong` → `unsigned long`，musl 未定义 glibc 的 `ulong` typedef） |
| 共享库 | 上游 CMakeLists 硬编码 `add_library(exmdbpp SHARED ...)`，故配方仅支持 `shared=True` |
| 构建日志 | clang 诊断经 conan 管道会被吞掉，配方 `build()` 将输出落盘到 `build.log` |
| 测试 | 上游无测试；`test_package` 自研消费者测试，32 项 `CHECK` 断言全部通过（Release/NDEBUG 下亦生效） |
| 未验证部分 | `connect()` / `login()` 等需真实 exmdb 服务端的 socket 路径，仅保证编译链接通过 |

## 目录

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| [1.11](1.11/) | published | 2026-09-23 |
