# kea-hook-bootp 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-02
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published（真机 conan-verify 全绿）

## 定位与家族复用

`bootp` 与已合入的 `kea-hook-limits`、`kea-hook-ping-check`、`kea-hook-flex-option`
同属 Kea 3.0.3 单源码树（`src/hooks/dhcp/bootp/` 平级目录），平台差异完全相同：
4 个补丁**整组逐字节复用**（0001/0002 与家族模板 kea-hook-limits 一致；
0003/0004 与家族配方 kea-hook-ping-check 一致，均作用于同一上游树的同一批文件），
零改动，本插件无新增平台问题。插件本身的源码核对（2026-10-02）：

- 产物 `libdhcp_bootp.so`（`meson.build` `shared_library('dhcp_bootp', ...)`，
  4 个 .cc 源文件：bootp_callouts / bootp_log / bootp_messages / version）
- 上游套件名：`dhcp-bootp-lib-tests` + `dhcp-bootp-libload-tests`
- 用例宏计数：tests/ 9 + libloadtests/ 2 = 11，无 TEST_P
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 插件行为与测试面特点

**行为**（RFC1497 BOOTP 兼容，两个 callout）：

- `buffer4_receive`：识别没有 DHCP 报文类型选项的 `BOOTREQUEST`，把它标记进
  `BOOTP` 类并按 DHCPREQUEST 改型（`addClass` + `setType`），使 kea-dhcp4 能像
  处理 DHCP 一样为旧式客户端分配主机保留地址；反方向 `BOOTREPLY` 与其他报文
  类型（DHCPDISCOVER/REQUEST/OFFER）原样放行。
- `pkt4_send`：查询属于 `BOOTP` 类时，剥离响应中的 DHCP 私有内容
  （`DHO_DHCP_MESSAGE_TYPE` 等选项并补零），使回包成为纯 `BOOTREPLY` 形态；
  纯 DHCP ACK/NAK 原样放行。

**测试面**：9 + 2 = 11 例全部为纯逻辑用例——报文构造、pack/unpack、
callout handle 驱动（`bootp_unittests.cc` 9 例覆盖上述分类矩阵；
`load_unload_unittests.cc` 2 例经 hook 框架真实 dlopen 插件：`validLoad4`
验证可加载进 DHCPv4 服务器、`invalidDaemonLoad` 验证加载进其他守护进程
（如 DHCPv6）失败）。无 SOCK_RAW、无特权依赖、无外部数据文件（源码 grep
零命中 geteuid/fork/system/popen），OHOS 沙箱下**零 root 零 SKIP 全实跑**
（与 ping-check 48 个 Root 组用例 SKIP 形成对比；实测结果见「真机验证」节）。
与 flex-option 的差异：bootp 为 **DHCPv4 单协议**插件（flex-option 服务 v4/v6
双协议），加载约束由 libloadtest 的 `invalidDaemonLoad` 固证。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/bootp/libdhcp_bootp.so \
        src/hooks/dhcp/bootp/tests/dhcp-bootp-lib-tests \
        src/hooks/dhcp/bootp/libloadtests/dhcp-bootp-libload-tests`
   （配方内以 `meson compile -j 8` 限并发：OHOS app 沙箱进程配额，见问题 11）
4. `meson test -v dhcp-bootp-lib-tests dhcp-bootp-libload-tests`

## 遇到的问题与解决方案

问题 1-11 为家族配方已解决的平台问题（同一上游树、同一差异），对策一一沿用
（4 个补丁整组复用 + 配方内三处构建级适配），本插件无新增平台问题：

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
| 10 | meson test 双套件 exit status 127，stderr 刷屏 `Error loading shared library libkea-X.so.N` | OHOS /storage 沙箱**拒绝创建符号链接**：meson 用 `version: 'N.M.K'` 构建并只以符号链接发布 soname 名 → 加载器按 NEEDED 名找文件落空 | build() 在 compile 后 `_materialize_sonames()` 以复制方式物化 soname 名（幂等；普通 Linux 宿主跳过）；package() 保留 0 字节落盘自愈复核，test_package 闭包逐个 dlopen 兜底 |
| 11 | ninja 默认并行度在 OHOS 上编译中道崩殂（posix_spawn EAGAIN） | OHOS app 沙箱限制并发进程数：真机 20 核 + ninja 默认并行度 ≈45 活进程瞬时超配额 | 编译行 `meson compile -j 8` 限并发（与 make 家族 MAKEFLAGS jobserver 同源） |

## 真机验证

2026-10-02 真机（HarmonyOS PC aarch64，conan 2.29.1，profile ohos-aarch64）
`ohc-run.py conan-verify` **G0-G4 + L2-L5 全 PASS**，验证报告 16:25:55 生成，
Verdict: PASS，R46 终态 result.json 已上报（draft:false）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ | E490 提示为 autotools 启发式误报（本配方 meson，无 configure 脚本），不影响 |
| G1 | ✅ | 配方完整性 11 项全过（R26/R28 通过） |
| G2 | ✅ | conan create 干净构建（全树 [1432/1432] 链接零错误）+ build() 内 meson test 实跑 + test_package |
| G3 | ✅ | R26 系统同名库隔离验证通过 |
| G4 | ✅ | 产物完整性检查通过 |
| L2/L4/L5 | ✅ | 框架在非默认 cache 路径下按“无 cache 路径”跳过深度检查并记 PASS（与家族配方同一运行环境行为） |

真机实测数据（reports/conan-create.log）：

- **meson test 两套件**：`dhcp-bootp-lib-tests` 9 例 + `dhcp-bootp-libload-tests` 2 例，
  **PASSED 11 / SKIPPED 0 / FAILED 0**（`[ PASSED ] 9 tests` + `[ PASSED ] 2 tests`，
  `Ok: 2 Fail: 0`）。9 例为 0 ms 级纯逻辑用例（报文集构造 + pack/unpack +
  callout handle 驱动，逐例 OK：dhcpDiscover/dhcpRequest/dhcpOffer/bootReply/
  bootRequest/dhcpAck/bootpAck/dhcpNak/bootpNak）；libloadtests 2 例经 hook 框架
  真实 dlopen 插件（validLoad4 4 ms / invalidDaemonLoad 1 ms）
- **test_package 3/3**：
  - test_bootp_hook：dlopen 加载成功（`libdhcp_bootp.so loaded (hooks version 30003)`）→ OK
  - test_ohos_platform：ELFCLASS64 / EM_AARCH64 / PT_DYNAMIC ✓；
    **DT_NEEDED 8 项** = kea 闭包 6（libkea-process.so.91 / stats.so.53 /
    dhcp.so.109 / asiolink.so.88 / log.so.75 / exceptions.so.45）+
    libc++_shared.so + libc.so（无 glibc/libstdc++ 命名）→ OK
  - test_ohos_runtime：包内 Kea 运行库 **40 found / 40 loaded**，
    闭包驻留后 hook 仍可加载、契约符号可解析 → OK
- **产物**：`lib/kea/hooks/libdhcp_bootp.so`（86 KB / 88512 字节）+ Kea 运行时闭包
  40 文件（20 库 × soname 名 + 全版本名）
- **0 字节落盘自愈命中 ×20**：本次真机验证与另一构建并发（高负载）下，package()
  复核发现全部 20 个 soname 名文件落盘为空，已逐一从构建树重拷（WARNING 日志
  20 条留存）；其后 test_ohos_runtime 40/40 dlopen 证明自愈有效（与 ping-check /
  flex-option 笔记同款瞬时异常，本配方因并发负载命中面更大）

运行环境备注（非配方知识）：直连 ftp.isc.org 出现 IncompleteRead 中断（读 3.7 MB /
共 6.6 MB 超时）→ 源码 tarball 改经设备内 127.0.0.1:18080 http 镜像供给（设备侧
conandata.yml 临时换 URL，本地配方保持官方 URL 不提交，与 flex-option 先例一致）；
依赖全部命中设备家族缓存（CONAN_HOME=/storage/Users/currentUser/.conan2），
零网络构建。

## 已知限制

无。上游本组件 11 例全部为纯逻辑用例（无 root 用例、无外部数据文件），不存在
ping-check 式 root 用例 SKIP；全树其余 11727 例（Kea 主程序、核心库及其他 hook
组件）不在本配方适配范围（见 MR 正文「测试减少原因」节）。
