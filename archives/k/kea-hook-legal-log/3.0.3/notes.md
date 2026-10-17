# kea-hook-legal-log 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（真机 conan-verify 全绿后改 published）

## 定位与家族复用

`legal_log`（Kea 2.4 起更名 Forensic Log，源码目录 `src/hooks/dhcp/forensic_log`，
产物仍为 `libdhcp_legal_log.so`）与已适配的 `kea-hook-limits`、
`kea-hook-ping-check`、`kea-hook-host-cmds` 同属 Kea 3.0.3 单源码树
（`src/hooks/dhcp/` 下平级目录），平台差异完全相同：补丁 0001-0004 整组复用
（md5 与家族配方逐字节一致），本配方新增补丁 0005（运行时命令 spawn）与
0006（只读系统目录下日志文件打开回退）。插件
本身的源码核对（2026-09-29）：

- 产物 `libdhcp_legal_log.so`（`meson.build` `shared_library('dhcp_legal_log', ...)`，
  9 个 .cc 源文件：command_callouts / lease4_callouts / lease6_callouts /
  legal_log_log / legal_log_messages / legal_syslog / load_unload /
  rotating_file / version）
- 上游套件名：`dhcp-forensic-log-tests` + `dhcp-forensic-log-libloadtests`
  （libloadtests 的可执行文件名是 `dhcp-forensic-log-libload-tests`，上游如此命名）
- 用例宏计数：tests/ 85（command_log 7+3 + legal_log4 17 + legal_log6 27+1 +
  legal_log_mgr 11 + rotating_file 19）+ libloadtests/ 10 = 95，无 TEST_P
- hook 框架版本：`src/lib/hooks/hooks.h` `KEA_HOOKS_VERSION = 30003`

## 测试面特点（与家族其他插件的关键差异）

1. **无 root 组**：全部用例走文件后端（ForensicLog）与内存后端，无原始套接字、
   无真实网络往返；libloadtests 的 4 个数据库用例受 HAVE_PGSQL/HAVE_MYSQL 守卫，
   `-Dmysql/-Dpostgresql=disabled` 下上游构建即不编译（属上游按配置裁剪，
   非适配删除用例）。预期 OHOS 沙箱下注册的 91 例全量 PASSED（0 SKIPPED / 0 FAILED）。

2. **rotating_file 三 spawn 用例真实执行脚本**：`RotatingFileTest.prerotateActions` /
   `postrotateActions` / `prerotateAndPostrotateActions` 通过 `ProcessSpawn` 实际
   运行 `forensic_prerotate_test.sh` / `forensic_postrotate_test.sh`（configure_file
   copy 自 `.sh.in` 模板，`#!/bin/sh` + `cp "${1}" "${1}-prerotate-completed"`），
   并以脚本副作用文件的存在性断言轮转成功——在 OHOS 内核拒绝 shebang execve 的
   前提下，这是本插件区别于家族其他 hook 的**运行时**（而非 configure 期）脚本
   执行点，由补丁 0005 处理（见问题 12）。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `ninja src/hooks/dhcp/forensic_log/libdhcp_legal_log.so \
        src/hooks/dhcp/forensic_log/tests/dhcp-forensic-log-tests \
        src/hooks/dhcp/forensic_log/libloadtests/dhcp-forensic-log-libload-tests`
   （配方内以 `meson compile -j 8` 限并发：OHOS app 沙箱进程配额，见问题 11）
4. `meson test -v dhcp-forensic-log-tests dhcp-forensic-log-libloadtests`

## 遇到的问题与解决方案

问题 1-11 为家族配方已解决的平台问题（同一上游树、同一差异），对策一一沿用；
问题 12 为本插件独有的运行时 spawn 问题：

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
| 12 | `dhcp-forensic-log-tests` 中 RotatingFileTest 的 prerotateActions / postrotateActions / prerotateAndPostrotateActions 三用例 FAIL：`waitForFile` 超时，脚本副作用文件（`*-prerotate-completed`）始终不出现 | `RotatingFile::rotateFiles()` 经 `ProcessSpawn`（`src/lib/asiolink/process_spawn.cc`：fork + **execve** + `_exit(EXIT_FAILURE)`，无 shell 回退）运行 prerotate/postrotate 命令；命令是 shell 脚本（`forensic_*_test.sh`），OHOS 内核拒绝 shebang 脚本 execve → 子进程 execve EACCES 即 `_exit`，父进程 ASYNC 模式不感知失败 | 补丁 `0005-src-hooks-dhcp-forensic_log-rotating_file.cc.patch`（本配方新增）：`__linux__ && !__GLIBC__` 守卫下把命令经 `/bin/sh` 路由——`ProcessArgs` 改为 `[脚本路径, getFileName()]`、命令改为 `/bin/sh`，脚本内 `$1` 语义与直接 execve 完全一致；glibc/Linux（上游 CI 环境）保留原 execve 路径（非脚本命令同样可用） |
| 13 | `dhcp-forensic-log-tests` 中 `LegalLogMgrTest.pathEnvVarOverride` FAIL（真机首轮 84/85）：fixture 设 `KEA_LEGAL_LOG_DIR=/tmp` → `addBackend` 建后端时 `RotatingFile::openInternal()` 打开 `/tmp/kea-legal.<日期>.txt` 失败，抛 `LegalLogMgrError: cannot open file ... Read-only file system` | OHOS app 沙箱把系统目录（`/tmp` 等）以只读挂载；上游测试（与 glibc/Linux 生产环境一致）假设 `/tmp` 可写。`getLogPath()` 的字符串校验（PathChecker）与 BadValue 消息必须保持原样（测试 line 215 断言消息文本），因此重定向只能落在**文件打开层** | 补丁 `0006-src-hooks-dhcp-forensic_log-rotating_file.cc.patch`（本配方新增）：`__linux__ && !__GLIBC__` 守卫下，打开失败且 `errno ∈ {EROFS, EACCES}` 时回退到 `$HOME/.kea-legal-log/`（路径中 `/` 转 `_` 防碰撞，mkdir 幂等）；配置字符串原样保留，glibc/Linux 路径零扰动。轮转 reopen 时按同一映射落回同一 scratch 文件，行为一致 |

## 验证记录

（真机二轮，2026-09-29，含补丁 0006）

- **结果**: conan-verify G0-G4 + L2-L5 全 PASS，VERIFY-RC=0；可标记 status: published
- **meson test dhcp-forensic-log-tests**: `[  PASSED  ] 85 tests`（0 failed / 0 skipped）
- **meson test dhcp-forensic-log-libloadtests**: `[  PASSED  ] 6 tests`（0 failed / 0 skipped）
- **pathEnvVarOverride**: `[ OK ] (66 ms)` — 补丁 0006 回退生效（KEA_LEGAL_LOG_DIR=/tmp → $HOME/.kea-legal-log/，配置路径消息仍为 /tmp）
- **prerotateActions / postrotateActions / prerotateAndPostrotateActions**: `[ OK ]` — 补丁 0005 /bin/sh 路由生效
- **test_package 3/3**: test_legal_log_hook OK（hooks version 30003）；test_ohos_platform 全 ok（ELF64/aarch64/DT_NEEDED 命名）；test_ohos_runtime 闭包逐个 dlopen ok
- **报告**: reports/conan-verify-report.md（Verdict PASS；conan-create.log 构建日志按规范不随档提交，留存设备端）
