# Zeek

> 可扩展的网络安全监控平台（原 Bro）：对网络流量做深度协议解析、会话分析与威胁检测。

## 简介

Zeek（原 Bro）是事实上的开源网络安全分析标准，由 Zeek 基金会与 Stanford 大学开发。
它以脚本化方式（Zeek 脚本语言 + Spicy 应用层解析 DSL）提供数百种协议分析器
（HTTP、DNS、SSL/TLS、FTP、IMAP、SSH 等），产出结构化的 conn.log、dns.log、http.log
等日志，广泛用于安全运营、流量取证与恶意流量检测。

本归档提供 Zeek 8.2.1 在 HarmonyOS PC（aarch64）上的 Conan 配方与适配产物。
本版本采用最小可行 core 构建形态（`-DDISABLE_SPICY=ON -DDISABLE_JAVASCRIPT=ON`）：
核心 C++ 引擎、broker 消息层（libbroker）与命令行工具链完整可用；
Spicy 生成的应用层分析器与 JavaScript 脚本引擎不在本版本范围内（见「排除与替代」）。

## OHOS 适配要点

- 交叉编译走 Conan `ci/conan/profiles/ohos-aarch64`（clang 15 / musl / libc++ 15.0.4 / C++17）。
- CMake 平台探测：OHOS 不在 fiber/libkqueue 的 OS 白名单，toolchain 注入
  `CMAKE_SYSTEM_NAME=Linux`（OHOS 为 Linux 内核 + musl，语义等价），详见 `8.2.1/notes.md` P1。
- OHOS libc++ 缺 `<memory_resource>`（std::pmr）与 C++20 ranges 算法：
  前者用 shim 头（`shims/memory_resource`，`-I` 注入，不进 patches）补全（P4），
  后者机械改写为等价经典 STL（47 文件 83+ 处，P3）。
- OHOS musl 声明但未实现 pthread 线程取消符号（pthread_cancel 等）：
  `shims/pthread_compat.c` 提供 weak no-op 实现链入所有可执行文件
  （知识图谱 E085；R8 合规：无 `__OHOS__` 平台宏进 patches）。
- host 生成器（bifcl/binpac/gen-zam）交叉编译：CMake 4.1.2 下 ALIAS 目标名
  不再展开为可执行路径，改用 `$<TARGET_FILE:...>` 生成器表达式（补丁 0015-0017）。

## 排除与替代

- `zeekctl`/`zkg`/`zeek-client`：依赖 Python 运行时与 SWIG 绑定，本构建关闭
  （`-DINSTALL_ZEEKCTL=OFF -DINSTALL_ZKG=OFF -DINSTALL_ZEEK_CLIENT=OFF`）。
  替代：直接用 `zeek` 命令行驱动分析（`zeek -b <script> -i <input>`）。
- ZeroMQ 集群后端：`-DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF`（集群模式本版本不启用）。
- Spicy 应用层分析器（HTTP/DNS 深度字段提取等）：`-DDISABLE_SPICY=ON`；
  依赖 Spicy 分析器的 base 脚本（如 igmp）加载会 fatal，
  完整能力待 Spicy 全量构建版本（后续可走依赖项路径单独包化）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libpcap | 1.10.6 | 抓包（requires） |
| openssl | 3.5.8.1 | TLS/证书解析（requires） |
| zlib | 1.3.1 | 压缩（requires） |
| flex | 2.6.4 | 词法生成（tool_requires） |
| bison | 3.8.2 | 语法生成（tool_requires） |

## 功能验证

```bash
# Conan 安装（CI 同源 profile）
conan install --requires=zeek/8.2.1 -pr:a ci/conan/profiles/ohos-aarch64 --build=missing

# 冒烟（与 test_package 同款断言）
zeek --version   # 期望输出: zeek version 8.2.1
```

## 参考

- [官网](https://zeek.org/)
- [源码仓库](https://github.com/zeek/zeek)
- [8.2.1 适配笔记](8.2.1/notes.md)
- [8.2.1 测试报告](8.2.1/reports/test-report.md)
- [8.2.1 兼容性评估](8.2.1/compatibility.md)
- [8.2.1 编译过程记录](8.2.1/reports/build-report.md)
