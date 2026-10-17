# kea-hook-host-cache 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-02
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published（2026-10-02 真机 conan-verify 八门禁全 PASS）

## 定位与家族复用

`host_cache` 与已合入的 `kea-hook-limits`、`kea-hook-ping-check`、`kea-hook-flex-option`
同属 Kea 3.0.3 单源码树（`src/hooks/dhcp/host_cache/` 平级目录），平台差异完全相同：
4 个补丁**整组逐字节复用**（0001/0002 与家族模板 kea-hook-limits 一致；
0003/0004 与家族配方 kea-hook-ping-check 一致，均作用于同一上游树的同一批文件），
零改动；另有 **1 个本插件新增的平台测试适配补丁 0005**（上游测试写死 /tmp、
OHOS /tmp 只读 → 数据目录改指构建目录，见问题 12，非家族复用）。
插件本身的源码核对（2026-10-02）：

- 产物 `libdhcp_host_cache.so`（`meson.build` `shared_library('dhcp_host_cache', ...)`，
  8 个 .cc 源文件：entry / host_cache / host_cache_callout / host_cache_impl /
  host_cache_log / host_cache_messages / host_cache_parsers / version）
- 上游套件名：`dhcp-host-cache-tests` + `dhcp-host-cache-libloadtests`
- 用例宏计数：tests/ 23 + 30 + 87 = 140 + libloadtests/ 4 = 144，无 TEST_P、无 DISABLED_
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 插件行为与测试面特点

**行为**（主机保留缓存，BaseHostDataSource 的内存实现）：

- host_cache 是 Kea 的 host data source 插件：把（可能很慢的）主机保留后端
  （数据库/CB）的查询结果缓存在内存容器（Boost multi index）里，同一保留第二次
  查询直接命中缓存，不再走后端。容器带两个额外索引：按最后使用顺序的 sequenced
  索引与按条目定位的 hashed 索引。
- 通过控制通道命令管理：`cache-size` / `cache-clear` / `cache-flush` /
  `cache-get` / `cache-get-by-id` / `cache-write` / `cache-insert` / `cache-load` /
  `cache-remove`（9 个命令 callout）。
- **双协议**：可同时加载进 kea-dhcp4 与 kea-dhcp6（libloadtest `validLoad`
  实测两者均成功；这是与 v4-only 的 bootp 插件的显著差异）。

**测试面**：144 例全部为纯逻辑用例——容器索引、命令 callout（含参数与错误
分支、自产 dump.json/source.json 数据文件并清理）、CacheHostDataSource 接口
（v4/v6 按 HWAddr/ClientId/DUID/CircuitId 查询、FQDN、多个保留冲突、
deleteByAddr/deleteById 等），其中 42（host_data_source）+ 14（command）= 56 例
为 MultiThreading 模式变体（*MultiThreading 后缀，与基础用例成对）。
无 SOCK_RAW、无特权依赖（源码 grep 零命中 geteuid/fork/system/popen），
OHOS 沙箱下**零 root 零 SKIP 全实跑**（与 ping-check 48 个 Root 组用例
SKIP 形成对比；实测结果见「真机验证」节）。与 bootp 的差异：bootp 为
DHCPv4 单协议插件，host_cache 为 v4/v6 双协议插件，加载能力由 libloadtest
的 `validLoad`（双协议加载成功）与 `invalidDaemonLoad`（ctrl-agent/ddns/
bogus 失败）两侧固证。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/host_cache/libdhcp_host_cache.so \
        src/hooks/dhcp/host_cache/tests/dhcp-host-cache-tests \
        src/hooks/dhcp/host_cache/libloadtests/dhcp-host-cache-libload-tests`
   （配方内以 `meson compile -j 8` 限并发：OHOS app 沙箱进程配额，见问题 11）
4. `meson test -v dhcp-host-cache-tests dhcp-host-cache-libloadtests`

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
| 12 | meson test `dhcp-host-cache-tests` 1 例失败：`CommandTest.writeEnvVarOverride`（command_unittests.cc:160/166/169/717，应答 `Unable to open file '/tmp/dump.json' for writing.`） | 该测试把 `KEA_DHCP_DATA_DIR` 覆盖为 **`/tmp`** 并真实落盘 dump.json；OHOS 真机 `/tmp` 是只读 rootfs 挂载（`touch /tmp/x` 实测 `Read-only file system`，目录属 root:root 出厂镜像），文件必然打不开 | 补丁 `0005-src-hooks-dhcp-host_cache-tests-command_unittests.cc.patch`：覆盖值改为 `TEST_DATA_BUILDDIR`（测试自身 meson 已定义 = 测试构建目录，可写），`EXPECT_EQ` 同步。`PathChecker::getPath` 逐字返回 env 值（仅去尾部 `/`），与安装常量 `DHCP_DATA_DIR`（@SHAREDSTATEDIR@）不同——env 覆盖语义与判别力保留。真机单测复验 140/140 通过（补丁为通用鲁棒性修复，Linux 桌面同样成立） |

## 真机验证

2026-10-02 真机（HarmonyOS PC aarch64，conan 2.29.1，profile ohos-aarch64）。
首轮 `ohc-run.py conan-verify` 全树编译零错误，meson test 144 例中 1 例失败
（`CommandTest.writeEnvVarOverride`：/tmp 只读，见问题 12）；补丁 0005 落地后
设备侧单测复验 `meson test` 双套件 2/2 OK（140/140 + 4/4），随后带补丁干净
重跑 `conan-verify` **G0-G4 + L2-L5 全 PASS**，验证报告 20:16:34 生成，
Verdict: PASS，R46 终态 result.json 已上报（draft:false）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ | E490 提示为 autotools 启发式误报（本配方 meson，无 configure 脚本），不影响 |
| G1 | ✅ | 配方完整性检查全过 |
| G2 | ✅ | conan create 干净构建（全树 [1432/1432] 链接零错误）+ build() 内 meson test 实跑 + test_package |
| G3 | ✅ | R26 系统同名库隔离验证通过 |
| G4 | ✅ | 产物完整性检查通过；「无法找到程序包 ID」为框架已知引用口径提示（verify 按 @ohc/stable 查询、创建引用为 @ohpcd/stable，与 wayland-protocols 等配方同一表现），不影响判定 |
| L2/L4/L5 | ✅ | 框架在非默认 cache 路径下按“无 cache 路径”跳过深度检查并记 PASS（与家族配方同一运行环境行为） |

真机实测数据（reports/conan-create.log）：

- **meson test 两套件**：`dhcp-host-cache-tests` 140 例 + `dhcp-host-cache-libloadtests`
  4 例，**PASSED 144 / SKIPPED 0 / FAILED 0**（`[ PASSED ] 140 tests` +
  `[ PASSED ] 4 tests`，`Ok: 2 Fail: 0`）。140 例为纯逻辑用例（容器索引 /
  9 个 cache-* 命令 callout / CacheHostDataSource 查询接口，含 56 个 MultiThreading
  模式变体），含补丁 0005 落地后恢复实跑的 `CommandTest.writeEnvVarOverride`；
  libloadtests 4 例经 hook 框架真实 dlopen 插件（`validLoad` 双协议：同时加载进
  kea-dhcp4 与 kea-dhcp6）
- **test_package 3/3**：
  - test_host_cache_hook：dlopen 加载成功（`libdhcp_host_cache.so loaded (hooks version 30003)`）→ OK
  - test_ohos_platform：ELFCLASS64 / EM_AARCH64 / PT_DYNAMIC ✓；
    **DT_NEEDED 11 项** = kea 闭包 9（libkea-dhcpsrv.so.131 / process.so.91 /
    dhcp.so.109 / hooks.so.121 / cc.so.83 / asiolink.so.88 / log.so.75 /
    util.so.102 / exceptions.so.45）+ libc++_shared.so + libc.so（无 glibc/libstdc++ 命名）→ OK
  - test_ohos_runtime：包内 Kea 运行库 **40 found / 40 loaded**，
    闭包驻留后 hook 仍可加载、契约符号可解析 → OK
- **产物**：`lib/kea/hooks/libdhcp_host_cache.so`（394 KB / 403904 字节）+ Kea 运行时闭包
  40 文件（20 库 × soname 名 + 全版本名）
- **0 字节落盘自愈**：本次验证 package() 复核零命中（无 0 字节 WARNING 日志；
  自愈机制为家族配方继承的兜底项，test_ohos_runtime 40/40 dlopen 证明包内闭包完整）

运行环境备注（非配方知识）：源码 tarball 经设备内 127.0.0.1:18080 http 镜像供给
（设备侧 conandata.yml 临时换 URL，本地配方保持官方 URL 不提交，与 flex-option /
bootp 先例一致）；依赖全部命中设备家族缓存
（CONAN_HOME=/storage/Users/currentUser/.conan2），零网络构建。

## 已知限制

无。上游本组件 144 例全部为纯逻辑用例（无 root 用例、无预置外部数据文件），
不存在 ping-check 式 root 用例 SKIP；全树其余测试（Kea 主程序、核心库及其他
hook 组件）不在本配方适配范围（见 MR 正文「测试减少原因」节）。
