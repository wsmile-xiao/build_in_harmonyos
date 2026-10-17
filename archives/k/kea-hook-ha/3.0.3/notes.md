# kea-hook-ha 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-02
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published（真机 conan-verify 全绿）

## 定位与家族复用

`high_availability`（HA 高可用 hook）与已合入的 `kea-hook-limits`、
`kea-hook-ping-check`、`kea-hook-flex-option`、`kea-hook-bootp` 同属 Kea 3.0.3
单源码树（`src/hooks/dhcp/high_availability/` 平级目录），平台差异完全相同：
0001-0004 四个补丁**整组逐字节复用**（0001/0002 与家族模板 kea-hook-limits 一致；
0003/0004 与家族配方 kea-hook-ping-check 一致，均作用于同一上游树的同一批文件），
零改动；**0005 为本插件新增**（OHOS 沙箱 netlink bind 拒绝的 getifaddrs 回退，
见问题 12——HA 是家族中首个在测试与生产路径构造 `IfaceMgr` 的成员，故首次暴露）。
插件本身的源码核对（2026-10-02）：

- 产物 `libdhcp_ha.so`（`meson.build` `shared_library('dhcp_ha', ...)`，
  14 个 .cc 源文件：command_creator / communication_state / ha_callouts /
  ha_config / ha_config_parser / ha_impl / ha_log / ha_messages / ha_service /
  ha_service_states / lease_sync_filter / lease_update_backlog / query_filter /
  version；`dependencies: [CRYPTO_DEP]`）
- 上游套件名：`dhcp-ha-lib-tests` + `dhcp-ha-libload-tests`
- 用例宏计数：tests/ 443（10 个测试文件）+ libloadtests/ 7 = 450，无 TEST_P、
  无 DISABLED_ 前缀用例
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 插件行为与测试面特点

**行为**（HA 冗余集群，多 callout + 9 个控制命令）：

- 服务器生命周期与报文 callout：`dhcp4_srv_configured` / `dhcp6_srv_configured`
  在服务配置时启动 HA 服务与通信状态机；`buffer4_receive` / `subnet4_select` /
  `leases4_committed` / `lease4_expire` / `lease4_server_decline`（v6 对等项）
  参与主流程，把本机租约变更经 `lease_sync_filter` 过滤后推送给伙伴。
- 伙伴协同（命令面，9 个）：`ha-heartbeat`（心跳与状态探测）、`ha-sync`
  （批量租约同步）、`ha-scopes`（管辖范围声明）、`ha-continue` / `ha-reset`
  （状态机控制）、`ha-maintenance-notify` / `ha-maintenance-start` /
  `ha-maintenance-cancel`（维护窗口）、`ha-sync-complete-notify`（同步完成确认）；
  通信状态机（communication_state）驱动 hot-standby / load-balancing /
  passive-backup 三种模式的状态迁移。
- 插件可加载进 **DHCPv4 与 DHCPv6 两种服务器**（libloadtests `validLoadDhcp4` +
  `validLoadDhcp6`），加载进其他守护进程失败（`invalidDaemonLoad`）。
- 伙伴连接建立后经 `IfaceMgr::instance().addExternalSocket()` 把外部套接字
  注册进主循环（`ha_service.cc` clientConnectHandler，生产路径）；该路径使 HA
  成为家族中首个构造 `IfaceMgr` 的组件——OHOS 沙箱拒绝 netlink bind，构造即抛
  `IfaceDetectError`（问题 12 的触发点，由补丁 0005 修复）。

**测试面**：443 + 7 = 450 例全部为本地回环（127.0.0.1）与纯逻辑用例：
`ha_service_unittest.cc` 190 例以真实 HA 服务实例 + 回环通信驱动完整状态机
（心跳、租约同步、伙伴失联、伙伴宕机接管等），`communication_state` 57 例、
`ha_impl` 62 例、`ha_config` 61 例等覆盖配置解析与实现细节；`ha_mt` 3 例做
多线程交互。无 SOCK_RAW、无特权依赖、无外部数据文件、无证书文件依赖
（源码 grep 零命中 geteuid/fork/system/popen 与 /tmp 硬编码；生产侧 TLS 支持由
cryptolink 提供，测试仅 `tlsParameterInheritance` 一条做 TLS 配置参数继承的纯
解析校验），OHOS 沙箱下**零 root 零 SKIP 全实跑**（与 ping-check 48 个 Root 组
用例 SKIP 形成对比；实测结果见「真机验证」节）。与 bootp 的差异：bootp 为
DHCPv4 单协议插件，HA 为 **v4/v6 双协议**插件，加载面由 libloadtest 的
`validLoadDhcp4` + `validLoadDhcp6` 双向固证。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/high_availability/libdhcp_ha.so \
        src/hooks/dhcp/high_availability/tests/dhcp-ha-lib-tests \
        src/hooks/dhcp/high_availability/libloadtests/dhcp-ha-libload-tests`
   （配方内以 `meson compile -j 8` 限并发：OHOS app 沙箱进程配额，见问题 11）
4. `meson test -v dhcp-ha-lib-tests dhcp-ha-libload-tests`

## 遇到的问题与解决方案

问题 1-11 为家族配方已解决的平台问题（同一上游树、同一差异），对策一一沿用
（0001-0004 补丁整组复用 + 配方内三处构建级适配）；问题 12 为本插件**新增**
（补丁 0005，沙箱 netlink 回退）：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running llvm-ar --version gave [Errno 2]` | 宿主环境 `AR=llvm-ar`（裸名）被 meson 静态链接器探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行**不解析 PATH**，裸名直接 ENOENT（`which llvm-ar` 却能找到） | `generate()` 从 `tools.build:compiler_executables` 的编译器目录推导 `llvm-ar`/`llvm-ranlib` **绝对路径**写入 machine file `[binaries]` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 meson 的 `build_machine.system()` 返回 `harmonyos`；Kea 白名单只含 linux/bsd/solaris/darwin | 补丁 `0001-meson.build.patch`（与家族模板逐字节一致）：`SYSTEM == 'harmonyos'` 归一化为 `'linux'` |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（首错 `boost/core/detail/sp_thread_sleep.hpp:73: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate()`，boost 1.85 的 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` + `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | meson 的"编译并运行"探针在 native 构建下真实执行；探针链接的 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH` | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` 聚合进 `conanbuild.sh` |
| 5 | `ninja FAILED: src/lib/dhcp/libkea-dhcp.so.109.0.0.p/iface_mgr_linux.cc.o` → `.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h` 都定义 `struct sockaddr_storage` | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（与家族模板逐字节一致）：define-guard 重命名，守卫 `__linux__ && !__GLIBC__` |
| 6 | `meson setup` 报 `/bin/sh: <conan 缓存>/bin/meson: Permission denied`（Error 126） | Conan 的 meson 包 `bin/meson` 是 **shebang shell 包装脚本**；OHOS 内核拒绝对脚本的 execve | build() 改 `sh "<meson 包>/bin/meson" setup/compile/test`（sh 直接读脚本不触发 execve；命令行参数与 conan 2.29 helper 完全一致） |
| 7 | `meson setup` 收尾处 `Running command: scripts/env.sh KEA_PKG_TYPE_IN_CONFIGURE` → `ERROR: Unhandled python OSError`（Error 13） | Kea 顶层 meson.build 在 configure 期直接 `run_command(ENV, ...)` 执行 `scripts/env.sh` 与 `scripts/grabber.py`——均为带 shebang 的脚本，OHOS 内核拒 execve | 补丁 `0003-meson.build.patch`（与家族配方逐字节一致）：脚本变量重定义为解释器前缀数组（`ENV = ['/bin/sh', <脚本路径>]`、`GRABBER = [find_program('python3').full_path(), <脚本路径>]`），调用点零改动 |
| 8 | setup 收尾 `Configuring config.report with command` → Error 13 | `meson.build:1025` 的 `CONFIG_REPORT = configure_file(command: [TOP_BUILD_DIR / 'config-report.sh'])` 直接执行刚生成的脚本 | 补丁 `0003` 第二个 hunk：`command: ['/bin/sh', TOP_BUILD_DIR / 'config-report.sh']`（hunk 行号按 patch-ng 语义写 1028，与家族配方逐字节一致） |
| 9 | `src/lib/process/cfgrpt` 处 `Configuring config_report.cc with command` → Error 13 | `src/lib/process/cfgrpt/meson.build:4` 的 `command: [mk_cfgrpt, ...]` 直接执行 `tools/mk_cfgrpt.sh` | 补丁 `0004-src-lib-process-cfgrpt-meson.build.patch`（与家族配方逐字节一致）：`command: ['/bin/sh', mk_cfgrpt, '@INPUT@', '@OUTPUT@']` |
| 10 | meson test 双套件 exit status 127，stderr 刷屏 `Error loading shared library libkea-X.so.N` | OHOS /storage 沙箱**拒绝创建符号链接**：meson 用 `version: 'N.M.K'` 构建并只以符号链接发布 soname 名 → 加载器按 NEEDED 名找文件落空 | build() 在 compile 后 `_materialize_sonames()` 以复制方式物化 soname 名（幂等；普通 Linux 宿主跳过）；package() 保留 0 字节落盘自愈复核（重拷后复验，有界重试 3 次仍为 0 则打包失败），test_package 闭包逐个 dlopen 兜底 |
| 11 | ninja 默认并行度在 OHOS 上编译中道崩殂（posix_spawn EAGAIN） | OHOS app 沙箱限制并发进程数：真机 20 核 + ninja 默认并行度 ≈45 活进程瞬时超配额 | 编译行 `meson compile -j 8` 限并发（与 make 家族 MAKEFLAGS jobserver 同源） |
| 12 | meson test 首轮 `dhcp-ha-lib-tests` 48 例 FAIL：`isc::dhcp::IfaceDetectError ... "Failed to bind netlink socket."`（`ha_service_unittest.cc:907`） | OHOS 沙箱对 AF_NETLINK 只放行 `socket()` 创建，拒绝显式 `bind()`（EPERM）：Kea 的 Linux `IfaceMgr` 构造 → `detectIfaces()` → `Netlink::rtnl_open_socket()`（socket 后立即 bind）失败 → `iface_mgr.cc:206` 包装为 `IfaceDetectError` 抛出；HA 建伙伴连接时调用 `IfaceMgr::instance().addExternalSocket()`（`ha_service.cc:3326`），构造单例即触发，48 个发心跳/同步类用例全部命中 | 补丁 `0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback.patch`（**本插件新增，非家族复用**）：`detectIfaces()` 的 netlink 打开包 try/catch，失败时回退 `getifaddrs()` 两趟枚举（AF_PACKET 取 MAC/HWType、AF_INET/AF_INET6 取地址、`if_nametoindex` 取索引），与上游自带 BSD/Solaris 实现同构；常规 Linux 上 netlink 正常，回退永不触发，行为零变化 |

问题 12 真机取证（python 探针）：`socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)`
创建成功；显式 `bind()` 被拒；但 `getifaddrs()` 可用（AF_PACKET 13 条含
MAC/hatype + v4/v6 地址；`if_nameindex` 列出 19 个接口）、`if_nametoindex` 与
ioctl（SIOCGIFADDR / SIOCGIFFLAGS / SIOCGIFINDEX）均可用（`/proc/net/dev`
被拒）。补丁 0005 生效后重跑双套件 443/443 + 7/7 全绿（此前 48 FAIL）。

## 真机验证

2026-10-02 真机 conan-verify（HarmonyOS PC aarch64，`ohos-aarch64` profile，
`kea-hook-ha/3.0.3@ohpcd/stable`）：**八门禁（G0-G4 + L2/L4/L5）全 PASS，
Verdict: PASS**（报告时间 2026-10-02T20:42:01；L2/L4/L5 为框架对无 cache
路径包的既定跳过形态，与已合入的 kea-hook-bootp 报告一致）。

- **上游测试**（G2 内 `meson test -v` 实跑）：`dhcp-ha-libload-tests` 1/2 OK
  （0.34s，`[ PASSED ] 7 tests`）+ `dhcp-ha-lib-tests` 2/2 OK（31.39s，
  `[ PASSED ] 443 tests`，11 个 test suite），共 450 例 PASSED / 0 SKIPPED /
  0 FAILED；编译 0 error
- **test_package 3/3**：test_ha_hook（dlopen + hooks version 30003 契约符号）/
  test_ohos_platform（ELFCLASS64 + EM_AARCH64；DT_NEEDED 14 项 = 12 个
  libkea-*.so（dhcpsrv/process/stats/config/http/dhcp/hooks/cc/asiolink/log/
  util/exceptions）+ libc++_shared.so + libc.so，无 glibc/libstdc++ 命名）/
  test_ohos_runtime（闭包 40/40 逐个 dlopen(RTLD_NOW) + 闭包驻留后 hook 再加载）
- **产物**：`lib/kea/hooks/libdhcp_ha.so` 1,227,200 字节（1.17 MiB）；
  包内 Kea 运行时闭包 40 个库文件（20 库 × soname 名/全版本名），lib/ 共 44 MB
- **0 字节自愈**：package() 命中 20 次「re-copied empty artifact」
  （/storage 写回瞬时异常，已全部从构建树重拷修复，无残留）

## 已知限制

无。上游本组件 450 例全部为纯逻辑/回环用例（无 root 用例、无外部数据文件、
无证书文件依赖），不存在 ping-check 式 root 用例 SKIP；OHOS 沙箱的 netlink
bind 限制（问题 12）由补丁 0005 的 getifaddrs 回退消化，常规 Linux 宿主机上
该回退永不触发；全树其余 11288 例（Kea 主程序、核心库及其他 hook 组件）
不在本配方适配范围（见 MR 正文「测试减少原因」节）。
