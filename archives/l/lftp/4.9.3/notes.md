# lftp 4.9.3 — 适配笔记

> 首轮工作树（2026-09-27）：配方按规范写完，未提交，待 HMBS 真机预检。
> 真机返回后按失败日志继续修复；任何配方改动都会使本文件中的
> “待验证”结论过期，需同步更新。

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | lftp |
| 版本 | 4.9.3（上游发布 2024-11-08） |
| 状态 | 首轮工作树（未验证） |
| 构建系统 | autotools（configure + make， tests/ 下 automake TESTS） |
| 上游主页 | https://lftp.yar.ru/ |
| 上游仓库 | https://github.com/lavv17/lftp（tag v4.9.3） |
| 源码包 | https://lftp.yar.ru/ftp/lftp-4.9.3.tar.gz（3.22 MB） |
| sha256 | 68116cc184ab660a78a4cef323491e89909e5643b59c7b5f0a14f7c2b20e0a29 |
| 产物类型 | application（单个 `lftp` 可执行文件，R38 commands.json） |
| 许可证 | GPL-3.0-or-later |

## 二、上游审计（2026-09-27，基于实测下载的 tarball）

### 依赖（configure.ac / m4 审计）

| 依赖 | 上游要求 | 本配方 | 制品仓状态 |
|------|---------|--------|-----------|
| readline | 硬要求（找不到直接 AC_MSG_ERROR） | readline/8.3，`--with-readline=<包路径>` | published（manifest.yaml，2026-06-05） |
| zlib | 硬要求（AX_CHECK_ZLIB 失败即 ERROR） | zlib/1.3.1，`--with-zlib=<包路径>` | published 1.3.1（manifest.yaml，2026-04-20） |
| openssl | 可选（默认 no） | openssl/3.5.6，`--with-openssl=<包路径>`，启用 FTPS/HTTPS | published 3.5.6（manifest.yaml，2026-05-19） |
| gnutls | 可选 | `--without-gnutls`（单 TLS 后端，确定性） | 不引入 |
| libidn2 | 可选（找不到仅 WARN，继续构建） | 不引入（自动降级） | 不引入 |
| expat | 可选（HAVE_EXPAT 条件编译） | 不引入（自动降级） | 不引入 |
| iconv | 系统（musl libc 自带） | 不引入 | 系统提供 |
| gettext（外部） | AM_GNU_GETTEXT([external])，缺 msgfmt 时用 missing 桩跳过 .gmo | 不引入工具链（.gmo 缺失可接受） | 不引入 |
| modules | `--with-modules`，默认 no | 保持默认（静态单二进制） | — |

### 上游测试（tests/Makefile.am 审计）

`check_PROGRAMS = ftp-mlsd ftp-list http-get ftp-cls-l`，
`check_SCRIPTS = module1 lftp-https-get lftp-queue-kill`，
`TESTS = $(check_PROGRAMS) $(check_SCRIPTS)`，共 **7 个** automake 条目。

| 测试 | 联网 | 离线预检预期 |
|------|------|-------------|
| ftp-mlsd（79 条硬编码 MLSD 解析） | 否 | PASS |
| ftp-list（硬编码 mirror.yandex.ru） | 是 | FAIL（environment） |
| ftp-cls-l（open ftp://mirror.yandex.ru/） | 是 | FAIL（environment） |
| http-get（连接 lftp.yar.ru） | 是 | FAIL（environment） |
| module1（默认无 modules，exit 77） | 否 | SKIP（environment） |
| lftp-https-get（拉取 lftp.yar.ru/features.html） | 是 | FAIL（environment） |
| lftp-queue-kill（纯本地 queue/kill/jobs） | 否 | PASS |

离线预测：TOTAL 7，PASS 2，FAIL 4，SKIP 1。以上为源码审计预测，
一切以真机 test-suite.log 实测为准；conanfile 按实测日志逐项记录 gaps。

### 构建注意点

- configure.ac 无 `host_os/build_os` 分支，triplet 只走标准 autoconf/libtool
  流程；gnulib 自带 m4/musl.m4，对 musl 有感知。
- configure 含标准 `umask 077 && mktemp -d` / `mkdir` 临时目录逻辑。
- `enable_rpath` 默认开启（gettext lib-link.m4），conan 包路径若被
  `-R` 进二进制则不可重定位，故显式 `--disable-rpath`。

## 三、适配决策与依据

1. **E007 补丁（patches/0001、0002）**：2022 版 build-aux/config.guess 无
   HarmonyOS 分支。Windows + Git sh.exe 实测复现：
   - 未打补丁：`config.sub aarch64-unknown-linux-ohos` →
     `Invalid configuration: OS 'ohos' not recognized`（补丁必要性成立）；
   - 仅套用 patch-autotools-ohos.pl 等价变换 →
     `Kernel 'linux' not known to work with OS 'ohos'`（该脚本 2.3 步在
     2.1 成功后恒被跳过，且其模式串会误伤 `uclinux-uclibc*` 分支）；
   - 0001（HarmonyOS guess 分支）+ 0002（含精确 kernel 校验表补项）→
     输出标准三元组 `aarch64-unknown-linux-ohos`，且 gnu/android/musl
     三元组回归验证无变化。
   补丁经 `git apply --check` 校验。无 `--build/--host` 绕过（R1 原生构建）。
2. **mktemp/umask（HMBS unsafe_local_mktemp，liblzf/cdck/complexity 同款）**：
   旧常闭 exit-1 桩已删除（全阶段影子全部 mktemp 且依赖 chmod，
   HMBS_CAP_CHMOD=0 下不可靠）。现为 configure 阶段限定：
   仅当 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时前置 `*conf*` 失败垫片
   （其余 mktemp 委派真实二进制），make/check 不挂垫片；
   另对 `configure`/`config.status` 做 `umask 077->022` 确定性改写
   （E011），即使垫片被旁路临时目录仍可写。
3. **make -j1**：E074/R9，防 HMDFS jobserver fifo EPERM。
4. **AutotoolsDeps + 显式 DIR 前缀**：readline/zlib/openssl 三个检测宏均
   支持前缀参数，用 conan 包路径显式传入；AutotoolsDeps 提供兜底
   CPPFLAGS/LDFLAGS/LIBS（含 -lncursesw 传递闭包）；LD_LIBRARY_PATH
   保障 configure conftest 链接期找到共享依赖（lbreakouthd/1.2.3 同款）。
5. **make check 失败不 veto 打包**：leatherman/1.12.1 同款诚实记录模式。
   test-suite.log 是唯一计数源（TOTAL/PASS/FAIL/SKIP/XFAIL/XPASS/ERROR
   汇总块 + PASS:/FAIL:/SKIP: 行），恒等式 `passed+failed==executed`、
   `executed+skipped<=discovered` 由单源数字构造性保证；gaps 逐项覆盖
   全部未通过项，合计恒等于总数减通过数，否则 fail-closed 报错。
6. **test_package 离线四检查**：版本串内容断言、help 非空断言、
   queue/kill/jobs 空输出断言（含 rc 双条件，防误报）、lcd/lpwd 回显
   断言；计数器由脚本自有，末行打印 HMBS_TEST_PACKAGE_RESULT；
   `set -e` 故意关闭（计数 harness 需要跑完全部检查，见脚本头注释）。

## 四、证伪记录（toybox 教训）

- test_lftp.sh 四项检查均为内容断言（子串/非空/精确匹配），非单纯 exit 0。
- t3 要求 rc==0 且 stdout 为空：若 lftp 二进制缺失或崩溃，rc 非 0 即判 FAIL，
  不会把“没跑起来”当成“jobs 为空”误判为通过。
- 上游 ftp-mlsd 为纯离线解析测试（79 条硬编码数据），可作为“真机 harness
  确实执行了测试”的交叉证据（若其 PASS 而网络项 FAIL，说明 harness 正常）。

## 五、真机失败修复（2026-09-27 预检：configure getcwd 风暴）

- 现象：`shell-init/job-working-directory: error retrieving current directory:
  getcwd: cannot access parent directories` 刷屏，
  `configure: error: working directory cannot be determined`，
  失败点 `autotools.configure()`。
- 根因：profile 注入的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在 HMDFS
  conan 构建缓存目录下 `getcwd()` 失败；且深一层的 `build-release` 子目录
  同样触发风暴、浅一层的源码目录正常（三条知识互相印证：E232、
  DRAFT-cvsgraph-bash-getcwd、DRAFT-6487-classads-configshell-hmdfs-getcwd）。
- 修复（仅 `settings_build.os == "OHOS"` 分支，非 OHOS 保持原 helper 路径）：
  `CONFIG_SHELL=<好shell> /system/bin/sh <source>/configure <args>` 显式启动，
  configure/make/check/install 全部在 `source_folder` 内联执行；
  参数仍取 `autotools._configure_args`（E232 forbid_2：不手写子集），
  `shlex.quote` 保留 `--bindir=${prefix}/bin` 类参数的引号；
  install 保持 `DESTDIR=<package_folder>` 契约。
- 待验证：新一轮真机预检（configure 一次通过、test-suite.log 实测、
  test_package 四检查）。
- 第二轮（2026-09-27 13:30 预检）：getcwd 风暴已消除（好 shell 策略有效，
  configure 已正常启动并进入参数解析），但新失败
  `configure: error: unrecognized option: '-'`——RUN 行显示参数被逐字符拆散
  （`- - p r e f i x = / ...`）。根因是配方把 `autotools._configure_args`
  当成列表做 join+quote，而 conan 2.30 里它是单个 shell-ready 字符串，
  迭代字符串即逐字符。修复：字符串原样透传，仅对旧版 list 形态才 join；
  其余（好 shell、源码目录内联、CONFIG_SHELL pin）保持不变。
- 第三轮（2026-09-27 14:07 预检）：`config.status: can't create
  ./conf44265-16891/subs1.awk: Permission denied`，能力
  `hardlink:0/chmod:0/local_mktemp:1` + 诊断 `unsafe_local_mktemp`。
  根因：旧常闭 mktemp 桩影子全部调用且依赖 chmod（CAP_CHMOD=0 下不可靠），
  真实 mktemp 建出的 0700 目录在 HMDFS 下后续不可写（E011）。
  修复：删旧桩，改用 configure 阶段限定的 `*conf*` 失败垫片
  （FALLBACK=1 才启用，其余委派真实 mktemp，make/check 不挂载）+
  `configure`/`config.status` 的 `umask 077->022` 确定性改写 +
  `config.status` 缺 Makefile 时重跑一次；全程复用 HMBS 注入 TMPDIR。
- 第四轮（2026-09-27 15:57 预检）：`make check-TESTS` 在
  `PASS: ftp-mlsd / ftp-list / http-get` 后打印裸 `Signal 9`，整个 make
  被 SIGKILL，test-suite.log 汇总块未来得及落盘。旧代码在“无日志/无汇总”
  路径直接 `raise ConanInvalidConfiguration`，被门禁计为 *compile* 失败
  （测试失败冒充编译失败）。另发现 `Path` 未导入（`from pathlib import
  Path` 缺失），即使日志存在也会 NameError。
  根因：下一个 TEST 是 `ftp-cls-l`（`open ftp://mirror.yandex.ru/`），
  无超时阻塞等待网络，沙箱离线即 hang 到被外层杀掉；`ftp-list/http-get`
  同为阻塞式 `FileAccess::New` 直连公网（源码见 tests/*.cc），同样无超时。
  修复：① 补 `from pathlib import Path`；② `make check` 经
  `TESTS_ENVIRONMENT="timeout 60"` 逐用例限时（`shutil.which("timeout")`
  探测到才启用，hang 变 FAIL exit 124，汇总仍能落盘；60s 内能过的用例
  不受影响）；③ 中断路径不再 veto 打包——无日志时按 searched 路径
  输出 `executed/passed/failed/skipped=0` + `count=7 environment` gaps
  并 `return` 继续安装，无汇总时按同一文件内 `PASS:/FAIL:/SKIP:` 行做
  部分计数、未跑项记 `environment` gaps 后 `return`；gap 记账失配同样
  只告警不抛异常。计数仍单源自 test-suite.log，无 stdout 数数、无减法
  推导、无 returncode 猜测分支。
- 第五轮（2026-09-27 17:18 预检）：`timeout 60` 已生效
  （`ftp-list.log Error 124` 即被限时杀掉），但 `make check` 在首个失败处
  即停（`check-TESTS Error 2`），后 5 个 TEST 未来得及跑，test-suite.log
  仍无汇总，标记只能报 `executed=0`；且 `package()` 在
  `doc/install-man1` 以 `Error 64` 失败（`install -c -m 644`）。
  根因：① 缺 `-k`（keep-going），首 FAIL 即终止整个 check；
  ② OHOS toybox `install` 不支持 `-c`，configure 探到的 system install
  在 man 安装时报用法错误（exit 64）。
  修复（与上轮不同策略）：① `make check` 改 `make check -j1 -k`
  （两分支及 marker command 同步），首 FAIL 后继续跑完 7 项使汇总落盘；
  ② 无 test-suite.log 时新增 `tests/*.trs :test-result:` 回退解析
  （parallel harness 单源，与汇总同源），有部分结果即按部分计数+未跑项
  environment gaps 记录后继续打包；③ configure 期
  `export INSTALL="<src>/install-sh -c"` 并在 `make install` 以
  `INSTALL="<src>/install-sh -c"` 覆盖，绕开残缺 system install。
- 第六轮（2026-09-27 17:46 预检）：`-k` 已跑完 7 项
  （ftp-mlsd PASS、ftp-list 超时 124、http-get PASS、ftp-cls-l 超时 124、
  module1 SKIP、lftp-https-get FAIL、lftp-queue-kill PASS），但 `.trs`
  回退只计 5/7（2 项“unrun”）；且 `install-sh not found` 两处告警，
  man 安装仍 `Error 64`。
  根因：① 超时进程 exit 124 时 parallel harness 不写 `.trs`（正常 FAIL
  exit 1 才写，如 lftp-https-get），故 124 的两项无记录；② `install-sh`
  只按顶层路径查找，实际不在顶层故未命中。
  修复（与上轮不同策略）：① 新增 `sh` 调用的超时包装脚本
  （`timeout 60 "$@"`，124 转 exit 1 并 stderr 留痕，经
  `TESTS_ENVIRONMENT="sh <wrapper> 60"` 挂载，无需 chmod），使超时项落
  为普通 FAIL 并写入 `.trs`；② 新增 `_find_install_sh()` 多候选+浅层
  递归查找，configure 与 install 均用查到的路径覆盖 `INSTALL`。

## 六、待真机验证（下一轮输入）

1. conan create 全流程（configure 是否一次通过；readline/zlib/openssl 三
   检测是否命中 conan 包路径；C++ 链接是否缺 -lncursesw/-ldl/-lpthread）。
2. tests/test-suite.log 实测：TOTAL/PASS/FAIL/SKIP 与上表预测是否一致；
   HMBS_UPSTREAM_TEST_RESULT 数字与恒等式自检。
3. test_package 四检查实测：重点关注 t2（help 输出是否含 open）、t3
  （jobs 是否绝对静默，有无 banner 噪声）。
4. 产物：bin/lftp 是否为 aarch64 OHOS 可执行文件；man/locale 是否正常安装。
5. 若 configure 失败，优先看 config.log 中 guess/sub 相关行（E007/E064），
   其次看 conftest 链接错误（缺传递库）。
