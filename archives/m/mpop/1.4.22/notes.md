# mpop 1.4.22 适配笔记

## 编译环境
- 构建系统: autotools（发布包同时带**生成的 `configure`** 与 `configure.ac`；本配方按发布产物对待，不重跑 autoreconf）
- 编译日期: 2026-09-26
- 编译器: clang 15（profile `tools.build:compiler_executables` → `/data/service/hnp/bin/clang`，Target `aarch64-unknown-linux-ohos`，musl）
- 机器: B 机（HarmonyOS PC aarch64，8 核 / 31G）
- profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同一个，按绝对路径引用仓内文件）
- CONAN_HOME: `~/tmp/ch/home-mpop`（本任务独立隔离）
- 状态: built（conan-verify 判决见「验证结果」节）

## 软件与构建面（读源码所得，不是猜测）

mpop 是一个非交互的 POP3 取信客户端（`marlam.de/mpop`）：从配置文件的账户段取信并投递到
maildir / maildir-plus / MDA / stdout，支持 APOP、CRAM-MD5、PLAIN、NTLM、OAUTHBEARER 等 SASL
机制与 STLS/POP3S。随包还产出第二个程序 `mpopd`（把已取到的邮件通过 Maildir 提供给本地
POP3 服务端的守护进程，`configure.ac` 的 `BUILD_MPOPD` 默认为 yes）。

- `src/Makefile.am`：`bin_PROGRAMS = mpop mpopd`，`mpop_LDADD` 含
  `$(libidn2_LIBS) $(libsecret_LIBS) $(LIBINTL)`，TLS 后端三选一（GnuTLS / OpenSSL / libtls）。
- TLS 走 `--with-tls=gnutls`（上游默认值，这里显式钉住，避免误链宿主 OpenSSL）；
  `mtls-gnutls.c` include `<gnutls.h>` 并需要 libgcrypt/libgpg-error/libtasn1 闭包。
- 运行期依赖闭包实测（`conan-create.log:446` 打印的 DT_NEEDED 原文）：
  `libc.so, libgcrypt.so.20, libgnutls.so.30, libgpg-error.so.0, libidn2.so.0, libtasn1.so.6`
  ⇒ 依赖是**共享**库（与同窗 lft 的静态 libpcap 相反），所以消费者测试必须带
  Conan 的 run 环境；测试里反向利用这一点做了一条负对照（见「消费者测试口径」第 22 条）。
- `doc/Makefile.am` 有 `info_TEXINFOS = mpop.texi` ⇒ `make`/`make install` 会调 `makeinfo`。
- `Makefile.in` 层面**没有 `TESTS`、没有 `check_PROGRAMS`**（全树 `grep -rnE
  '^(TESTS|check_PROGRAMS|check_|installcheck)' --include=Makefile.am` 命中 0）
  ⇒ 上游没有自动化测试套件；配方仍跑 `make check`（`RUN: make check -j1 MAKEINFO=true`），
  但它只走 Makefile 依赖图、不含任何用例。

## 依赖面与"故意不声明"的依赖（每条都有实测理由）

- 声明：`gnutls/3.8.10`、`libidn2/2.3.8`（均 `transitive_headers=True, transitive_libs=True`）。
  W0 preflight 06:30 实跑 PASS，并同轮以 `zlib/1.3.1` 作正对照 ⇒ `gnutls/3.8.10`、
  `libidn2/2.3.8`、`libsecret/0.21.7`、`gettext/0.22.5.1` 全部"已发布"。
- 不声明 `libgsasl`：`configure.ac` 硬约束 `libgsasl >= 2.1`，而仓内 `archives/g/gsasl`
  只登记 **1.8.1 且目录里没有 `conanfile.py`**（只有 manifest/notes/patches）⇒ 制品仓没有可消费的
  gsasl 包，版本也不满足约束 ⇒ `--without-libgsasl`。
  **功能后果（不是无害裁剪）**：CRAM-MD5 / DIGEST-MD5 / SCRAM-* / OAUTHBEARER / NTLM 这些
  需要 SASL 库的认证机制在本构建里不存在；`mpop --version` 的 "Authentication library:" 行
  实测打印为 built-in，消费者测试把这一事实做成了断言（第 5 条），而不是掩盖它。
- 不声明 `gettext` ⇒ `--disable-nls`：`gettext/0.22.5.1` 虽已发布，但其 `cpp_info.libs`
  列了包里实际不提供的 `libasprintf`（下载侧探测所得）⇒ 链上去就是悬空 `-lasprintf`。
  上游 `AM_GNU_GETTEXT([external])` 因此被显式关断，`LIBINTL` 退化为空。
- 不声明 `libsecret` ⇒ `--without-libsecret`：`libsecret-1` 会把整条 glib 闭包拖进来，
  而 GNOME 密钥环在无头 POP3 客户端场景没有使用面。
- `--without-macosx-keyring`：探测默认开着，非 macOS 平台显式关掉以免误捡。

## OHOS 适配点（六条，全部实测命中）
- **E007 / E160（三元组识别）**：`configure` 在 `AC_CANONICAL_TARGET` 阶段死在
  `../build-aux/config.guess[1744]: cant create .../dummy.c: Permission denied` 之后
  `configure: error: cannot guess build type; you must specify one`。
  处方＝用仓内 `scripts/patch-autotools-ohos.pl` 成对生成 **随包 patches**
  （`patches/0001-build-aux-config.guess-ohos.patch` + `0002-...config.sub-ohos.patch`），
  由 `export_conandata_patches` 应用（`conan-create.log:129-130` 两行 Apply patch 原文）。
  与同窗 lft 的区别：这里在**起草期**就生成 diff 落 `patches/`，不在运行期去找仓内脚本，
  因此不需要 `export_sources` 带 helper，也不会因缓存导出目录而上溯失败。
  ⛔ 未用 `--build/--host` 绕过（E007/`autotools-patterns #0` 明令禁止）：本包
  `configure.ac` 确有 `AC_RUN_IFELSE` 形态的 getaddrinfo/`AI_IDN` 探测，被判成交叉编译会静默跳过；
  实测走补丁路线后 `conan-create.log:143` = `checking whether we are cross compiling... no`。
- **E011 / E114**：`build()` 内把 `configure` 里的 `umask 077` 就地改写为 `umask 022`，
  实测命中 2 处（`conan-create.log:133` 原文 `E011: rewrote 2 occurrence(s) ...`）。
  `configure` 是发布产物 ⇒ 不走 `patches/`（与仓内 1000+ 存量配方一致）。
- **E386**：profile `[buildenv]` 注入 `CONFIG_SHELL=/data/service/hnp/bin/bash`，该 bash 在
  HMDFS 上 `getcwd()` 失败，而 autoconf 生成的 configure 会用它 re-exec 自身 ⇒ 起手即死。
  处方＝在**同一条 shell 命令里** `unset CONFIG_SHELL`（generate() 期 `env.unset` 会被运行期重注入击败）。
- **E467**：同一条命令内联 `LD_LIBRARY_PATH=<依赖闭包 libdir>`，避开 `AutotoolsDeps` 注入的
  `$LIBS` 让最早的"能否运行 C 程序"探测被加载器拒载、被误报成编译器不可用。
  configure 参数仍取 `Autotools._configure_args`，配方只追加 feature 开关（R1/R33/R49）。
- **makeinfo 缺失（texinfo 未发布）**：`doc/Makefile.am` 的 `info_TEXINFOS` 让 `make`/`install`
  需要 `makeinfo`；设备实测无该命令，且仓内 `archives/t/texinfo/7.3` 目录**没有 `conanfile.py`**
  ⇒ 不能 `tool_requires`。处方＝`make`、`make check`、`make install` 一律带 `MAKEINFO=true`
  （日志 `:249/:294/:319` 三行 `RUN:` 原文），这是 corpus 自有惯例（先例
  `archives/a/autoconf/2.72`、`archives/a/anubis/4.3`）。发布包自带生成好的 `doc/mpop.info`，
  只是不再重生成，手册页与 info 页仍照常安装。
- **上游内嵌 gnulib 只在 C23 下可编译**：`src/base64.h`（gnulib vendored）声明返回 `bool` 的
  原型却不 include `<stdbool.h>`；OHOS clang 15 默认 C17（实测 `__STDC_VERSION__=201710L`）
  ⇒ `error: unknown type name 'bool'`（两处）。`patches/0003-src-base64.h-include-stdbool.patch`
  补一次 include（不改任何逻辑，也不升到 `-std=c2x`，以免改变全局语言标准）。
- **libc 函数"探测正确、调用点未守护"**：`configure.ac` 有 `AC_CHECK_FUNCS([getpass])`，
  实测生成的 `config.h` 里是 `/* #undef HAVE_GETPASS */`（OHOS libc 既不在 `unistd.h` 声明
  `getpass` 也不导出该符号），但 `src/password.c:215` **无条件**调用它 ⇒
  `ld.lld: error: undefined symbol: getpass / referenced by password.o:(password_get)`。
  `patches/0004-src-password.c-guard-getpass.patch` 用**上游自己已有的** `HAVE_GETPASS`
  宏补上守护。**功能后果如实披露**：OHOS 上交互式口令提示不可用，口令只能走
  `password_program`（`--passwordeval`）或 `netrc`，这是 mpop 本来就支持的三条取口令路径之二。

## 消费者测试口径（赛道二：真实执行、断言决定退出码）
- 行为层（`test_package/test_mpop.sh`，**22 个用例** = 脚本里 22 个 `report` 调用点，
  计数写进 `<scratch>/checks.count` 供 Python 侧与申报值双向对账；断言失败即 `die` → `exit 1`）：
  1. `bin/mpop` 与 `bin/mpopd` 均已打包且为可执行常规文件；
  2. `mpop --version` 退出码 0 且打印 `mpop version 1.4.22`（证明 `config.status` 替换生效）；
  3. `--version` 的 `Platform:` 行取到真实 OHOS target 三元组（含 `aarch64` 且含 `ohos`）；
  4. `TLS/SSL library: GnuTLS` ⇒ `--with-tls=gnutls` 实测生效；
  5. `Authentication library:` 报 built-in ⇒ 关闭 libgsasl 后的**真实后果**被断言而不是被掩盖；
  6. `IDN support: enabled` ⇒ libidn2 被真实链接；
  7. `mpop --help` 退出码 0 并打印取信模式用法；
  8. `--help` 列出 `--all-accounts` 与上游 bug 地址；
  9–14. 选项校验（发生在任何网络动作之前，共 6 条）：未知长选项 → `EX_USAGE=64`；
  `--port=0` 被拒（`invalid argument 0 for --port` + 64）；`--pipelining=bogus` 被拒；
  `--received-header=bogus` 被拒；`--host` 与 `--all-accounts` 互斥；`--all-accounts` 与
  账户列表互斥 —— 每条都同时断言退出码与诊断文本；
  15–17. 配置文件解析（`get_conf` 失败即 `goto exit`，网络栈尚未初始化，共 3 条）：
  `-C` 指向不存在的文件 → `EX_IOERR=74` 且诊断点名该文件；裸 `account` 关键字 →
  `EX_CONFIG=78` + `missing account name`；无账户的配置 → `EX_CONFIG=78` + `no accounts defined`；
  18. `--configure` 对非法地址返回 `EX_DATAERR=65`（该分支在任何 SRV/DNS 查询之前）；
  19–21. `mpopd`（第二个交付程序，共 3 条）：`--version` 退出码 0 且打印
  `mpopd version 1.4.22`；`--help` 退出码 0 且 usage 带 `--maildir`；缺 `--auth/--maildir`
  时非零退出并给诊断（未触网）；
  22. **负对照（R34 反证）**：去掉 Conan 运行库路径后 `mpop` 必须被加载器拒载
  ⇒ 证明被测二进制确实消费**本包**的依赖闭包，而不是命中系统里恰好同名的命令。
  以上 22 条对应脚本内 22 个 `report` 调用点（脚本注释块号写到 24 是分段号，不是计数号；
  复现命令：`grep -cE '^[[:space:]]*report ' test_mpop.sh` → 22）。
- 平台层（`test_package/conanfile.py`，**4 条**，直接从打包 ELF 的字节里解析）：
  ELF64/AArch64 头、动态 `NEEDED` 闭包必须同时含 `libgnutls.so*` 与 `libidn2.so*`
  （即声明的依赖真的被链进来，不是宿主副本）、`.codesign` 段、产物字节无宿主绝对路径泄漏。
  并打印机器可读两行：`HMBS_MPOP_NEEDED=[...]`（`:446`）与
  `HMBS_TEST_PACKAGE_RESULT={"consumer_passed": 26, "consumer_total": 26, "executed": true,
  "passed": true}`（`:447`）。
- 合计口径（notes / `MANIFEST.yml` / PR 正文三处同源）：`test_case_count: 26` = 行为 22 + 平台 4；
  `measured_passed: 26`、`failed: 0`；`static_upstream_test_files: 0`（三条实测清点证据）。
  另一个口径写在 `MANIFEST.yml` 的 `assertion_count: 45` = 脚本里 41 个 `expect_rc/expect_has/
  expect_absent` 调用点（一条用例可含多条断言）+ 4 项 ELF 平台检查；复现命令
  `grep -oE 'expect_(rc|has|absent)' test_mpop.sh | wc -l` → 41。26 是"用例/检查点"，45 是
  "判定表达式"，两者不互相替换。
- 能力层（**未做成断言**，逐条带实测错误签名记录在 `MANIFEST.yml` 的 `consumer_skipped`，
  绝不记成通过）：
  1. POP3 会话（USER/PASS、STAT/LIST/RETR/DELE/UIDL）与 `--serverinfo`：设备无外网 POP3 服务，
  也没有可连的本地监听方（无 `ss`/`ip`/`nc`，`/proc/net/tcp` 为 EACCES）。实测签名：
  `mpop: cannot connect to 127.0.0.1, port 1999: Connection refused` + `error during mail
  retrieval`，退出码 75（EX_TEMPFAIL）⇒ TCP 连接与错误上报链路本身工作正常，缺的是服务器端。
  2. `getaddrinfo` 实际解析上网：实测签名 `mpop: cannot locate host does-not-exist.invalid:
  Try again`（退出码 75，即 `EAI_AGAIN` 被原样报出）⇒ 解析调用链通、无新失败签名。
  3. TLS 握手与需服务端的认证协商：需要一个可连的 POP3S/STARTTLS 对端，设备没有。
  注意边界：TLS 后端的**链接与配置**一面不在此列，已由 `TLS/SSL library: GnuTLS` 断言与
  DT_NEEDED 里的 `libgnutls.so.30` 两条实测覆盖。

## 验证结果（B 机实测；证据日志 = `archives/m/mpop/1.4.22/reports/conan-create.log`）
- `conan-verify`（经 `~/tmp/uc2/build-slot.sh` 取槽）：`G0/G1/G2/G3 全 PASS`，
  `reports/conan-verify-report.md` 首行 `**Verdict**: PASS`。
- 该轮为**源码真重建**：日志 `:113` `Calling source()`、`:128` `Calling build()`，
  且 4 条 `Apply patch` 原文（`:129-132`）与 `:133` 的 E011 命中数都在同一份被审日志里
  ⇒ 补丁与就地改写确实绑定当前交付内容。
- 编译/链接：`:143` cross compiling = no、`:249` `RUN: make -j1 MAKEINFO=true`、
  `:294` `RUN: make check -j1 MAKEINFO=true`、`:319` `RUN: make install DESTDIR=<pkg> -j1 MAKEINFO=true`。
- 消费者测试：`:446` DT_NEEDED 原文、`:447` `consumer_passed: 26 / consumer_total: 26 / passed: true`。
- ⚠ 时序披露：上表证据出自 08:33 那一轮 finish 的本地 CI 全量日志；此后配方文件只有
  **一处注释级改动**（把注释里引用的实测报错原文中的家目录前缀写成 `$HOME`，避免静态审查
  把证据引用误读成硬编码路径），不改任何构建逻辑、不改补丁、不改依赖 ⇒ 该轮编译与测试证据
  仍绑定交付内容；CI 侧本就是从零重建，以 CI 产物为最终准绳。
- 上游测试：0 用例（三条实测清点证据见 `test_package/MANIFEST.yml` 头部）⇒
  不存在"上游测试通过"这一档证据，配方跑 `make check` 只走依赖图不含用例。

## 已知限制 / 未覆盖
- POP3 会话、TLS 握手、SASL 协商、IDN 实际解析上网：见「消费者测试口径」能力层三条，
  均附实测错误签名，属平台能力面（无外网、无本地服务对端）限制，而非配方缺陷。
- SASL 机制面本构建不存在（制品仓无 `libgsasl>=2.1`）：`--without-libgsasl` 的后果已被
  断言固定成可观察事实。
- NLS 关断（`--disable-nls`）： gettext 包声明了它不提供的 `libasprintf`，为不悬空链接而关断
  ⇒ 本机消息目录未安装。
- `mpopd` 只做了离线的版本/usage/参数诊断三条断言，未做真实守护进程行为（同样需要本地服务面）。
- 包目录里的 ELF 直接 exec 需要 OHOS 自签与正确的运行库路径；测试通过 Conan 的 `conanrun`
  环境执行，并额外用"剥掉依赖搜索路径必须被拒载"作反证。

---
---

**编译结束**: 2026-09-26 08:33
**最终状态**: built
