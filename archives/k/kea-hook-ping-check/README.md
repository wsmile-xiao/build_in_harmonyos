# kea-hook-ping-check

ISC Kea 的 **ping-check**（候选地址探测）hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_ping_check.so` 是 Kea DHCPv4 服务器的地址冲突探测钩子：服务器在把某个
候选地址放进 DHCPOFFER 之前，先向该地址发送 ICMP echo 请求（`ping`），收到回显
应答说明地址已被占用，则跳过该地址。插件由 Kea 服务器在运行时 `dlopen()` 加载
（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/ping_check/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_ping_check.so`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带插件运行时加载的 20 个 Kea 共享库（`readelf -d` NEEDED 闭包），
因此安装后无需额外的 Kea 运行库即可被服务器加载。

## OHOS 适配要点

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
   而 Kea 的 configure 期会直接执行 `scripts/env.sh`、`scripts/grabber.py`
   等辅助脚本。补丁将脚本变量重定义为解释器前缀数组
   （`['/bin/sh', 脚本]` / `[find_program('python3').full_path(), 脚本]`，
   meson 的 run_command 数组首参语法已真机验证）；配方自身的 `build()`
   也遵循同一纪律——conan 的 meson 包 `bin/meson` 是 shell 包装脚本，改经
   `sh "<meson 包>/bin/meson"` 调用。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-ping-check-tests` | 90 | hook 单元测试（config_cache / ICMP 消息编解码 / PingChannel 状态机 / PingCheckMgr 流程 / PingContext 存储） |
| `dhcp-ping-check-libloadtests` | 4 | 插件的加载/卸载契约与回调行为 |

其中 `RootICMPSocketTest`（2）、`RootPingChannelTest`（18）、
`RootPingCheckMgrTest`（26）共 46 例为上游标记的 **root 用例**：它们真实打开
`SOCK_RAW` ICMP 套接字并对 127.0.0.1 做真实回显往返（上游 CI 以 root 运行；
上游 `-Dsudo=enabled` 时这组用例会从主套件剔除并改由 sudo 运行）。

本版本实测：见版本级 `notes.md`（含 root 用例在 OHOS 沙箱下的处置记录）。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_ping_check_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下逐个 `dlopen(RTLD_NOW)` 包内 20 个 Kea 运行时库，校验完整 NEEDED 闭包可解析、闭包驻留后 hook 仍可加载且契约符号可解析 |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-hook-ping-check/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf`）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_ping_check.so" }
    ]
  }
}
```
