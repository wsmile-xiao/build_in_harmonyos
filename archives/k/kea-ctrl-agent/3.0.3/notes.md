# kea-ctrl-agent 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published（真机 conan-verify 八门禁全 PASS，Verdict: PASS）

## 定位与家族复用

kea-ctrl-agent（Control Agent）是 Kea 的 REST 控制通道前端：对外提供
HTTP/HTTPS 端点，把远端管理命令转发给 kea-dhcp4/kea-dhcp6/kea-d2 的控制通道，
并自行处理 `config-get` / `config-set` / `status-get` / `shutdown` 等 Control
Agent 原生命令。源码位于 Kea 3.0.3 单源码树 `src/bin/agent/`（与已合入的
kea-hook-* 组件、kea-perfdhcp 同树），上游把可执行文件安装到 SBINDIR。

平台差异与该树其余组件完全相同：0001-0004 四个补丁**整组逐字节复用**
（0001/0002 与家族模板 kea-hook-limits 一致、0003/0004 与 kea-hook-ping-check
一致，均作用于同一上游树的同一批文件），零改动；家族 dhcp6 配方的
getifaddrs 回退补丁仍无需复现——Control Agent 不含 DHCP 接口管理路径，
运行期不构造 `IfaceMgr`。**本组件另新增 3 个测试期补丁**（真机实测暴露）：
`0005`（`src/lib/testutils/sandbox.h`——与 kea-dhcp6 配方对**同一共享测试
辅助文件**的移植逐字节一致：`mkdtemp(P_tmpdir)` 在 /tmp 只读的主机上返回
NULL，`std::string` 空指针赋值即崩溃，改为优先 TMPDIR）、`0006`（本组件
新增：AF_UNIX 路径名 bind 同型探针 + 9 个命令转发用例的 GTEST_SKIP）与
`0007`（本组件新增：测试 socket 拼接路径超 `sockaddr_un::sun_path` 上限时
回退 TMPDIR），详见问题 12/13/14。

二进制形态的差异（对照 hook 组件）：kea-ctrl-agent 是**可执行文件**（非 .so
插件），直接 `DT_NEEDED` 9 个 Kea 库、递归 NEEDED 闭包 16 库（readelf 逐级
解析，实测见「真机验证」节）——Kea 各库以全部已构建库累积链接
（`LIBS_BUILT_SO_FAR`），闭包深于直接 NEEDED，且经 `libkea-hooks` 加载的
插件还会更深，故配方按家族 kea-hook-bootp/kea-hook-ha 同口径分发 Kea 运行时
库全集（20 库 40 文件），以 `package_type = "application"` 打包：可执行文件
按 Conan 约定落 `bin/`（上游 SBINDIR），运行时全集（libkea-*.so*，含物化的
soname 名）随包落 `lib/`，软件目录另有 `commands.json`（R38：可执行工具须在
versions 登记）。

上游核对（2026-10-04）：

- gtest 套件 `kea-agent-tests`（`src/bin/agent/tests/`，`meson.build`
  `protocol: 'gtest'`）：98 个 TEST/TEST_F 宏——ca_cfg_mgr 20、
  ca_command_mgr 15、ca_controller 22、ca_process 2、
  ca_response_creator_factory 1、ca_response_creator 14、get_config 1、
  parser 23；其中 `DISABLED_configParseEmpty` 与 `DISABLED_connectionTimeout`
  为上游自带 DISABLED_ 前缀（gtest 不执行）→ 实测执行 96 例
- 进程级 shell 套件 `ca_process_tests.sh`（`suite: 'shell-tests'`）：7 个具名
  用例——`kea-ctrl-agent.server_pid_file_test`（pid 文件二次启动拒绝）、
  `ctrl-agent.sigterm_test` / `ctrl-agent.sigint_test`（优雅退出）、
  `ctrl-agent.syntax_check_success|bad_syntax|bad_values`（-t 三态）、
  `ctrl-agent.password_redact_test`（口令脱敏：sensitive 隐藏 /
  superadmin 可见）
- 合计源码宏 105，实测执行 103（96 + 7）；其中 9 例命令转发用例为
  **平台探针判定的跳过**（hmdfs 存储拒绝 AF_UNIX 路径名 bind，问题 13），
  其余 94 例（87 gtest + 7 shell）实跑通过、0 失败；2 例上游自带
  DISABLED_ 前缀不执行（与「跳过」分列统计）

## 行为与测试面特点

**行为**（REST 控制通道前端，单一职责）：

- HTTP/HTTPS 控制端点：解析 `Control-agent` 配置（http-host/http-port、
  TLS 参数、clients 列表），校验 basic auth（user / password-file / realm /
  auth-type），把请求体 JSON 转发给 dhcp4/dhcp6/d2 中配置的控制端点，并把
  应答原样回给客户端；
- 原生命令直答：`config-get` / `config-set` / `status-get` / `shutdown` /
  `version-get` 等由 Control Agent 自身处理（不回发上游服务器）；
- 命令路由与应答构造由 ca_command_mgr / ca_response_creator(+factory)
  实现，ca_cfg_mgr 管理自身配置（loggers、hooks-libraries 等）。

**测试面**：98 例 gtest 全部为纯逻辑/本地回环用例——

- ca_command_mgr 15 例：命令转发决策（本地 / 远端 / 拒绝）；其中 9 例走
  unix 控制通道转发——该 9 例在无 AF_UNIX 路径名 socket 支持的主机上按探针
  跳过（问题 13），其余 6 例（含 2 例未注册 socket 的错误路径）照常实跑
  （深构建路径下经补丁 0007 的 TMPDIR 回退保持实跑，问题 14）；
- ca_controller 22 例：控制通道 HTTP 会话（本地回环 HttpConnection）、
  应答构造、非请求错误路径；
- ca_cfg_mgr 20 例 + parser 23 例：Control Agent 配置解析与校验（http、
  auth、loggers、hooks-libraries、TLS 参数）；
- ca_response_creator 14 例 + factory 1 例：坏 JSON / 未注册命令的应答
  与工厂契约；
- ca_process 2 例 + get_config 1 例：进程接口与配置获取。

无 root 用例、无 SOCK_RAW、无外部数据文件依赖（TLS 相关用例仅做参数解析
校验，不出真实 TLS 连接）→ OHOS 沙箱下**零 root 实跑**；唯一平台性限制为
AF_UNIX 路径名 socket（hmdfs 拒绝 bind，问题 13），受影响 9 例按探针跳过。
`ca_process_tests.sh` 7 例以**真实二进制**驱动，测试内自行把
KEA_PIDFILE_DIR / KEA_LOCKFILE_DIR 指向临时目录，同样无需 root
（实测结果见「真机验证」节）。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps
   + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini
   -Dtests=enabled`（配方内以 `sh "<meson 包>/bin/meson"` 包装调用，见问题 6）
3. `meson compile -C <builddir> -j 8`（限并发：OHOS app 沙箱进程配额，
   见问题 11）
4. `meson test -v --timeout-multiplier 4 -C <builddir> kea-agent-tests`
5. `meson test -v --timeout-multiplier 8 --wrapper sh -C <builddir>
   ca_process_tests.sh`（shell 套件经 sh 包装，见问题 6）

## 遇到的问题与解决方案

问题 1-11 为家族配方已解决的平台问题（同一上游树、同一差异），对策一一沿用
（0001-0004 补丁整组复用 + 配方内三处构建级适配）；问题 12/13/14 为**本组件
真机实测新暴露**的测试期平台问题（对策 = 补丁 0005/0006/0007），问题 15 为
干净构建下打包面新暴露（对策 = 配方运行时库全集口径），问题 16/17 为消费者
用例面新暴露（对策 = 用例导出 KEA_LOG_FILE_DIR + 日志落盘校验；控制通道应答
单元素数组解包）：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running llvm-ar --version gave [Errno 2]` | 宿主环境 `AR=llvm-ar`（裸名）被 meson 静态链接器探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行**不解析 PATH**，裸名直接 ENOENT（`which llvm-ar` 却能找到） | `generate()` 从 `tools.build:compiler_executables` 的编译器目录推导 `llvm-ar`/`llvm-ranlib` **绝对路径**写入 machine file `[binaries]` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 meson 的 `build_machine.system()` 返回 `harmonyos`；Kea 白名单只含 linux/bsd/solaris/darwin | 补丁 `0001-meson.build.patch`（与家族模板逐字节一致）：`SYSTEM == 'harmonyos'` 归一化为 `'linux'` |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（首错 `boost/core/detail/sp_thread_sleep.hpp:73: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate()`，boost 1.85 的 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` + `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | meson 的"编译并运行"探针在 native 构建下真实执行；探针链接的 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH` | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` 聚合进 `conanbuild.sh` |
| 5 | `ninja FAILED: src/lib/dhcp/libkea-dhcp.so.../iface_mgr_linux.cc.o` → `.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h` 都定义 `struct sockaddr_storage`（kea-ctrl-agent 构建全树，libdhcp 同样编译到） | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（与家族模板逐字节一致）：define-guard 重命名，守卫 `__linux__ && !__GLIBC__` |
| 6 | `meson setup` 报 `/bin/sh: <conan 缓存>/bin/meson: Permission denied`（Error 126） | Conan 的 meson 包 `bin/meson` 是 **shebang shell 包装脚本**；OHOS 内核拒绝对脚本的 execve（与可执行位无关） | build() 改 `sh "<meson 包>/bin/meson" setup/compile/test`（sh 直接读脚本不触发 execve；命令行参数与 conan 2.29 helper 完全一致）；shell 套件同理用 `meson --wrapper sh` 执行 |
| 7 | `meson setup` 收尾处 `Running command: scripts/env.sh KEA_PKG_TYPE_IN_CONFIGURE` → `ERROR: Unhandled python OSError`（Error 13） | Kea 顶层 meson.build 在 configure 期直接 `run_command(ENV, ...)` 执行 `scripts/env.sh` 与 `scripts/grabber.py`——均为带 shebang 的脚本，OHOS 内核拒 execve | 补丁 `0003-meson.build.patch`（与家族配方逐字节一致）：脚本变量重定义为解释器前缀数组（`ENV = ['/bin/sh', <脚本路径>]`、`GRABBER = [find_program('python3').full_path(), <脚本路径>]`），调用点零改动 |
| 8 | setup 收尾 `Configuring config.report with command` → Error 13 | `meson.build:1025` 的 `CONFIG_REPORT = configure_file(command: [TOP_BUILD_DIR / 'config-report.sh'])` 直接执行刚生成的脚本 | 补丁 `0003` 第二个 hunk：`command: ['/bin/sh', TOP_BUILD_DIR / 'config-report.sh']`（hunk 行号按 patch-ng 语义写 1028，与家族配方逐字节一致） |
| 9 | `src/lib/process/cfgrpt` 处 `Configuring config_report.cc with command` → Error 13 | `src/lib/process/cfgrpt/meson.build:4` 的 `command: [mk_cfgrpt, ...]` 直接执行 `tools/mk_cfgrpt.sh` | 补丁 `0004-src-lib-process-cfgrpt-meson.build.patch`（与家族配方逐字节一致）：`command: ['/bin/sh', mk_cfgrpt, '@INPUT@', '@OUTPUT@']` |
| 10 | meson test 双套件 exit status 127，stderr 刷屏 `Error loading shared library libkea-X.so.N` | OHOS /storage 沙箱**拒绝创建符号链接**：meson 用 `version: 'N.M.K'` 构建并只以符号链接发布 soname 名 → 加载器按 NEEDED 名找文件落空 | build() 在 compile 后 `_materialize_sonames()` 以复制方式物化 soname 名（幂等；普通 Linux 宿主跳过）；package() 保留 0 字节落盘自愈复核（重拷后复验，有界重试 3 次仍为 0 则打包失败），test_package 闭包逐个 dlopen 兜底 |
| 11 | ninja 默认并行度在 OHOS 上编译中道崩殂（posix_spawn EAGAIN） | OHOS app 沙箱限制并发进程数：真机 20 核 + ninja 默认并行度 ≈45 活进程瞬时超配额 | 编译行 `meson compile -j 8` 限并发（与 make 家族 MAKEFLAGS jobserver 同源） |
| 12 | gtest 二进制在 ca_command_mgr 套件处整体 SIGSEGV（首轮真机 conan-verify G2 由此挂） | `isc::test::Sandbox` 构造：`char tmpl[] = {P_tmpdir "/kea-XXXXXX"}` + `mkdtemp()`——OHOS app 沙箱 /tmp 只读，`mkdtemp` 返回 NULL，`path_ = NULL`（std::string 空指针赋值）即崩（全树仅此套件用到 Sandbox） | 补丁 `0005-src-lib-testutils-sandbox.h.patch`：临时目录模板优先取 `TMPDIR`（未设时回退 P_tmpdir，普通宿主行为不变）；与 kea-dhcp6 配方对同一共享测试辅助文件的移植逐字节一致 |
| 13 | ca_command_mgr 9 例 `bind: Operation not permitted`（boost asio `local::stream_protocol` bind → EPERM） | 鸿蒙用户存储为 hmdfs 挂载：真机探针枚举显示**全盘可写挂载点均拒绝 AF_UNIX 路径名 socket bind**（TMPDIR/HOME/构建树/dev/shm 等），仅抽象命名空间可用；Kea 的 unix 控制通道按文件路径寻址，无法切换抽象名 | 补丁 `0006-src-bin-agent-tests-ca_command_mgr_unittests-skip-unix-channel.patch`：测试内加与 TestServerUnixSocket **同路径、同原语**的 bind 探针，不可用时 9 例 `GTEST_SKIP`（消息写明平台语义）；校验点/用例逻辑/注册数零改动，常规 Linux 探针恒真（问题类在库草稿：DRAFT-ohos-agent-socket-tmpdir-only-bindable-path——AF_UNIX 路径名 bind 挂载点白名单实测：普通存储 EPERM、抽象命名空间全可用、仅 user storage base 可 bind；本包探针与其判定语义一致） |
| 14 | 命令转发组 `CtrlAgentCommandMgrTest.noServerSocket` 单例失败：`C++ exception with description 'Filename too long [system:36]'`（ENAMETOOLONG）——首轮 verify2 干净构建 G2 由此单例挂 | 构建目录过深（共享包缓存路径）：夹具 socket 路径 = `TEST_DATA_BUILDDIR`（106 字节，meson `@current_build_dir@`）+ `/test-socket`（12）= 118 > `sockaddr_un::sun_path` 108 字节上限，`connect()` 对超限路径一律抛 ENAMETOOLONG（同一用例在浅构建目录下通过，与文件系统无关） | 补丁 `0007-src-bin-agent-tests-ca_command_mgr_unittests-socket-path-tmpdir-fallback.patch`：夹具在拼接超限时回退 `TMPDIR`（短且可写；未设 TMPDIR 时行为不变），该用例恢复实跑并通过（执行 87 PASSED + 9 SKIPPED + 0 FAILED）；patch_ng 对 0006→0007 链式应用 round-trip 逐字节一致 |
| 15 | test_package 运行时闭包完整性检查（干净构建首跑）报 5 个 Kea 库缺失（libkea-log-interprocess.so.3 / libkea-dhcp.so.109 / libkea-cfgrpt.so.3 / libkea-dns.so.71 / libkea-database.so.76），`kea-ctrl-agent -v` 退出码 127——verify3 G2 由此挂 | 配方初版按代理二进制**直接** `DT_NEEDED` 收录 11 库；Kea 各库以 `LIBS_BUILT_SO_FAR` 累积链接，真实递归闭包 16 库（二阶依赖链：log→log-interprocess、http/config→dhcp、process→cfgrpt、dns/database 等），且 test_package 对包内每个库 dlopen 都要能解析其 NEEDED | 配方改为分发 Kea 运行时库**全集** 20 库（40 文件，与已合入的 kea-hook-bootp/kea-hook-ha 3.0.3 同口径）；真机预验证 40/40 dlopen 全过、`kea-ctrl-agent -v` 输出 3.0.3（exit 0）恢复；test_package 检查下限随全集同步（>= 20 库） |
| 16 | 消费者 e2e 用例（verify4 干净构建首跑）真实进程被配置校验拒绝：Service failed: ... invalid path in output: invalid path specified: '<WORK 临时目录>', supported path is '/var/log/kea'（exit 1，端口 15 s 未监听） | Kea 对文件 logger 的输出路径做白名单校验：白名单目录取环境变量 `KEA_LOG_FILE_DIR`（默认 `/var/log/kea`；OHOS 上 `/var/log` 不存在）。用例把日志写进 WORK 临时目录的绝对路径必然被拒（此校验与平台无关，普通 Linux 上同样被拒） | e2e 用例导出 `KEA_LOG_FILE_DIR=WORK`（上游 `ca_process_tests.sh.in`/`dhcp4_process_tests.sh.in`/`d2_process_tests.sh.in` 等全部进程测试的标准做法），并新增「配置的日志文件已落盘」校验；其余 6 用例不受影响 |
| 17 | 消费者 e2e 用例（verify5 干净构建首跑）POST config-get 后崩溃：`TEST FAIL: control_channel_e2e: crashed: AttributeError("'list' object has no attribute 'get'")`（6 passed / 1 failed） | Kea 控制通道把每个应答包在**单元素 JSON 数组**里（batch/JSON-RPC 形制）：用例把 `json.loads` 的结果直接当对象调用 `.get()`，返回 `list` 即抛 AttributeError（前 6 个用例不经过该分支，故首轮未暴露） | 用例新增 `control_answer()` 解包单元素数组 + `isinstance` 显式判定（非对象记 FAIL 消息，不再崩溃），两处 POST 同款处置；修复后设备独立运行复验 `TEST SUMMARY: 7 passed, 0 failed`，随后官方 verify 运行全绿 |

## 真机验证

2026-10-04 真机 conan-verify（HarmonyOS PC aarch64，`ohos-aarch64` profile，
`kea-ctrl-agent/3.0.3@ohpcd/stable`）：**八门禁（G0-G4 + L2/L4/L5）全 PASS，
Verdict: PASS**（报告时间 2026-10-04T13:40:02）。

- `kea-agent-tests`（gtest）：96 ran → **87 PASSED / 9 SKIPPED（平台探针）/
  0 FAILED**（另 2 例上游自带 DISABLED_ 不执行）；87 例含全部 TCP 回环
  控制通道用例（HTTP 822/8081 端口会话、原生命令、配置解析）
- `ca_process_tests.sh`：7/7（meson 套件行 `Ok: 1 / Fail: 0`；`kea-agent-tests`
  同为 `Ok: 1 / Fail: 0`）
- `test_package`：3/3（消费者契约 7 项 + 鸿蒙平台 8 项 + 运行时闭包 6 项）
- 产物：`bin/kea-ctrl-agent` 506368 字节（494.5 KiB）；`lib/` Kea 运行时库全集
  （20 库 × soname 名 + 全版本名）40 文件 / 44164864 字节（≈42.1 MiB）；
  0 字节落盘复核：包内 0 字节产物 0 个

## 已知限制

1 项平台性限制：鸿蒙用户存储（hmdfs 挂载）**拒绝 AF_UNIX 路径名 socket 的
`bind()`（EPERM，真机全盘探针实测：仅抽象命名空间可用，而 Kea 的 unix 控制
通道按文件路径寻址、无法改用抽象名）**——本组件 9 个命令转发用例因此按
「与测试服务器同路径、同原语」的 bind 探针判定后 `GTEST_SKIP`（如实计列
SKIP，非失败、非删除；上游用例的校验点、逻辑与注册数零改动）。常规 Linux 上
探针恒真、跳过路径永不触发。Control Agent 的功能面（HTTP 控制通道、原生
命令、配置解析）不受影响。

本组件 105 个源码宏中 103 例实测执行（2 例为上游自带 DISABLED_ 前缀不执行），
其中 94 例通过 + 9 例上述平台性跳过；全树其余用例（Kea 主程序、核心库及
其他组件）不在本配方适配范围（见 MR 正文「测试减少原因」节）。
