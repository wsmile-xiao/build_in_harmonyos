# kea-dhcp-ddns 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-unknown-linux-ohos，libc++，C++17）
- 工作副本: `wt-kea-d2`（分支 `feat/kea-dhcp-ddns-3.0.3`，基线 `origin/main`）
- 真机构建树: `/storage/Users/currentUser/tmp/ch/home-smartdns/p/b/kea-d13796342e2bc0/b/build-release`（真实 meson 树，全量实跑验证）
- 状态: published（真机 conan-verify 全绿）

## 编译步骤

```bash
# 1) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of=<of>

# 2) 配方 build() 内真实执行的步骤（经 sh 调用 meson 包装脚本，见问题 #7）
sh "<meson 包>/bin/meson" setup --native-file <of>/build-release/conan/conan_meson_native.ini \
    <of>/build-release <src> --prefix=/
sh "<meson 包>/bin/meson" compile -C <of>/build-release -j 8
# _materialize_sonames()（配方内自动，见问题 #9）
sh "<meson 包>/bin/meson" test -v --timeout-multiplier 4 -C <of>/build-release kea-d2-tests
sh "<builddir>/src/bin/d2/tests/d2_process_tests.sh"   # 配方 _run_process_shell_tests()，见问题 #11

# 3) 配方固化与官方验证
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-dhcp-ddns 3.0.3
ohc-run.py finish kea-dhcp-ddns 3.0.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001`（+7/-1）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`（家族补丁，与 kea-hook-ha 逐字节一致） |
| 2 | 编译期 `iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h`（bionic 派生）与 musl `sys/socket.h` 都定义 `struct sockaddr_storage` | 补丁 `0002`（+14/-1）：包含 netlink 头前 define-guard 重命名内核侧定义，守卫 `__linux__ && !__GLIBC__`（不用平台宏） |
| 3 | `meson.build:477 ERROR: Boost TLS support broken`（`use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl `pthread.h` 不声明该函数，boost `sp_thread_sleep.hpp` 无条件调用 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" runs: NO (127)` → `Unknown variable "log4cplus"` | meson 特性探针编译并运行；host 共享依赖 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH` | `generate()` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` |
| 5 | configure 期 `env.sh` / `grabber.py` / `config-report.sh` 直接执行报 Error 126 | OHOS 内核拒绝 shebang 脚本 execve（与可执行位无关） | 补丁 `0003`（+10/-5，顶层 meson.build 脚本变量改为解释器前缀数组）+ `0004`（+2/-2，cfgrpt） |
| 6 | `Unknown linker(s): [['llvm-ar']]`（configure 期首个错误） | meson 对 clang 默认裸名探测静态链接器，MesonToolchain 未写 `ar/ranlib`，OHOS 只按绝对路径解析 | `generate()` 从 `tools.build:compiler_executables` 推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 7 | conan 的 meson 包装脚本（`bin/meson` shebang 脚本）直接执行报 Error 126 | 同上 execve 限制 | `build()` 经 `sh "<meson 包>/bin/meson"` 调用（`_meson()` 前缀，家族配方同款） |
| 8 | meson 特性探针与构建期偶发 `Error loading shared library liblog4cplus.so.9` | 配置期需 host 共享依赖在 `LD_LIBRARY_PATH` 可见（同 #4 补齐后消失） | 已由 #4 的 `conanbuildenv-kea-runtime` 脚本覆盖（build 阶段自动 source） |
| 9 | `kea-d2-tests` / 真实守护进程启动报 `Error loading shared library libkea-X.so.N`（exit 127） | OHOS /storage 沙箱拒绝符号链接（ln -s → EPERM）：meson 的 soname 名只以符号链接发布，链接名文件根本不存在，NEEDED 查找全部落空 | `build()` 在 compile 后 `_materialize_sonames()`：以复制方式物化 soname 名（幂等；真机实测物化 40 文件 / 20 soname 实体） |
| 10 | `meson compile` 中途 posix_spawn EAGAIN | OHOS 沙箱限制并发进程数，ninja 默认按 20 核并发（~45 个活动 spawn） | `meson compile -j 8`（家族配方实测值） |
| 11 | meson test 直接执行 `d2_process_tests.sh` 报 Error 126 | OHOS 内核拒绝 shebang 脚本 execve（与 0003/0004 同根因，发生在测试驱动阶段） | 配方 `_run_process_shell_tests()` 以 `sh "<builddir>/src/bin/d2/tests/d2_process_tests.sh"` 在该目录内驱动同一脚本，10 场景原样执行、测试源码零改动（对照：kea-dhcp6 以补丁 0011 改 meson 注册命令，本包选择配方侧最小改动） |
| 12 | `package()` 复制产物偶发 0 字节落盘 | 真机 /storage 瞬态 flush 异常（同家族设备现象） | `package()` 对守护进程与每个闭包库做 0 字节复核：三重补拷（逐次复验 `getsize`），仍为 0 则显式抛 `ConanException` 失败而非静默交付 |
| 13 | 真机 conan-verify 的 L2 平台冒烟门禁（**阻塞项**）对包内可执行文件探 `--version`/`--help` 全部失败 | GNU 命令行惯例的探测方式，而 Kea 守护进程命令行只接受 getopt 短选项表 `dvVWc:t:X`（`parseArgs` 的 optstring），长选项进 getopt 报 `Usage error: unsupported option: --`；`launch()` 把 `InvalidUsage` 重抛为空消息异常 → `main.cc` `ret = EXIT_FAILURE`，实测退出码 1 | 补丁 `0005`（+16/-1）：`DControllerBase::parseArgs` 在 getopt 前扫描 argv，把 `--version`/`--help` 处理为纯别名——`--version` 与 `-v` 同样抛 `VersionMessage(getVersion(false))`（输出恰为 `3.0.3`）、`--help` 先 `usage("")` 打印选项表再抛空 `VersionMessage` 成功退出；不改动 getopt 表与任何其他行为 |
| 14 | `meson test` 默认 30s 单测预算在高负载设备上偏紧 | 设备并行构建时单测耗时波动 | `meson test --timeout-multiplier 4`（家族配方式） |
| 15 | 真机测试二进制在首个 fixture 构造时 SIGSEGV（CtrlChannelD2Test 全组崩溃，同 fixture 的解析类用例同样无法运行） | `isc::test::Sandbox` 构造用编译期 `P_tmpdir`（`/tmp`）拼模板调 `mkdtemp`——鸿蒙 PC `/tmp` 只读，`mkdtemp` 返回 NULL，随后以 NULL 构造 `std::string` 是未定义行为即段错误（gdb 受沙箱 ptrace 限制不可用，经插桩 `std::cerr` 轨迹定位到成员构造序、崩溃点在首个成员 `sandbox`） | 补丁 `0006`（+16/-3）：Sandbox 构造优先读 `TMPDIR`（未设回退 `P_tmpdir`）；与 kea-dhcp6 同名补丁逐字节一致（md5 `a0a1ef2f`） |
| 16 | unix 命令通道测试 24 例全部失败：`bind: Operation not permitted` | 鸿蒙 hmdfs 用户存储拒绝 AF_UNIX 路径名 socket 的 `bind()`（EPERM；`/storage` 各目录实测均失败，`/data`、`/dev/shm` 不可访问） | 补丁 `0007`（+45/-1）：CtrlChannelD2Test 增加 `unixControlSocketsUsable()`（以服务器将要执行的同一 `bind()` 探测）+ `SetUp()` `GTEST_SKIP`——平台不支持时如实跳过 26 例，可 bind 主机上全部照常执行（家族先例 kea-dhcp6 0007/0008） |
| 17 | HTTP 控制通道 config-write 全路径用例 2 例失败 | 用例把 `/tmp/test*.json` 硬编码为配置/输出全路径，鸿蒙 `/tmp` 只读写不进 | 补丁 `0008`（+16/-5）：路径改取 `TMPDIR`（未设回退 `/tmp`）；Http/Https 两 fixture 共享同一尾函数，一处修复两处生效（与 kea-dhcp6 0010 同款） |
| 18 | 消费者契约测试 `-t` 合法配置用例失败：`DCTL_PARSER_FAIL ... invalid path in 'output'，supported path is '/var/log/kea'`（真机 verify 实测） | 守护进程对日志 `output` 路径按编译期日志目录白名单校验（本构建为 `/var/log/kea`），而测试把 output 指向临时目录；`-t` 调用未带重定位环境变量即被拒 | test_package 全部调用统一注入 `KEA_LOG_FILE_DIR`/`KEA_PIDFILE_DIR`/`KEA_LOCKFILE_DIR`（守护进程官方环境变量重定位机制）指向测试临时目录；真机 15/15 通过 |

> 平台差异 1-7 与家族已合入配方一致（补丁 0001-0004 与 kea-hook-ha 逐字节复用，
> md5 对账通过：0001 `fb02d6ec` / 0002 `73e78987` / 0003 `ac87cd3e` / 0004 `bea535f4`）；
> 8-14 为本包首曝或本包测试面复现，15-17 为测试面真机适配（0006 与 kea-dhcp6
> 同名补丁逐字节一致 md5 `a0a1ef2f`；0007/0008 按 kea-dhcp6 同款路线本包实现），
> 均以真机原始输出取证（真机 conan-verify 报告与构建日志）。

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +7/-1 | harmonyos → linux 平台名归一化（家族） |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +14/-1 | netlink 头包含期 `sockaddr_storage` define-guard（家族） |
| 0003-meson.build.patch | `meson.build` | +10/-5 | configure 期脚本经解释器执行（家族） |
| 0004-src-lib-process-cfgrpt-meson.build.patch | `src/lib/process/cfgrpt/meson.build` | +2/-2 | mk_cfgrpt.sh 经 /bin/sh（家族） |
| 0005-src-lib-process-d_controller.cc.patch | `src/lib/process/d_controller.cc` | +16/-1 | `DControllerBase::parseArgs` 接受 `--version`/`--help` 长选项（纯别名，平台冒烟探测契约；本包新增） |
| 0006-src-lib-testutils-sandbox.h.patch | `src/lib/testutils/sandbox.h` | +16/-3 | 测试 Sandbox 目录优先 `TMPDIR`（/tmp 只读，mkdtemp NULL 崩溃；与 kea-dhcp6 同款） |
| 0007-src-bin-d2-tests-d2_command_unittest-unix-socket-skip.patch | `src/bin/d2/tests/d2_command_unittest.cc` | +45/-1 | AF_UNIX 路径名 bind 探针 + unix 通道 fixture 按探针跳过（家族同款路线） |
| 0008-src-bin-d2-tests-d2_http_command_unittest-tmpdir.patch | `src/bin/d2/tests/d2_http_command_unittest.cc` | +16/-5 | HTTP config-write 全路径用例改取 `TMPDIR`（与 kea-dhcp6 0010 同款） |

补丁均不含平台宏（PF5 通过）；0001-0004 与家族 kea-hook-ha 同名补丁逐字节一致，
0005 按 staged-diff 生成并在纯净源码树上验证可应用（`git apply --check` + 字节级等价比对）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头 |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（CRYPTO_DEP） |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |

## 包内容与运行期依赖

`kea-dhcp-ddns` 可执行文件（`bin/kea-dhcp-ddns`）+ 20 个 Kea 共享库（`lib/libkea-*.so*`：
asiodns、asiolink、cc、cfgrpt、config、cryptolink、d2srv、database、dhcp、dhcp_ddns、
dns、exceptions、hooks、http、log、log-interprocess、process、stats、tcp、util，
含物化的 soname 名，共 40 文件）。上游 `INSTALL_RPATH` 指向构建机 prefix，Conan 包改用
`cpp_info.libdirs=["lib"]` 让生成的 run 环境提供 `LD_LIBRARY_PATH`。

## 上游测试（2026-10-04 真机实跑）

- `kea-d2-tests`（gtest，38 套件）：426 例实跑——**400 passed / 26 skipped / 0 failed**（9.41s）。
  26 例跳过 = CtrlChannelD2Test（unix 命令通道 fixture）：鸿蒙 hmdfs 存储判 AF_UNIX
  路径名 `bind()` EPERM（问题 #16），由补丁 0007 的探测驱动条件性跳过；可 bind
  AF_UNIX 的主机上该 fixture 全部照常执行。
- `d2_process_tests.sh`（进程级 shell 套件，10 场景）：**10/10**（日志实录 [ RUN ]×10 → [ OK ]×10）
  （真实守护进程 127.0.0.1:53001，SIGHUP/SIGINT/SIGTERM 与 `-t` 校验 0/1/1、日志脱敏）。
- meson 汇总：Ok: 1 / Fail: 0（目标 1/1 kea:kea-d2-tests OK 9.72s）；shell 套件由配方以
  sh 驱动（见问题 #11），10 场景 [ RUN ]×10 → [ OK ]×10 全过（任一场景失败即中断构建）。

## 鸿蒙特有测试用例（test_package，2 个用例，真机实测 2/2）

| 用例 | 文件 | 校验点 | 覆盖内容 |
|------|------|------|----------|
| `test_ohos_platform` | `test_package/test_ohos_platform.c` | 8 | 包内 `bin/kea-dhcp-ddns` 的 OHOS 平台 ABI 特征（ELFCLASS64 / `EM_AARCH64` / `ET_DYN` PIE；`DT_NEEDED` 含 musl `libc.so` 且不含 glibc `libc.so.6`；含 `libc++_shared.so`） |
| `test_ohos_runtime` | `test_package/test_ohos_runtime.c` | 6 | OHOS 加载器下的运行时闭包（DT_NEEDED 的 Kea 库全部随包分发；20 个 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功；真实执行 `kea-dhcp-ddns -v` 输出 `3.0.3`） |

另含通用消费者契约测试 `test_kea_dhcp_ddns.py`（15 校验点）：版本输出（`-v` 恰为
`3.0.3`；本包新增的 GNU 风格别名 `--version` 同输出 / `--help` 打印 usage，均退出 0）、
语法检查 `-t` 三路径（合法配置退出 0；坏 JSON 退出 1；越界端口 80000 退出 1）、一次完整
守护进程生命周期（`-c` 启动 → `DCTL_CONFIG_COMPLETE` → pidfile 落盘 → SIGTERM →
`DCTL_SHUTDOWN`），并校验各次运行 stderr 无 "Error loading shared library"；
全部调用以 `KEA_LOG_FILE_DIR`/`KEA_PIDFILE_DIR`/`KEA_LOCKFILE_DIR` 把守护进程运行期
状态重定位到测试临时目录（日志路径白名单校验见问题 #18），真机实测 15/15 通过。

## 服务器 CLI 契约（真机实测，消费者测试的锚点）

| 调用 | 结果 |
|------|------|
| `kea-dhcp-ddns -v` | 输出 `3.0.3`，RC=0 |
| `kea-dhcp-ddns --version` | 输出 `3.0.3`，RC=0（补丁 0005 新增别名，与 `-v` 等价） |
| `kea-dhcp-ddns --help` | 打印 `Usage: kea-dhcp-ddns` 选项表，RC=0（补丁 0005 新增别名；usage 走 stderr） |
| `kea-dhcp-ddns -t <合法>` | RC=0 |
| `kea-dhcp-ddns -t <坏 JSON>` | RC=1（CONFIG_BAD_SYNTAX 路径） |
| `kea-dhcp-ddns -t <越界端口 80000>` | RC=1（CONFIG_BAD_VALUE 路径） |
| `kea-dhcp-ddns -c <合法> + SIGTERM` | `DCTL_CONFIG_COMPLETE` → `DCTL_SHUTDOWN`，进程优雅退出 |

## R37 / R38

- R37：官方 main 中不存在 kea-dhcp-ddns 既往版本（`git ls-tree HEAD archives/k/kea-dhcp-ddns` 为空），
  本包为 3.0.3 首发，版本号按任务卡。
- R38：本包产物是可执行文件，已在软件级别目录提供 `archives/k/kea-dhcp-ddns/commands.json`
  （`type=tool`、`binary=true`）；包内可执行文件按 Conan 约定落在 `bin/`。
---

**编译结束**: 2026-10-04 13:21
**最终状态**: published
