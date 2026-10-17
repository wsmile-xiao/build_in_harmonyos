# kea-dhcp4 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: published（真机 conan-verify 全绿；验证数据见「真机验证」节）

## 定位与家族复用

`kea-dhcp4`（DHCPv4 服务器）与已合入的 `kea-perfdhcp`、`kea-hook-limits`、
`kea-hook-ping-check`、`kea-hook-flex-option`、`kea-hook-bootp`、`kea-hook-ha`
同属 Kea 3.0.3 单源码树（`src/bin/dhcp4/` 平级目录，共用同一顶层 `meson.build`
与 `src/lib/`），平台差异完全相同：0001-0005 五个补丁**整组逐字节复用**、
零改动（sha256 见下），其中 0005 由 kea-hook-ha 引入（DHCPv4 服务器的测试同样
构造生产 `IfaceMgr` 检测路径，直接复用）。0006-0011 为本包新增的测试侧适配，
与同批姊妹适配 kea-dhcp6 的补丁组同源同解：0006（测试沙箱 TMPDIR）与 dhcp6 版
逐字节同源，0007-0011 按 DHCPv4 测试树改写（问题 13-16）。

服务器自身核对（2026-10-04）：

- 产物 `kea-dhcp4`（`src/bin/dhcp4/meson.build`：`static_library('dhcp4')` +
  `executable('kea-dhcp4', 'main.cc', install_dir: SBINDIR, dependencies: [CRYPTO_DEP])`）
- CLI（`main.cc` usage 实测行为）：`-v`/`-V` 版本与扩展版本、`-W` 构建配置报告、
  `-t file` 配置语法校验（check-only）、`-T file` 校验+hooks 加载+额外检查、
  `-c file` 正常运行、`-d` 调试、`-p`/`-P` 测试端口、`-X` 关闭安全检查
- 上游套件名：`kea-dhcp4-tests`（gtest；源码宏计 948 用例，二进制真机运行期
  注册 1024 用例 / 29 套件——含 TEST_P 实例化展开，以 gtest 输出为准）；同目录
  注册的 shell 套件 `dhcp4_process_tests.sh`（suite: shell-tests，14 个子用例）
  ——两套件均在 build() 内实跑
- 2 个上游 DISABLED_ 用例：`Dhcp4ParserTest.DISABLED_Uint32Parser`、
  `JSONFileBackendTest.DISABLED_loadAllConfigs`（gtest 标记不运行）
- 1 个 TEST_P：`Dhcp4GetConfigTest.run`（get_config_unittest.cc，按实例化展开）

## 程序行为与测试面特点

**行为**（多线程 DHCPv4 服务器守护进程）：

- 读 JSON 配置（`subnet4`/`pools`/options/`lease-database`/`hooks`/`dhcp-ddns`/
  `loggers` 等），在 `interfaces-config` 指定的接口上监听 UDP 67，按 DORA 流程
  分配租约；租约后端 memfile（默认，CSV+租约文件）或 mysql/pgsql（本配方禁用两
  SQL 后端）。
- 控制通道：Unix socket 控制通道与 HTTP 控制 socket（`http_control_socket`），
  支持 config-set/config-get 等命令；`kea-dhcp4 -t` 为 check-only 模式。
- 插件/Hook 面：hooks 套件验证 callout 加载与查询转发（co3/co4 为故意
  加载失败/转发失败的 callout 库）；进程套件验证 hooks 失败路径与信号处理。
- 生产路径构造 `IfaceMgr` 做接口检测——OHOS 沙箱拒绝 netlink bind，测试用例
  （ctrl_dhcp4_srv / http_control_socket 等）会命中，由补丁 0005 的
  `getifaddrs()` 回退修复（同 kea-hook-ha 在生产连接路径的暴露）。
- `-W` 输出 configure 期 `mk_cfgrpt.sh` 生成的 config_report.cc 内容，是
  补丁 0003/0004 修补链的运行时端到端校验点。

**测试面**：gtest 二进制真机运行期注册 1024 用例 / 29 套件（源码宏计 948），
全部为纯逻辑/模拟报文/回环高位端口用例：上游源码零 `geteuid`/`getuid` 守卫
（平台适配补丁按探测结果程序化跳过控制通道相关用例，见问题 14）；报文比对里
的端口 67 为常量而非真实绑定。DORA 用例经模拟 socket 注入报文，HTTP 控制
socket 用例绑定回环高位端口——OHOS 沙箱下零 root 实跑（实测结果见
「真机验证」节）。`dhcp4_process_tests.sh`（shell 套件）以真实 kea-dhcp4 进程
做信号/重配置/LFC 验证（配置 `interfaces: []`，不开 socket、零特权；经 `sh`
前缀运行，见问题 13），真机实测 14/14 子用例全过（exit status 0，48.86s，
见「真机验证」节）。

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
3. `meson compile -C <builddir> -j 8`（全树；限并发防沙箱 posix_spawn EAGAIN）
4. `meson test -v --timeout-multiplier 10 -C <builddir> kea-dhcp4-tests dhcp4_process_tests.sh`

## 遇到的问题与解决方案

问题 1-12 为家族配方已解决的平台问题（同一上游树、同一差异），对策一一沿用
（0001-0004 补丁整组复用 + 配方内三处构建级适配；0005 为 ha 引入、本包复用）；
问题 13-16 为本包真机验证阶段实测发现并修复的测试侧平台问题（0006-0011，
与 kea-dhcp6 配方同题同解）：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` | 宿主环境 `AR=llvm-ar`（裸名）被探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行不解析 PATH，裸名 ENOENT | `generate()` 从 `tools.build:compiler_executables` 推导 `llvm-ar`/`llvm-ranlib` 绝对路径写入 machine file |
| 2 | `ERROR: Problem encountered: Unsupported system "harmonyos".` | Kea 平台白名单只含 linux/bsd/solaris/darwin | 补丁 0001：`SYSTEM == 'harmonyos'` 归一化为 `'linux'` |
| 3 | `use of undeclared identifier 'pthread_setcancelstate'` | OHOS musl `<pthread.h>` 不声明它，boost 1.85 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` | meson 编译并运行探针真实执行，`liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH` | `Environment` 聚合各 host 依赖 libdirs 进 `LD_LIBRARY_PATH`（conanbuildenv-kea-runtime） |
| 5 | `sysroot/usr/include/linux/socket.h: error: redefinition of 'sockaddr_storage'` | bionic 派生 `linux/socket.h` 与 musl `sys/socket.h` 冲突 | 补丁 0002：define-guard 重命名（`__linux__ && !__GLIBC__`） |
| 6 | `meson setup` 报 `<conan 缓存>/bin/meson: Permission denied`（Error 126） | conan meson 包 `bin/meson` 是 shebang 包装脚本，OHOS 内核拒脚本 execve | build() 改 `sh "<meson 包>/bin/meson" setup/compile/test` |
| 7 | `Running command: scripts/env.sh ...` → `ERROR: Unhandled python OSError`（Error 13） | 顶层 meson.build 经 `run_command(ENV, ...)` 执行带 shebang 的 `env.sh`/`grabber.py` | 补丁 0003：脚本变量重定义为解释器前缀数组（`['/bin/sh', 脚本]` 等），调用点零改动 |
| 8 | `Configuring config.report with command` → Error 13 | `configure_file(command: [config-report.sh])` 直接执行生成的脚本 | 补丁 0003 第二 hunk：`command: ['/bin/sh', ...]` |
| 9 | `Configuring config_report.cc with command` → Error 13 | `src/lib/process/cfgrpt/meson.build` 直接执行 `tools/mk_cfgrpt.sh` | 补丁 0004：`command: ['/bin/sh', mk_cfgrpt, ...]` |
| 10 | 测试进程 stderr 刷屏 `Error loading shared library libkea-X.so.N` | /storage 沙箱拒绝符号链接：meson 只以符号链接发布 soname 名 | `_materialize_sonames()` 以复制方式物化（幂等）；package() 0 字节落盘三重补拷复核；test_package 逐库 dlopen 兜底 |
| 11 | ninja 常态并行度编译中道崩殂（posix_spawn EAGAIN） | OHOS app 沙箱限制并发进程数（20 核默认并行 ≈45 活进程超配额） | `meson compile -j 8` 限并发 |
| 12 | `IfaceDetectError ... "Failed to bind netlink socket."` | OHOS 沙箱对 AF_NETLINK 放行 socket() 拒绝 bind()；服务器测试构造生产 `IfaceMgr` 检测路径即触发 | 补丁 0005（ha 引入、本包复用）：`detectIfaces()` 打开 netlink 失败时回退 `getifaddrs()` 两趟枚举（AF_PACKET 取 MAC/HWType + AF_INET/AF_INET6 取地址 + if_nametoindex），与上游 BSD/Solaris 实现同构；常规 Linux 上回退永不触发 |
| 13 | `meson test` 启动 shell 套件报 `PermissionError: [Errno 13] Permission denied: .../dhcp4_process_tests.sh`（build() 测试步 ConanException；编译已完成） | OHOS 内核拒 shebang 脚本 execve（EACCES，与可执行位无关）；meson `test()` 直接 spawn 配置期生成脚本本体 | 补丁 0011：`test()` 改为 `find_program('sh')` + `args: [dhcp4_process_tests]`；先行实证＝设备直跑 `sh dhcp4_process_tests.sh` 14/14 通过（与补丁 0003/0004/配方 `_meson()` 同一内核特性、同一解释器前缀纪律） |
| 14 | 控制通道用例整组不可用：`CtrlChannelDhcpv4SrvTest` 系 55 例（unix 控制通道）与 `Dhcp4ParserTest.comments`（报 `Filename too long [system:36]`，ENAMETOOLONG）、`Dhcp4GetConfigTest` 控制 socket 配置的 commit 实例 | 用户存储为 hmdfs 挂载，不承载 AF_UNIX pathname socket：bind 被拒（EPERM），且解析后的 socket 路径超出 `sockaddr_un.sun_path` 上限（ENAMETOOLONG） | 补丁 0007：新增 `Dhcpv4SrvTest::unixControlSocketsUsable()`——以服务器实际使用的同一 bind 操作对探测 socket 路径做可用性探测（cc+h 同 patch）；补丁 0008：fixture `SetUp()` 按探测结果对这 55 例 `GTEST_SKIP()`；补丁 0009：parser comments 与 get_config 两处配置 commit 用例按同一探测+配置包含 `control-socket` 跳过；常规 Linux 上探测恒真、跳过永不触发 |
| 15 | `CtrlChannelDhcpv4SrvTest` 构造期崩溃（Signal 11）——fixture 成员 `isc::test::Sandbox` 构造失败 | OHOS `/tmp` 只读（Read-only file system）：sandbox.h 默认 `P_tmpdir`("/tmp") 下 `mkdtemp` 返回 NULL，赋值 `std::string` 解引用空指针 | 补丁 0006（kea-dhcp6 配方 0006 逐字节复用）：sandbox 先取 `TMPDIR`（设备已设置 `~/tmp`）再回落 `P_tmpdir`，模板改用 `std::vector<char>` + 终止符；md5 a0a1ef2f 与 dhcp6/ctrl-agent 版一致 |
| 16 | Http/Https `configWriteFullPath` 两例失败（config-write 无法写入目标路径） | 用例把 `-c` 配置与 config-write 目标写死为 `/tmp/test1.json`、`/tmp/test2.json`；/tmp 只读 | 补丁 0010：两路径改建于 `TMPDIR`（回落 `/tmp`），并显式补 `<cstdlib>`（getenv 声明）；文件内其余引用 /tmp 的用例为比较语义（"拒绝写"路径），不受只读影响 |

补丁 sha256（本包 `patches/`；0001-0005 与家族归档逐一核对一致，0006-0011 为本包新增并经全量回放校验）：

| 补丁 | sha256 |
|------|--------|
| 0001-meson.build.patch | 64f8d3544ba6a5e5aff3371b2d489cd4f2422a0ad7cffcb13ee3d7c74fdb6ec1 |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | a19a64b5556510e15c3d8ce488841375afe258f4d728bb35293a9f6ace1ae8b0 |
| 0003-meson.build.patch | 9e45acee8438f49fa64a21c5b68b3a51790764970ea80cbfbe5312bb45603b77 |
| 0004-src-lib-process-cfgrpt-meson.build.patch | ec9f11b1b5df915191dde1bf769e3154e290cd4bf06847950fc08896f5fefd51 |
| 0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback.patch | d74fffe59d5772a09626c89160847ff549ff2e181f10650abd90f28b8e4590b3 |
| 0006-src-lib-testutils-sandbox.h.patch | 79fb46d54ab805e983c4cc6c60a782f6828e82156550dc281b4c5e95f4e9244d |
| 0007-src-bin-dhcp4-tests-dhcp4_test_utils-unix-socket-check.patch | d34cc5d0335af1c33ae4226ede88cb03e76d6fe218186fc9080f3a502705cc3f |
| 0008-src-bin-dhcp4-tests-ctrl_dhcp4_srv_unittest-skip-unix-channel.patch | b159268fb1a23b00cafcba37f20c83764b3cbffbbffae89cb42196b279731176 |
| 0009-src-bin-dhcp4-tests-config-commit-skip-unix-control-sockets.patch | 4d218436ab012ae1311b6818fe92f7aec08ee71c6da4f4523c8700e52e4819b6 |
| 0010-src-bin-dhcp4-tests-http_control_socket_unittest-tmpdir.patch | 0cbd7387ca9af1d4b814b08c80467a32e0436ee8466e7f4209b0b7761643e76a |
| 0011-src-bin-dhcp4-tests-meson.build-shell-test-via-sh.patch | 8f4a00598327632477322617e0557cabf5a0b4d13271d956608a60ef9d26242c |

## 真机验证

2026-10-04 真机 conan-verify（HarmonyOS PC aarch64，`ohos-aarch64` profile，
`kea-dhcp4/3.0.3@ohpcd/stable`）：**八门禁（G0-G4 + L2/L4/L5）全 PASS，
Verdict: PASS**（报告时间 2026-10-04T15:37；L2/L4/L5 为框架对无 cache 路径包
的既定跳过形态，与已合入的 kea-hook-ha / kea-hook-bootp 报告一致）。

- **上游测试**（G2 内 `meson test -v` 全量实跑，2026-10-04 干净构建）：
  `kea-dhcp4-tests` 2/2 OK（26.01s）——运行期注册 1024 例 / 29 套件实跑：
  **967 通过 + 57 平台性 SKIP（bind 探针判定）+ 0 失败**（另 2 例上游
  `DISABLED_` 不运行）；`dhcp4_process_tests.sh` 1/2 OK（48.86s）——
  **14/14 子用例全过**（exit status 0；junit 11+2+1，0 失败）；meson 汇总
  Ok: 2 / Fail: 0；全树 1433/1433 编译链接零错误
- **test_package 3/3**：test_dhcp4.py（消费者契约 21 项：-v/-V/-W 输出、
  命令行错误路径、`-t` 配置校验正反路径）/ test_ohos_platform（平台 ABI
  11 项：ELFCLASS64 + EM_AARCH64 + ET_DYN；DT_NEEDED 19 项 = 17 个
  libkea-*.so.N + libc++_shared.so + libc.so，无 glibc/libstdc++ 命名）/
  test_ohos_runtime（运行时闭包 6 项：闭包 20 库 40 文件全部随包分发、逐个
  dlopen(RTLD_NOW) 40/40 成功、真实执行 kea-dhcp4 -v 输出 3.0.3）
- **产物**：`bin/kea-dhcp4` 1,620,480 字节（1.55 MiB）；包内 Kea 运行时闭包
  40 个库文件（20 库 × soname 名 / 全版本名），lib/ 共 44,048 KiB（≈ 44 MB）
- **0 字节自愈**：package() 空产物三重补拷复核就位；本次打包产出的 44 个
  文件（bin 1 + lib 40 + 元数据）逐个复核均为非零字节（0 字节文件 0 个）
