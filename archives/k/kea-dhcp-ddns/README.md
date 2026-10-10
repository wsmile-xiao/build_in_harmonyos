# kea-dhcp-ddns

ISC Kea 的 **DHCP-DDNS（D2）守护进程**，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`kea-dhcp-ddns` 是 Kea 套件的 DHCP-DDNS 独立守护进程（昵称 D2）：接收
kea-dhcp4 / kea-dhcp6 服务器发来的 NameChangeRequest（NCR），按配置执行
**TSIG 签名的 DNS 动态更新**——`forward-ddns` 维护正向 A/AAAA 记录、
`reverse-ddns` 维护 PTR 记录。守护进程内置请求队列管理（`D2QueueMgr`）、
更新管理（`D2UpdateMgr`：DNS 服务器选择、失败重试与超时）、TSIG key 管理
与 HTTP 控制通道；支持配置语法检查（`-t`）与 SIGHUP 动态重配置。产物是
命令行守护进程，由管理员直接启动（`kea-dhcp-ddns -c <config>`），不是被
链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/bin/d2/`（守护进程主程序）+ `src/lib/d2srv/`（D2 核心库），
  与 Kea 同一源码树，Meson 单工程构建
- 产物路径：`bin/kea-dhcp-ddns`（上游 `SBINDIR`，Conan 包按约定落 `bin/`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`，TSIG 签名依赖 cryptolink） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带守护进程运行时加载的 Kea 共享库闭包（`lib/libkea-*.so*`，
`readelf -d` NEEDED 闭包，实测数量见版本级 `notes.md`），因此安装后无需
额外的 Kea 运行库即可直接启动。

## OHOS 适配要点

本配方与家族配方 kea-hook-limits/kea-hook-ping-check/kea-hook-flex-option/
kea-hook-ha/kea-hook-flex-id 同属 Kea 3.0.3 单源码树，0001-0004 四个补丁
**整组逐字节复用**；补丁 0005（GNU 风格长选项别名，见要点 8）为**本包新增**；
kea-hook-ha 的补丁 0005（沙箱 netlink 回退）**不携带**——D2 守护进程与其测试
从不构造 `IfaceMgr`（`src/bin/d2` 与 `src/lib/d2srv` 零引用），该代码路径
对本包不可达。适配要点逐项保留：

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
   `bin/meson` 是 shell 包装脚本，改经 `sh "<meson 包>/bin/meson"` 调用；
   上游进程级 shell 套件 `d2_process_tests.sh` 同理经 `sh` 执行。
6. **soname 物化**：OHOS /storage 沙箱拒绝符号链接，meson 的版本化 soname
   只以符号链接发布 → `build()` 在 compile 后以复制方式物化 soname 名
   （`_materialize_sonames`，幂等）。
7. **并发限制**：OHOS app 沙箱限制并发进程，`meson compile -j 8` 防
   posix_spawn EAGAIN（家族配方 host-cmds 实测）。
8. **平台工具链的 CLI 探测**：OHOS PC 打包工具链（真机 conan-verify 的冒烟
   门禁与 MR CI 冒烟测试）以 `--version`/`--help` 探测包内可执行文件，而 Kea
   守护进程的 getopt 短选项表（`dvVWc:t:X`）不接受长选项，实测直接以
   usage 报错退出（rc=1）。补丁 0005 在 `DControllerBase::parseArgs` 中把
   两者处理为既有行为的纯别名（`--version` 等同 `-v`、`--help` 打印 usage，
   均退出 0），不改动任何其他行为。

## 上游测试

一个 Meson 注册的 gtest 套件与一个进程级 shell 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `kea-d2-tests`（gtest） | 424 | D2 单元测试，18 个套件：parser 23、d2_simple_parser 15、nc_add 37、nc_remove 38、check_exists_add 37、check_exists_remove 38、simple_add 24、simple_add_without_dhcid 24、simple_remove 26、simple_remove_without_dhcid 26、d2_cfg_mgr 13、d2_command 26、d2_controller 9、d2_http_command 50、d2_process 16、d2_queue_mgr 4、d2_update_mgr 17、get_config 1 |
| `d2_process_tests.sh`（shell-tests） | 10 场景 | 进程级：server_pid_file、dynamic_reconfiguration（SIGHUP）、sigterm、sigint、version、logger_vars、syntax_check×3（含 `-t`）、password_redact——驱动真实守护进程（127.0.0.1:53001） |

424 例全部为本地回环（127.0.0.1）与纯逻辑用例：无 SOCK_RAW、无特权依赖、
无外部数据文件；进程级套件真实起停守护进程并经 pidfile 收发 SIGHUP/SIGINT/
SIGTERM，OHOS 沙箱下零 root 实跑（实测见版本级 `notes.md`）。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_kea_dhcp_ddns.py` | 消费者契约 | 包内守护进程：`-v` 版本（含本包新增的 GNU 风格别名 `--version` 同输出 / `--help` 打印 usage，均退出 0）、`-t` 语法检查三路径（合法/坏 JSON/越界端口）、一次完整守护进程生命周期（启动 → `DCTL_CONFIG_COMPLETE` → SIGTERM → `DCTL_SHUTDOWN`） |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`ET_DYN` PIE、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so` |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下校验完整 NEEDED 闭包：DT_NEEDED 的 Kea 库全部随包分发、包内 Kea 运行时库逐个 `dlopen(RTLD_NOW)`、真实执行 `kea-dhcp-ddns -v` |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-dhcp-ddns/3.0.3 -pr:h=<ohos-aarch64 profile>
```

启动守护进程（最小配置示例，管理地址 192.0.2.1 为文档专用地址）：

```json
{
  "DhcpDdns": {
    "ip-address": "192.0.2.1",
    "port": 53001,
    "tsig-keys": [],
    "forward-ddns": { "ddns-domains": [] },
    "reverse-ddns": { "ddns-domains": [] },
    "loggers": [
      { "name": "kea-dhcp-ddns", "output-options": [ { "output": "/var/log/kea-dhcp-ddns.log" } ] }
    ]
  }
}
```

```bash
kea-dhcp-ddns -t /etc/kea/kea-dhcp-ddns.conf   # 配置语法检查
kea-dhcp-ddns -c /etc/kea/kea-dhcp-ddns.conf   # 启动守护进程
```

上游：https://www.isc.org/kea/ -- https://gitlab.isc.org/isc-projects/kea
