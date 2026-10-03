# kea-hook-host-cache

ISC Kea 的 **host_cache**（主机保留内存缓存）hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_host_cache.so` 是 Kea DHCP 服务器的**主机保留缓存**插件：把（可能很慢的）
主机保留后端（数据库、配置后端等）的查询结果缓存到内存容器里，同一保留第二次
查询直接由缓存回答，不再触达后端。它在 Kea 中扮演 host data source 角色
（实现 `isc::dhcp::CacheHostDataSource` 接口），并注册 9 个控制通道命令管理
缓存：`cache-size`、`cache-clear`、`cache-flush`、`cache-get`、`cache-get-by-id`、
`cache-write`、`cache-insert`、`cache-load`、`cache-remove`。**双协议**：可同时
加载进 kea-dhcp4 与 kea-dhcp6 服务器（与仅 v4 的 bootp 插件不同）。插件由 Kea
服务器在运行时 `dlopen()` 加载（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/host_cache/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_host_cache.so`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带 Kea 运行时共享库（`lib/libkea-*.so*`），因此安装后无需额外的
Kea 运行库即可被服务器加载。

## OHOS 适配要点

本配方与家族配方 kea-hook-limits/kea-hook-ping-check/kea-hook-flex-option 同属
Kea 3.0.3 单源码树，4 个补丁**整组逐字节复用**（0001/0002 与 limits 一致；
0003/0004 与 ping-check 一致）；另有 1 个本插件新增的平台测试适配补丁 0005
（上游测试写死 /tmp、OHOS /tmp 只读 → 数据目录改指可写的构建目录），
适配要点逐项保留：

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
4. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径
   （OHOS 的 Python subprocess 不解析 PATH）。
5. **脚本执行一律经解释器**：OHOS 内核拒绝 shebang 脚本的 execve（无论执行位），
   而 Kea 的 configure 期会直接执行 `scripts/env.sh`、`scripts/grabber.py`、
   `config-report.sh`、`tools/mk_cfgrpt.sh` 等辅助脚本。补丁将脚本变量重定义为
   解释器前缀数组（`['/bin/sh', 脚本]` / `[find_program('python3').full_path(),
   脚本]`）；配方自身的 `build()` 也遵循同一纪律——conan 的 meson 包
   `bin/meson` 是 shell 包装脚本，改经 `sh "<meson 包>/bin/meson"` 调用。
6. **soname 物化**：OHOS /storage 沙箱拒绝符号链接，meson 的版本化 soname
   只以符号链接发布 → `build()` 在 compile 后以复制方式物化 soname 名
   （`_materialize_sonames`，幂等）。
7. **并发限制**：OHOS app 沙箱限制并发进程，`meson compile -j 8` 防
   posix_spawn EAGAIN（家族配方 host-cmds 实测）。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-host-cache-tests` | 140 | 容器索引（cache_unittests 23）+ 9 个命令 callout（command_unittests 30）+ CacheHostDataSource 查询接口（host_data_source_unittests 87，含 42 个 MultiThreading 变体） |
| `dhcp-host-cache-libloadtests` | 4 | 加载契约：kea-dhcp4 与 kea-dhcp6 双协议加载成功（validLoad）；family 不匹配及 ctrl-agent/ddns/bogus 加载失败（invalidDaemonLoad）；9 个 cache-* 命令在 v4/v6 注册齐全（commands4/commands6） |

144 例全部为纯逻辑用例：无 root 用例、无预置外部数据文件，OHOS 沙箱下零 root
零 SKIP 全实跑（实测见版本级 `notes.md`）。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_host_cache_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下逐个 `dlopen(RTLD_NOW)` 包内 Kea 运行时库，校验完整 NEEDED 闭包可解析、闭包驻留后 hook 仍可加载且契约符号可解析 |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-hook-host-cache/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf`，双协议插件的 dhcp6 配置同理）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_host_cache.so" }
    ]
  }
}
```
