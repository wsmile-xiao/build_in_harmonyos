# boost1.84-log_setup

Boost.LogSetup 组件拆分包——从 Boost 1.84.0 官方发行版中单独构建
Boost.Log/Boost.LogSetup 组件，提供：

- `boost1.84-log_setup/1.84.0`：
  - `libboost_log.a`（libs/log/src 核心 31 TU + posix/object_name、
    posix/ipc_reliable_message_queue + syslog_backend 可移植 UDP socket 实现；
    x86 SIMD TU 在 aarch64 排除）
  - `libboost_log_setup.a`（libs/log/src/setup 10 TU：settings/filter/
    formatter 解析器 + init_from_settings/init_from_stream + 默认工厂）
  - `libboost_thread.a`（libs/thread/src pthread 分支 3 TU——Boost.Log 的
    线程特定存储依赖编译型 libboost_thread 的 get_tss_data/set_tss_data 符号）
  - 完整 Boost 头文件树
- CMake 配置名：`BoostLogSetup`（组件目标 `Boost::log` / `Boost::log_setup` /
  `Boost::thread` / `Boost::headers`；组件包用独立 cmake_file_name 以避免与
  元包 cmake_file_name "Boost" 的 CMakeDeps 冲突）
- Conan 组件：`boost_log` / `boost_log_setup` / `boost_thread` / `boost_headers`

与 `boost/1.84.0` 元包的关系：元包提供 headers + filesystem/regex/
program_options/iostreams 编译库（本包 requires 元包，链接其 filesystem/
regex/iostreams）；本包是 log/log_setup 维度的拆分形态。

上游：https://github.com/boostorg/log（发行 tarball 见各版本 conandata.yml）

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.84.0 | built | 首次适配（手动编译 43 TU：31 log core + 2 posix + 10 setup，另含 thread pthread 3 TU；见 1.84.0/notes.md） |
