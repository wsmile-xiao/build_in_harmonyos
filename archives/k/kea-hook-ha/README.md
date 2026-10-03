# kea-hook-ha

ISC Kea 的 **High Availability**（HA 高可用）hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_ha.so` 是 Kea DHCPv4/DHCPv6 服务器的高可用钩子：让多台 kea-dhcp4 /
kea-dhcp6 服务器组成冗余集群，在 `hot-standby`（热备）、`load-balancing`
（负载分担）与 `passive-backup`（被动备份）模式下对外提供容灾 DHCP 服务。
插件注册服务配置/报文处理/租约提交等 callout（`dhcp4_srv_configured`、
`buffer4_receive`、`subnet4_select`、`leases4_committed`、`lease4_expire` /
`lease4_server_decline` 及 v6 对等项）参与服务器主流程；伙伴间通过
`ha-heartbeat` 心跳、`ha-sync` 批量租约同步、`ha-scopes` 管辖范围声明、
`ha-reset` / `ha-continue` 状态机控制与 `ha-maintenance-*` 维护窗口等
**9 个控制命令**协同（租约更新经 `lease_sync_filter` 过滤与
`lease_update_backlog` 补偿队列交换），通信状态机由 `communication_state`
驱动。该库可加载进 **DHCPv4 与 DHCPv6 两种服务器**（libloadtest
`validLoadDhcp4` + `validLoadDhcp6` 固证；加载进其他守护进程失败）。插件由
Kea 服务器在运行时 `dlopen()` 加载（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/high_availability/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_ha.so`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；crypto 后端（HA 伙伴通信的 TLS 与签名依赖 cryptolink） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带 Kea 运行时共享库（`lib/libkea-*.so*`），因此安装后无需额外的
Kea 运行库即可被服务器加载。

## OHOS 适配要点

本配方与家族配方 kea-hook-limits/kea-hook-ping-check/kea-hook-flex-option/
kea-hook-bootp 同属 Kea 3.0.3 单源码树，0001-0004 四个补丁**整组逐字节复用**
（0001/0002 与 limits 一致；0003/0004 与 ping-check 一致）；0005 为本插件新增
（沙箱 netlink 回退）。适配要点逐项保留：

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
8. **netlink 沙箱回退**（本插件新增）：OHOS 沙箱对 AF_NETLINK 放行
   `socket()` 创建但拒绝 `bind()`，Kea 的 Linux `IfaceMgr` 构造即抛
   `IfaceDetectError`（HA 建伙伴连接时构造 IfaceMgr → 首轮 48 例测试失败）
   → 补丁 0005 让 `detectIfaces()` 在 netlink 打不开时回退 `getifaddrs()`
   枚举（AF_PACKET 取 MAC/HWType），与上游 BSD/Solaris 实现同构，常规
   Linux 上回退永不触发。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-ha-lib-tests` | 443 | HA 协议核心库：command_creator 26、communication_state 57、ha_config 61、ha_impl 62、ha_mt 3、ha_relationship_mapper 5、ha_service 190、lease_sync_filter 5、lease_update_backlog 2、query_filter 32 |
| `dhcp-ha-libload-tests` | 7 | 插件加载约束：可加载进 DHCPv4（`validLoadDhcp4`）与 DHCPv6（`validLoadDhcp6`）服务器、加载进其他守护进程失败（`invalidDaemonLoad`），以及 v4/v6 关闭路径（`close4`/`close4Backup`/`close6`/`close6Backup`） |

450 例全部为本地回环（127.0.0.1）与纯逻辑用例：无 SOCK_RAW、无特权依赖、无外部
数据文件、无证书文件依赖（源码 grep 零命中 geteuid/fork/system/popen 与 /tmp
硬编码；生产侧 TLS 支持由 cryptolink 提供，测试仅 `tlsParameterInheritance`
一条用例做 TLS 配置参数继承的纯解析校验，不做握手、不落盘证书），OHOS 沙箱下
零 root 零 SKIP 全实跑（实测见版本级 `notes.md`）。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_ha_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下逐个 `dlopen(RTLD_NOW)` 包内 Kea 运行时库，校验完整 NEEDED 闭包可解析、闭包驻留后 hook 仍可加载且契约符号可解析 |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-hook-ha/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf` / `kea-dhcp6.conf`，以热备模式为例）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      {
        "library": "<prefix>/lib/kea/hooks/libdhcp_ha.so",
        "parameters": {
          "high-availability": [
            {
              "this-server-name": "server1",
              "mode": "hot-standby",
              "peers": [
                { "name": "server1", "url": "https://192.0.2.1:8000/", "role": "primary" },
                { "name": "server2", "url": "https://192.0.2.2:8000/", "role": "standby" }
              ]
            }
          ]
        }
      }
    ]
  }
}
```

示例使用文档专用地址（192.0.2.0/24，仅示意）。HA 伙伴间交换心跳、租约同步
与状态机控制报文，**生产部署必须使用 `https://` 并配置 TLS 参数**
（`trust-anchor` 与对端证书材料等，见 Kea ARM 的 high-availability TLS 配置）；
本包依赖的 cryptolink（openssl）提供该能力。
