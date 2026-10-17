# kea-hook-ddns-tuning 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-02
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: 真机 conan-verify 全绿（Verdict: PASS，2026-10-02）

## 定位与家族复用

`ddns_tuning` 与已合入的 `kea-hook-limits`、`kea-hook-ping-check`、
`kea-hook-flex-option` 同属 Kea 3.0.3 单源码树（`src/hooks/dhcp/ddns_tuning/`
平级目录），平台差异完全相同：4 个补丁**整组逐字节复用**
（0001/0002 与家族模板 kea-hook-limits 一致；0003/0004 与家族配方
kea-hook-ping-check 一致，均作用于同一上游树的同一批文件），零改动，
本插件无新增平台问题。插件本身的源码核对（2026-10-02）：

- 产物 `libdhcp_ddns_tuning.so`（`meson.build` `shared_library('dhcp_ddns_tuning', ...)`，
  6 个 .cc：ddns_tuning / ddns_tuning_callouts / ddns_tuning_log /
  ddns_tuning_messages / expression_cache / version）
- 上游套件名：`dhcp-ddns-tuning-tests` + `dhcp-ddns-tuning-libloadtests`
  （libloadtests 可执行文件名 `dhcp-ddns-tuning-libload-tests`，注意套件名连写）
- 用例宏计数：tests/ 46（ddns_tuning_unittests 32 + expression_cache_unittests 14）
  + libloadtests/ 19（callout4 8 + callout6 8 + load_unload 3）= 65，无 TEST_P
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 插件行为与测试面特点

**行为**（ddns_tuning.dox 官方描述 + callouts 源码核对，6 个 callout，v4/v6 对称）：

- `cb4_updated` / `cb6_updated`：Config Back End 更新指示子网变化时重建表达式缓存
- `dhcp4_srv_configured` / `dhcp6_srv_configured`：服务器重配置时重建缓存
- `ddns4_update` / `ddns6_update`：经 Kea eval 表达式引擎计算主机名（全局
  `hostname-expr` 参数或子网 user-context `ddns-tuning.hostname-expr`，子网级
  优先；结果按子网 `ddns-qualifying-suffix` 限定），并对属于内置 `SKIP_DDNS`
  类的客户端把 fwd-update / rev-update 方向标志置否（跳过 DDNS 更新）
- 表达式缓存按子网 ID 键控（`ExpressionCache`），支持 flush / 重填充，
  多线程模式兼容（dox 明示）

**测试面**：46 + 19 = 65 例全部为纯逻辑用例——表达式解析/求值、配置解析矩阵、
子网缓存场景、callout handle 驱动（`ddns_tuning_unittests.cc` 32 例为
DdnsTuningImplTest4/6 × 8 场景 × regular/MultiThreading 变体；
`expression_cache_unittests.cc` 14 例为 ExpressionCacheTest 7 项 × 2 变体；
libloadtests 19 例经 hook 框架真实 dlopen 插件：callout4/callout6 各 8 例驱动
callout 场景矩阵、`load_unload_unittests.cc` 3 例验证 validLoad4 / validLoad6 /
invalidDaemonLoad）。无 SOCK_RAW、无特权依赖、无外部数据文件（源码 grep 零命中
geteuid/fork/system/popen/tmpfile），OHOS 沙箱下**零 root 零 SKIP 全实跑**
（与 ping-check 48 个 Root 组用例 SKIP 形成对比；实测结果见「真机验证」节）。
与 bootp 的差异：ddns-tuning 为 **v4/v6 双协议**插件（bootp 为 DHCPv4 单协议），
且核心可测面在表达式的配置解析与缓存语义。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/ddns_tuning/libdhcp_ddns_tuning.so \
        src/hooks/dhcp/ddns_tuning/tests/dhcp-ddns-tuning-tests \
        src/hooks/dhcp/ddns_tuning/libloadtests/dhcp-ddns-tuning-libload-tests`
   （配方内以 `meson compile -j 8` 限并发：OHOS app 沙箱进程配额，见问题 11）
4. `meson test -v dhcp-ddns-tuning-tests dhcp-ddns-tuning-libloadtests`

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

2026-10-02 真机（HarmonyOS PC aarch64，conan 2.29.1，profile `ohos-aarch64`）
conan-verify **全绿**（报告 2026-10-02T19:24:24.837195，`reports/conan-verify-report.md`）：

- **八门禁**：G0 知识图谱预查 / G1 配方完整性 / G2 conan create / G3 R26 系统库隔离 /
  G4 产物完整性 + L2/L4/L5 全 PASS，**Verdict: PASS**（E490 autotools 启发式误报为
  家族同款已知项）；R46 终态 result.json 已上报（draft:false），可标记 `status: published`。
- **上游套件（meson test 实跑，G2 内）**：
  - `dhcp-ddns-tuning-tests`：**46/46 PASSED**（3 个 gtest suite，16 ms；
    `[ PASSED ] 46 tests`，零 SKIP 零 FAILED）
  - `dhcp-ddns-tuning-libloadtests`：**19/19 PASSED**（35 ms；Ok: 2 Fail: 0）
  - 合计 **65/65（100%）**，零 root 零 SKIP——与源码分析结论（纯逻辑用例）一致
- **test_package 3/3**（G2 内实跑）：
  - `test_ddns_tuning_hook`：`libdhcp_ddns_tuning.so loaded (hooks version 30003)`，
    load/unload 契约符号解析 OK
  - `test_ohos_platform`：DT_NEEDED closure **11 项** = kea 闭包 9（libkea-dhcpsrv.so.131 /
    process.so.91 / eval.so.84 / dhcp.so.109 / hooks.so.121 / cc.so.83 / log.so.75 /
    util.so.102 / exceptions.so.45）+ libc++_shared.so + libc.so；musl/libc++ 命名校验 4/4 ok
  - `test_ohos_runtime`：包内 Kea 运行时库 **40 found / 40 loaded**（逐个 dlopen RTLD_NOW）
- **构建规模**：ninja 全量 clean 构建 **[1432/1432]**（1229 个 .o）；
  产物 `.so` = **195008 字节**（190.4 KB）。
- **0 字节自愈实测命中**：package() 落盘时 20 个物化 soname 名（`libkea-X.so.N`）
  读出 0 字节（/storage 写回异常），复核逻辑逐条重拷（WARN ×20，与家族配方同一
  现象）；自愈后 package 目录 40 文件 **0 个空文件**，soname 名与构建树真实文件
  **md5 逐字节一致**（抽样 libkea-dhcpsrv.so.131 = 2f6e5377…，hook .so = 15f1b0e5…），
  test_package 闭包 40/40 dlopen 通过。

## 已知限制

无。上游本组件 65 例全部为纯逻辑用例（无 root 用例、无外部数据文件），不存在
ping-check 式 root 用例 SKIP；全树其余测试（Kea 主程序、核心库及其他 hook
组件）不在本配方适配范围（见 MR 正文「测试减少原因」节）。
