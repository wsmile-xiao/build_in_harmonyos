# ircd-hybrid 8.2.46-dfsg.1 移植记录

## 来源与版本

- 软件：ircd-hybrid 8.2.46 IRC 服务端。
- Conan 包版本：`8.2.46-dfsg.1`，按请求保留版本名。
- 源码：官方 SourceForge `ircd-hybrid-8.2.46.tgz`，SHA-256 为
  `a5d5c8f1888fa82fbded7a313456f5a659b871f2ce07e6ff81eb5a8d73f3c74b`。
- 该版本名含 `dfsg.1`，但源码明确取自官方原始上游归档，并非 Debian
  source/repack；没有从 Debian 源包导入补丁。
- 上游版本由 `configure.ac` 的 `AC_INIT([ircd-hybrid], [8.2.46], ...)`
  确认。

## 构建适配

- 上游使用 Autotools，构建为应用包：`bin/ircd`、`bin/mkpasswd` 和
  libtool 模块。
- 配方启用 `--with-tls=openssl`，依赖仓库已发布的
  `openssl/3.5.8.1`；未添加 zlib 或其他未证实依赖。
- 真机 `uname -s` 返回 `HarmonyOS`，上游 release 中的 `config.guess`
  无法识别该系统。上游 `config.sub` 接受并规范化
  `aarch64-linux-ohos`，因此配方显式传 `--build=aarch64-linux-ohos`，不改
  上游源码，也不添加 `__OHOS__` 专用补丁。
- 首次真机构建在 `config.status` 创建 `conf*/subs1.awk` 时失败，报
  `Permission denied`。上游生成的 configure 用 `umask 077` 创建临时目录；
  参照仓库中 HMDFS 上相同失败模式，适配补丁仅把 configure 两处临时目录
  创建的 umask 放宽到 `022`。该补丁是通用权限调整，不含 HarmonyOS 条件编译。
- 编译进一步发现 `src/ircd_signal.h` 声明 `sig_atomic_t`，但该头文件没有
  引入定义该类型的 `<signal.h>`；`ircd.c` 的 include 顺序在当前 OHOS libc
  下没有其他头文件间接包含它。补丁在该公共头文件中加入直接 include，是
  可移植的自包含头文件修正。
- 链接时，ircd-hybrid 的 TLS backend 函数 `tls_free` 与静态 OpenSSL 3.5.8.1
  中同名全局符号冲突。项目发布的 OpenSSL 包固定为 static-only；补丁将
  ircd-hybrid 内部接口及各 TLS backend 实现改名为 `ircd_tls_free`，避免
  导出名称碰撞，不改变 TLS 行为或依赖库的构建选项。
- `mkpasswd` 也调用 `crypt()`，但只包含 `<unistd.h>`；configure 已确认
  `<crypt.h>` 可用。补丁添加直接 include，修复 Clang 对未声明函数返回值的
  指针转换错误。
- HarmonyOS sysroot 的 `unistd.h`/libc 不提供已废弃的 `getpass()`。为保留
  `mkpasswd` 的交互用法，补丁改用 POSIX `/dev/tty` 与 `termios` 禁止终端回显，
  收到一行后恢复终端状态，再继续原有 `crypt()` 流程。
- 安装前缀设为 `/`，配置示例安装到 `/etc/ircd-hybrid`，模块安装到
  `lib/ircd-hybrid/modules`。

## 上游测试审计

- 顶层 `Makefile.am` 仅递归构建 `libltdl libio src modules tools doc help`；
  源码中没有注册 `TESTS` 或 `check_PROGRAMS`。构建中运行 `make check`，
  其结果和零测试数量写入包内 `res/upstream_test_result.json`。
- 上游 GitHub workflow `irctest-ci.yml` 使用外部
  `progval/irctest`（固定提交 `aaa2e26b6e468112665ad7b15d144574a969b411`）、
  Anope 2.1.1、pytest 与 faketime，对运行中的服务做集成测试。
- 固定 irctest 提交的上游 hybrid workflow 使用 `make -C irctest/ hybrid`：517 项
  收集，官方选择器排除 59 项，目标选择 458 项。上游 `conftest.py` 的
  `pytest_collection_modifyitems` 在使用 server controller 时会过滤 20 项 client-side
  用例；过滤 hook 没有把它们计入 pytest 的 `deselected` 数。因此完整 Hybrid 目标最终
  有 438 项服务端 pytest 结果。2026-10-04 在 HarmonyOS 6.1.0.117 aarch64 真机上，
  pytest 7.4.4 最终结果为 311 通过、125 跳过、2 xfailed、0 失败，用时 757.05 秒；
  438 项中没有服务端用例未运行。59 项 selector 排除和 20 项 client controller 过滤
  均不属于未运行的服务端测试。
- 最终运行使用同一固定 irctest revision `aaa2e26b6e468112665ad7b15d144574a969b411`。
  为避免 HarmonyOS 上 faketime 注入造成 LIST 时间测试错误，运行环境的 PATH 未包含
  faketime；`FaketimeListTestCase.testListTopicTime` 按真实时间等待后通过，单项耗时
  186.56 秒。未修改测试用例或断言。
- 最终 125 项 skip 的 `-rs` 原因分组为：85 项需要服务端未宣告支持的 IRCv3 capability
  （含 `message-tags`、`echo-message`、`server-time`、`batch`、`labeled-response`、
  `extended-monitor`、`away-notify`、`setname`、`draft/channel-rename`、
  `draft/account-registration` 等）；14 项需要未支持的 SASL 机制（PLAIN、
  SCRAM-SHA-256 或 SASL 能力）；5 项依赖多目标 `KICK`、`NAMES` 或 `WHOWAS` 扩展；
  5 项依赖可选命令 `HELPOP`/`WALLOPS`；4 项需要未宣告的 `TARGMAX`/`UTF8ONLY`
  ISUPPORT token；5 项由上游实现选择定义（RFC1459 casemapping 或普通用户对 `@#chan`
  的 `PRIVMSG`）；4 项被上游标注为 `Not consistently implemented`；3 项需要未支持的
  `mute` extban。它们是上游测试按已协商能力和行为选择主动跳过，不是平台执行失败。
- 原先记录的三项 pytest 失败均已复测解决，且没有修改交付源码：
  - `HelpTestCase.testHelpNoArg[HELP]` 与 `testHelpPrivmsg[HELP]` 最初都收到
    `524 Help not found`。包构建使用 `--prefix=/`，帮助数据路径为绝对路径
    `/share/ircd-hybrid/help`；真机普通用户无法把归档安装到系统 `/share`。为验证行为，
    在设备用户目录建立临时包副本，把帮助模块的数据前缀指向该副本的 `share/`，并让
    临时 irctest 配置加载此副本；两项用例均通过。交付包仍是系统前缀 `/` 构建，当前
    结果证明正确安装路径下的帮助逻辑可用；任意 home 目录直接解包运行仍需安装到
    `/share` 或另行构建相应前缀。
  - `FaketimeListTestCase.testListTopicTime` 最初在 faketime 注入下 `LIST T<2` 未返回
    `#chan2`。设备 faketime probe 虽能推进 realtime，但该注入模式与此测试不兼容；从
    PATH 移除 faketime 后同一上游用例通过，实际墙钟等待 186.56 秒。Hybrid 的真实时间
    列表筛选因此通过，未改产品代码。
  - 服务集 `RegisterTestCase.testRegisterDefaultName` 最初因 Anope 异常没有到达断言。
    设备上的 stock Anope 2.1.1 以 `-fvisibility=hidden` 编译，`NotImplementedException`
    的 RTTI 在 Anope 核心和 `hybrid.so` 中分别是本地符号，libc++ 无法跨动态模块捕获，
    导致未捕获异常。设备禁止 LLDB 启动目标进程（remote launch 返回 `A` packet error
    8），所以没有调试器堆栈；通过 `llvm-nm` 确认符号可见性后，在临时 Anope 测试构建
    中给该异常类加 `CoreExport`，验证核心及模块均导出同一 RTTI。随后服务正常上线，
    `RegisterTestCase.testRegisterDefaultName` 按上游规则因 Hybrid 不支持
    `draft/account-registration` 而跳过。该补丁只用于设备外部测试依赖，不进入本仓库。
- 单独以 `-m services` 运行 Anope 子集时，75 项候选经上游 controller 过滤后有 55 项
  服务端结果：4 通过、51 按 IRCv3/SASL 能力跳过、0 失败。它们已包含在上述完整目标
  438 项结果中，不重复计数；没有服务端 services 用例未运行。
- 为适配 HarmonyOS 的可执行文件查找和只读系统日志路径，仅在设备上的 irctest 临时
  checkout 调整了 controller 的 executable 与每例 logfile；为 HELP 验证还使用了隔离
  的用户前缀副本。上游测试逻辑和断言未修改，临时改动未进入本仓库。
- Conan `test_package` 仍在真机直接启动包内 ircd，通过 loopback TCP 完成
  NICK/USER → IRC `001` welcome、PING/PONG，并正常退出；3 项消费者用例通过。
  这是实机 socket 协议交互，不是纯断言。

## HarmonyOS 真机

- 设备内核报告 `HarmonyOS`，产品标识为 `HAD-W24 6.1.0.117(SP68C00E100R13P3)`；
  设备为 aarch64。Conan host/build profile 使用 `OHOS/armv8`、Clang 15、
  libc++、C++17 和 `os.version=6.0`。实际编译和运行均在 HarmonyOS 6.1.0.117
  真机上完成。
- 最终 `conan create` 成功生成 OHOS/armv8 包；本次 W3 实测完整 Conan 引用为
  `ircd-hybrid/8.2.46-dfsg.1#61b7c73949d62bf8cb97d99482a0722e:bb90e580ad95d7a637b75cdeaa4cbd1e5bc533a9#7f2a24ad07d19c9b313fb563e7fd3492`。
  TLS 使用仓库的 OpenSSL 3.5.8.1 静态包。
- Conan consumer test 在真机报告 3 项通过、0 项失败：HarmonyOS 内核及产品版本
  探测；已打包 ircd 版本和必需模块检查；加载动态模块后通过 loopback 完成
  IRC `NICK`/`USER`、数值 `001` 欢迎、`PING`/`PONG`，并确认 SIGTERM 后正常退出
  （退出码 0）。这是实际设备与 socket 协议交互，不是纯断言。
- `make check` 在构建中执行。上游没有注册 Automake `TESTS` 或 `check_PROGRAMS`，
  因此包内测试数为 0。
- 上游 `progval/irctest` hybrid 外部集成目标适用 458 项；本次真机结果及未运行
  项的原因详见“上游测试审计”。
- 仓库 `python -X utf8 tests/run_all.py` 有 11/12 套件通过；唯一未通过的
  `test_v1220.py` 将 Git 可执行文件硬编码到设备路径
  `/data/service/hnp/git.org/git_2.45.2/bin/git`，Windows 构建主机上没有该路径，
  因此该环境相关的预检测试未能启动。针对本包的 PF3/R34、PF8/R38 和 R39
  静态预检均通过。

## 路线 B：知识扩展

- 新增草稿对：knowledge/drafts/E546-draft-A54E.kv 与同名 .md。
- 已用知识：E011 处理 Autotools 临时目录 umask 权限；E093 对照 musl 缺少 getpass 的适配边界；E420 作为直接包含类型/API 所属头文件的相邻模式。
- 可复用问题：src/ircd_signal.h 使用 sig_atomic_t，但没有直接包含声明该类型的 <signal.h>；OHOS/Clang 构建因当前 libc 头文件集合及 include 顺序未偶然带出该 typedef 而失败。补丁 0002-ircd-signal-header-include.patch 在使用类型的头文件中加入标准头。
- 查重与增量：E420 覆盖依赖 API 声明需要直接包含其 owner header；E721 草稿覆盖 OHOS musl 中 <dirent.h> 不传递暴露 NAME_MAX 的源文件场景；E634 草稿覆盖 BSD 信号 API 语义。它们均未记录本次 sig_atomic_t 项目头缺少 <signal.h> 的签名，也未提出“把该头作为首个 include 单独编译”的自包含性验证。
- 引擎以完整错误特征查询时命中 E367（Dl_info/dlfcn.h），属于通用 “unknown type name” 词项导致的误命中；精确检索 sig_atomic_t 未发现正式条目。
- 最终 Conan create 与真机消费者测试结果见本记录上文；草稿验证命令复用已通过的 OHOS aarch64 Conan create 配置。

## 最终状态与辅助流程限制

- HarmonyOS 6.1.0.117 aarch64 上执行仓库定向 W3（本次改动后重跑）：
  `ci/conan/build_and_test.sh archives/i/ircd-hybrid/8.2.46-dfsg.1`，1/1 包通过；
  Conan create、`make check`、3 项真机消费者用例，以及 L0/L1/L1e/L2/L4/L5 门禁通过。
- 为满足仓库 §21，`0005-mkpasswd-portable-hidden-prompt.patch` 已统一为 LF 行尾；
  此后重新运行完整 W3、官方打包和解包后真机消费者测试，结果均通过。
- 真机 W3 生成的 `ci-metadata.json` 与 `reports/w3-local-ci.log` 留在包目录作证据；
  `.ci-result.json` 的日志哈希与原始日志一致；运行时标记和日志不作为源代码变更提交。
- `verify-build` 对本次 Conan 安装前缀给出质量 PASS（G1 121/0/0，G2 0/2 警告、
  G3 0/4 警告、G4 0/1 警告）。官方 `package_builder` 生成
  `ircd-hybrid-8.2.46-dfsg.1-ohos-aarch64.tar.gz`（15,880,075 字节，SHA-256：
  `9aeec72915105c7a630180961ba436ae0c627fe9f50ff6f0d8a94cc39071501e`）；将临时 tar.gz
  解包到真机目录后，HarmonyOS consumer runtime 测试再次 3/3 通过。该 tarball 与
  `packaging/` 目录按 `knowledge/ARCHIVE-SPEC.md` §2.3 在 PR 前清除，不作为归档文件提交。
  最终归档 SHA-256 为 `9aeec72915105c7a630180961ba436ae0c627fe9f50ff6f0d8a94cc39071501e`；
  与 HarmonyOS 真机上的产物哈希一致。
- 仓库 Step 8 staging 验证从 Conan 安装树复制真实可执行文件并运行两个
  `--version` 检查，结果 `verified=2 failed=0`。官方 `close-archive` 已将归档关闭
  为 `built`；submit-readiness 的测试报告、打包目录、staging 标记和 build-closed
  标记四项全部通过。
- 独立 `conan-verify` 使用 `ircd-hybrid/8.2.46-dfsg.1@ohpcd/stable` 时，G2
  在 HarmonyOS configure 阶段失败，报 `working directory cannot be determined`
  并伴随 `getcwd` 错误；标准 plain ref 的 W3 fresh Conan create 和消费者测试通过。
  此辅助流程失败已在本目录的测试记录中单列，不计作通过。
- 全量 `finish` 的其他辅助检查有限制：干净源码复核缺少仓库构建上下文中的原始
  tarball；知识补充扫描指出正式条目 E219/E253/E305 的既有字段为空，而
  `graph validate` 对 542 条正式条目仍报告 All checks passed（170 条存量警告）。
  打包与 staging 产物随后由仓库官方流程真实生成并验证；没有将其他辅助流程的
  限制报告成 W3 失败，也未修改正式知识图谱。

## 最终状态

- 适配状态：`built`；HarmonyOS aarch64 W3 本地 CI 及真实消费者测试通过。
- 路线 B：新增 E546 草稿对，草稿预审与知识图谱校验通过；尚未进入正式知识图谱。
- 仓库 submit-readiness 前置检查 4/4 通过；W4/W5 独立审计均为 PASS，P0/P1 为 0。
- `0005` 的 CRLF 行尾问题已修正并重新完成设备构建；独立 W4 复核后仅保留一个
  非阻断 P2：口令提示被 SIGINT/SIGTERM 中断时，终端回显可能未恢复。当前测试未覆盖信号中断。
---

**编译结束**: 2026-10-03 21:15
**最终状态**: built
