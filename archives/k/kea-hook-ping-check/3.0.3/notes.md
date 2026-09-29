# kea-hook-ping-check 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 定位与家族复用

`ping_check` 与已适配的 `kea-hook-limits` 同属 Kea 3.0.3 单源码树
（`src/hooks/dhcp/` 下平级目录），平台差异完全相同：两处补丁作用于
顶层 `meson.build` 与 `src/lib/dhcp/iface_mgr_linux.cc`，与家族模板
kea-hook-limits 逐字节一致，直接复用。插件本身的源码核对（2026-09-26）：

- 产物 `libdhcp_ping_check.so`（`meson.build` `shared_library('dhcp_ping_check', ...)`，
  11 个 .cc 源文件：config_cache / icmp_msg / ping_channel /
  ping_check_callouts / ping_check_config / ping_check_log /
  ping_check_messages / ping_check_mgr / ping_context / ping_context_store / version）
- 上游套件名：`dhcp-ping-check-tests` + `dhcp-ping-check-libloadtests`
- 用例宏计数：tests/ 90（Root 组 46 + 常规 44）+ libloadtests/ 4 = 94，无 TEST_P
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/ping_check/libdhcp_ping_check.so \
        src/hooks/dhcp/ping_check/tests/dhcp-ping-check-tests \
        src/hooks/dhcp/ping_check/libloadtests/dhcp-ping-check-libload-tests`
4. `meson test -v dhcp-ping-check-tests dhcp-ping-check-libloadtests`

## 遇到的问题与解决方案

与家族模板 kea-hook-limits 完全同源的五个平台问题（同一上游树、同一差异），
对策一一沿用：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running llvm-ar --version gave [Errno 2]` | 宿主环境 `AR=llvm-ar`（裸名）被 meson 静态链接器探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行**不解析 PATH**，裸名直接 ENOENT（`which llvm-ar` 却能找到） | `generate()` 从 `tools.build:compiler_executables` 的编译器目录推导 `llvm-ar`/`llvm-ranlib` **绝对路径**写入 machine file `[binaries]` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 meson 的 `build_machine.system()` 返回 `harmonyos`；Kea 白名单只含 linux/bsd/solaris/darwin | 补丁 `0001-meson.build.patch`：`SYSTEM == 'harmonyos'` 归一化为 `'linux'`（一处修改使 `src/lib/dhcp` 等所有子目录走 Linux 分支） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（首错 `boost/core/detail/sp_thread_sleep.hpp:73: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate()`（实测 grep 计数 0），boost 1.85 的 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` + `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | meson 的“编译并运行”探针在 native 构建下真实执行；探针链接的 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH`（127 = 动态加载失败） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` 聚合进 `conanbuild.sh` |
| 5 | `ninja FAILED: src/lib/dhcp/libkea-dhcp.so.109.0.0.p/iface_mgr_linux.cc.o` → `.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h:377` 都定义 `struct sockaddr_storage`；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`：包含 netlink 头前后 `#define sockaddr_storage __linux_uapi_sockaddr_storage` / `#undef`，守卫用 `__linux__ && !__GLIBC__`（标准 libc 鉴别宏，**不含平台宏**） |
| 6 | `meson setup` 报 `/bin/sh: <conan 缓存>/bin/meson: Permission denied`（conan create Error 126） | Conan 的 meson 包 `bin/meson` 是 **shebang shell 包装脚本**（`exec python3 "$here/../lib/.../meson.py"`）；OHOS 内核拒绝对脚本的 execve（全设备禁 shebang exec，与 automake 1.19 笔记同根因） | build() 不直接用 Meson helper 执行 meson，改 `sh "<meson 包>/bin/meson" setup/compile/test`（sh 直接读脚本不触发 execve；内部 exec 的 python3 是 ELF 可执行）——命令行参数与 conan 2.29 helper 完全一致（同 --native-file/--prefix=/）。ninja 由 PATH 上的系统 ELF（/data/service/hnp/bin/ninja）提供，clang 编译出的产物 ELF 在本域可正常 exec（真机实测 hw 探针 RC=0）。二轮真机验证中 setup 全程跑通（依赖探针全 YES），修法确认有效 |
| 7 | `meson setup` 收尾处 `Running command: scripts/env.sh KEA_PKG_TYPE_IN_CONFIGURE` → `ERROR: Unhandled python OSError`（conan create Error 13） | Kea 顶层 meson.build 在 configure 期直接 `run_command(ENV, ...)` 执行 `scripts/env.sh`（探包类型）与 `scripts/grabber.py`（src/share/api、yang、doc/sphinx 等处的文件列表探针）——均为带 shebang 的脚本，OHOS 内核拒 execve，与 #6 同根因但发生在**上游源码内部** | 补丁 `0003-meson.build.patch`：把三个脚本变量的定义改为**解释器前缀数组**（`ENV = ['/bin/sh', <脚本路径>]`、`GRABBER = [find_program('python3').full_path(), <脚本路径>]`），所有调用点仍把变量作为 run_command 首参传入、无需逐点修改；meson 数组首参语法已真机探针验证（RC_SH_OK/RC_PY_OK 实测）。install 阶段脚本（install-meson-info.sh/install_docs.py）不触发：本配方不用 meson install，package() 手工 copy |
| 8 | setup 全绿后收尾处 `Configuring config.report with command` → `ERROR: Unhandled python OSError`（Error 13，第三轮真机） | meson.build:1025 的 `CONFIG_REPORT = configure_file(command: [TOP_BUILD_DIR / 'config-report.sh'])` 直接执行**刚生成的**脚本（config-report.sh.in 经 configure_file 生成，内容为纯 printf/heredoc 写配置报告，无嵌套 exec）——同一 shebang execve 家族，但发生在生成的产物脚本上 | 补丁 `0003` 增加第二个 hunk：`command: ['/bin/sh', TOP_BUILD_DIR / 'config-report.sh']`。全树排查（grep run_command/command: 所有 meson.build）确认再无直接脚本 exec：其余调用点（GRABBER 9 处、CD_AND_RUN 测试 env 若干处）全走已修补的数组变量；1136 行的 `run_command(['cat', CONFIG_REPORT])` 为 ELF cat，不受影响。**注意 hunk 2 行号写 1028 而非 1022**：conan 的 patch-ng 引擎按"已打过先前补丁文件的源"解释 hunk 行号（0001 在 165 行处 +6 行），1022+6=1028；该坐标下 patch-ng 与 git apply 都能命中（位置 1028 与 1033 的内容相同，均为 CONFIG_REPORT 上下文，实测 patch-ng 模拟通过） |
| 9 | setup 进入 `src/lib/process/cfgrpt` 后 `Configuring config_report.cc with command` → `ERROR: Unhandled python OSError`（Error 13，第四轮真机） | `src/lib/process/cfgrpt/meson.build:4` 的 `command: [mk_cfgrpt, '@INPUT@', '@OUTPUT@']` 直接执行 `tools/mk_cfgrpt.sh`（把 config.report 文本嵌进 config_report.cc；纯 echo/printf 处理，无嵌套 exec）——与 #6/#7/#8 同根因，但位于子目录构建文件 | 补丁 `0004-src-lib-process-cfgrpt-meson.build.patch`：`command: ['/bin/sh', mk_cfgrpt, '@INPUT@', '@OUTPUT@']`。该文件未被任何先前补丁触碰，行号按原始坐标即可（patch-ng 本地模拟验证 OK）。至此整树 configure 期脚本 exec 全部清零（fuzz 子目录由 FUZZ_OPT 门控不评估；cppcheck/grammar 等 run_target 为 build-time，本配方不触发） |
| 10 | meson test 两个套件 0.05s 内双双 FAIL，exit status 127；stderr 刷屏 `Error loading shared library libkea-dhcpsrv.so.131:`（空原因）+ `Error relocating ...: _ZNK3isc9Exception4whatEv: symbol not found`（第五轮真机） | OHOS /storage 沙箱**拒绝创建符号链接**（`ln -s` → Permission denied，构建树 find -type l = 0）：meson 用 `version: '131.0.0'` 构建并只以**符号链接**发布 soname 名 `libkea-X.so.131` → 链接名文件从不存在，加载器按 NEEDED 名（soname）找文件必然落空，先报"库加载失败"再级联成符号重定位失败。家族模板 kea-hook-limits 之所以没踩中：它的 build() 不跑 meson test（不加载测试二进制），package() 里还有 islink 分支的复制兜底 | build() 在 compile 后新增 `_materialize_sonames()`：os.walk 构建树 src/lib，对每个 `libkea-X.so.N.M.K` 实文件以**复制**方式生成 soname 名 `libkea-X.so.N`（shutil.copyfile；普通 Linux 宿主上 meson 已建符号链接则跳过，幂等）。测试二进制与 package() 遍历（startswith "{lib}.so."）都自动吃到这些 soname 副本，包内闭包同样受益。**第六轮真机 meson test 两套件全绿（Ok: 2 / Fail: 0，90 例 PASSED 42 + SKIPPED 48；libloadtests 4/4），修法确认有效**。另：真机曾出现包内 soname 文件落盘 0 字节的瞬时异常（/storage 写回问题，根因未复现），package() 收尾已加空产物复核自愈（0 字节即从构建树重拷并 WARNING），test_package 40 库逐个 dlopen 兜底拦截 |

## 插件特有风险点：Root 用例与原始套接字

ping_check 与 limits 的关键差异在测试面：插件的 `IcmpSocket` 是 header-only
模板类（`icmp_socket.h`，无 .cc，直接编进库），底层是
`boost::asio::ip::icmp::socket`——Linux 上即
`socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)` 原始套接字。上游在测试里把需要
真实 ICMP 往返的用例标记为 root 组（`RootICMPSocketTest` 2 +
`RootPingChannelTest` 18 + `RootPingCheckMgrTest` 26 = 46 例），上游 CI 以
root 运行；`-Dsudo=enabled` 时上游会把 root 组从主套件剔除、改由 sudo 另跑。

OHOS 真机沙箱下这 46 例的处置实测记录见下节。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| boost | 1.85.0 | requires（**必须固定**：1.90 缺 `interprocess_upgradable_mutex.hpp`，1.91 缺 `circular_buffer.hpp`，均为 Kea meson.build 的 required 头） |
| log4cplus | 2.2.0.1 | requires |
| openssl | 3.5.8.1 | requires（默认 crypto 后端） |
| zlib | 1.3.1 | boost 传递依赖 |
| gtest | 1.17.0.1 | test_requires（`-Dtests=enabled` 时） |
| meson | 1.11.0 | tool_requires（须 ≥ 1.10：boost 包无 libboost_system，依赖 meson 的 header-only 模块回退） |

## 验证结果

真机 conan-verify（2026-09-27，OHOS PC aarch64 真机，conan 2.29.1 + clang 15.0.4）：

- **G2 conan create**：meson setup → compile → 上游测试 → package → test_package 全绿。
- **上游测试（build() 内实跑）**：
  - `dhcp-ping-check-tests`：90 例 = **PASSED 42 + SKIPPED 48 + FAILED 0**
    （SKIPPED 48 例全部为 Root 组：RootICMPSocketTest 2 + RootPingCheckMgr 2 +
    RootPingChannelTest 18 + RootPingCheckMgrTest 26。OHOS 沙箱无 CAP_NET_RAW，
    gtest 在 socket(AF_INET, SOCK_RAW, IPPROTO_ICMP) 前置检查处自动 SKIP——
    上游设计就是 root 才跑，跳过=平台预期行为，见「插件特有风险点」节）
  - `dhcp-ping-check-libloadtests`：4 例全 PASSED（exit status 0）
  - 合计：**94 例实跑，46 PASSED，48 SKIPPED，0 FAILED**（manifest 已回填）
- **test_package 鸿蒙特有测试（3/3 通过）**：
  - `test_ping_check_hook`：dlopen(RTLD_NOW) 加载 hook，KEA_HOOKS_VERSION=30003 ✓
  - `test_ohos_platform`：ELF64 + EM_AARCH64 + DT_NEEDED 11 项解析
    （kea 闭包 + libc++_shared.so + libc.so；无 glibc/libstdc++ 命名）✓
  - `test_ohos_runtime`：包内 40 个库（20 soname + 20 全版本名）逐个
    dlopen(RTLD_NOW) 全过，闭包驻留后 hook 仍可加载 ✓
- **Root 用例实测结论**（可复用于家族配方测试面）：OHOS 沙箱下 Root 组的行为
  是 **SKIP 而非 FAIL**，无特权环境无需任何额外处理即可拿到全绿 meson test。

test_ohos_platform 实现中的两个坑（本任务内修复）：
1. 动态字符串表 156KB，缓冲区只给 64KB 会把 strsz 截断，导致所有
   DT_NEEDED 偏移（≈0x25f91 起）超过 strsz 被静默丢弃 → 误报 0 项
   （缓冲区扩至 256KB，偏移检查对真实 strsz 生效）；
2. 静态链接产物可合法地无 libc/libc++ NEEDED 项：检查改为「闭包里有 libc
   类条目才判命名，无条目=静态运行时，跳过并记 info」。
