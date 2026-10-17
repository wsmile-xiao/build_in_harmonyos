# validns 8.00.11.0 适配笔记

## 版本映射与取数路径（版本串形态特殊，W0 实核）

- 平台版本 **8.00.11.0** = Debian/Ubuntu 源码包版本 **8.0+really0.11.0**（8.0 与 0.11.0
  拼合去 `+really`），对应上游 **DNS-OARC validns v0.11.0**。
- 上游权威仓：https://codeberg.org/DNS-OARC/validns （GitHub 镜像 DNS-OARC/validns；
  旧上游 git.verplant.org/validns 的 git:// 已不可达：access denied or repository not
  exported，2026-09-22 实测）。
- 本次取数路径（三路实核之一：上游官方发行物）：
  - URL: `https://www.dns-oarc.net/files/validns/validns-0.11.0.tar.gz`
    （codeberg release v0.11.0 说明原文给出的发行物地址与 sha256）
  - sha256: `76d11af7930231bb5914643b5247df69ac85327dc490ba04b3c1bb207697f4e8`
    （2026-09-22 下载实测 == 发行说明锚定值）
- Debian 等价物（第二路交叉验证）：
  `https://deb.debian.org/debian/pool/main/v/validns/validns_8.0+really0.11.0.orig.tar.xz`
  sha256 `a41d5dcfe15c1a922c3f7c4e195d9c59b8f028a9488f486ab981a6dcf244088f`
  （352192 字节；dsc 实核 Build-Depends: libjudy-dev, libssl-dev,
  libtest-command-simple-perl <!nocheck>, pkgconf）。**取上游原始发行物**的原因：
  Debian orig 是重打包（顶层目录改名 `validns-8.0+really0.11.0/`，且**不含**生成的
  configure，需 autogen.sh），上游原始包自带 configure，符合 R21 平台检测优先口径。
- 上游测试夹具随源码同源：t/zones 47 个文件、t/issues 30 个、t/roundtrip 3 个。

## W0 依赖与可移植性实核（2026-09-22）

| 项 | 结论 | 证据 |
|---|---|---|
| judy（硬依赖，configure.ac `AC_CHECK_LIB([Judy],[Judy1Test])`） | ✅ ohpcd 有 judy/1.0.5，binary `4b97726...` os=OHOS arch=armv8 shared=False | `conan list -r=ohpcd judy` + `conan list -r=ohpcd "judy/1.0.5:*"` |
| openssl（硬依赖，`PKG_CHECK_MODULES([libssl]/[libcrypto])`，需 3.0+ 的 EVP 探针） | ✅ ohpcd 有 openssl/3.5.6（另有 3.5.6.1…4.0.1），binary `6b129b0...` os=OHOS armv8 | `conan list -r=ohpcd "openssl/*"` |
| pkgconf（configure 用 PKG_CHECK_MODULES，CI worker 无系统 pkg-config） | ✅ ohpcd 有 pkgconf/3.0.5（仓库 8 个配方同款 tool_requires） | `conan list -r=ohpcd "pkgconf*"` |
| ISA 专属头（altivec/mmx/3dnow/immintrin） | ✅ 无 | grep 全源码 0 命中 |
| glibc printf 钩子（printf.h/register_printf_*） | ✅ 无 | grep 全源码 0 命中 |
| perl（仅测试面：TAP 套件 t/test.pl） | ✅ 设备 `~/.harmonybrew/bin/perl` 5.44.0；CI worker `/data/service/hnp/bin/perl` 5.42.0；两者 core Test::Harness/Test::More 实测可加载 | 本机实测 |
| Test::Command::Simple（t/test.pl 的 use 目标，非 core） | ❌ 两端皆无 → 以 CPAN 官方发行物作 conandata 第二 source，构建期 PERL5LIB 注入（见下） | perl -MTest::Command::Simple 实测 BEGIN failed |

## 编译环境

- 构建系统: autotools（tarball 已 bootstrap：含 configure/Makefile.in/config.guess/sub，
  无需 autoreconf，也就不需要 automake/autoconf tool_requires）
- 编译日期: 2026-09-22
- 编译器: clang（OHOS aarch64）
- 状态: built

## 编译步骤

`conan create`（W3 与采信轮同源）：
1. `source()`：取上游 tarball（strip_root）+ CPAN Test-Command-Simple（解到
   `test-perl/`，仅测试面，不进 package）。
2. `generate()`：AutotoolsToolchain + AutotoolsDeps（judy/openssl 的 -I/-L/-l）+
   PkgConfigDeps（生成 libssl.pc/libcrypto.pc 供 PKG_CHECK_MODULES）+
   VirtualBuildEnv（把 pkgconf 挂上 PATH）。
3. `build()`：config.guess/config.sub OHOS 幂等补丁（见下）→ configure → make →
   `make check`（PERL5LIB 注入后经 perl Test::Harness 跑 t/test.pl，再依次
   ./test64、./test32hex、./testcompose）。
4. `package()`：`make install` → `<pkg>/bin/validns`（+ man1 与文档）。
   judy/openssl 静态链入可执行文件（R26：系统同名库不动态链接）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备 `uname -s`=HarmonyOS，上游 config.guess 不识别，configure 报 unable to guess | 上游 config.guess（2024 版）无 HarmonyOS 分支 | 配方内幂等 Python 补丁：UNAME_SYSTEM 分支早退 `aarch64-unknown-linux-ohos`（锚点 193 行 case 行，conanfile `_patch_config_for_ohos`） |
| 2 | `sh config.sub aarch64-unknown-linux-ohos` → `OS 'ohos' not recognized`（实测） | 2024 版 config.sub 结构变化：`case $basic_os in` 的 `*-*` 分支先按 `-` 拆 kernel/os，最终校验表无 ohos | 同一补丁函数内三处最小插入：basic_os 分支（linux-ohos→kernel=linux,os=ohos）、最终 OS 表 `| ohos*`、kernel-os 组合表 `| linux-ohos*`（三锚点均已实测 `config.sub` 输出 `aarch64-unknown-linux-ohos` rc=0） |
| 3 | t/test.pl `use Test::Command::Simple`；两端 perl 皆无该模块；缺失时 test.pl 退化为「1 个失败断言」（use_ok 失败计入 done_testing）→ make check 必败 | 该模块非 perl core；conan 无此包；CI 无网络装包 | CPAN 官方发行物 Test-Command-Simple-0.05 作为 conandata 第二 source（sha256 4d9dc422…），build() 里 PERL5LIB 指向其 lib/。纯 Perl、仅依赖 core（IPC::Open3/IO::Select/Test::Builder），等价 Debian `libtest-command-simple-perl <!nocheck>`（仅测试面，不参与打包） |
| 4 | 不 tool_requires conan perl | conan perl/5.42.2 是 OHOS 交叉构建，同机 dlopen Cwd.so 失败（Perl_my_cxt_init 崩溃，见 device-facts §一.23） | `make check` 用系统 perl：设备 harmonybrew perl 5.44 / CI worker HNP perl 5.42，均实测可加载 Test::Harness |
| 5 | `./config.status: ./confXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | 上游 configure 内嵌 `umask 077 && mktemp -d ./confXXXXXX`（15437/15442 行）；HMDFS 上 077 目录落盘为 drwx--S---，写入必拒（§一.10） | build() 在 configure 前对 configure 做 `umask 077→022` 幂等替换（`_fix_configure_umask`；config.status 由 configure 生成、继承该 umask）。与仓库 98 处同款修法一致 |
| 6 | `checking for libssl... no` → `Package requirements (libssl) were not met` | 上游查询系统安装态的 pc 名 `libssl`/`libcrypto`；conan openssl 包注册的 pc 名是 `openssl`，名字对不上 | 用 configure 自身的 `<MOD>_CFLAGS/_LIBS` 覆盖（错误信息原文建议的旁路），值取自 `self.dependencies["openssl"]` 的 cpp_info 拼装（零硬编码路径）；同时保留 pkgconf tool_requires（PKG_PROG_PKG_CONFIG 仍要求二进制存在）。实测 `checking for libssl... yes` |
| 7 | PERL5LIB 已注入 @INC 却仍 `Can't locate Test/Command/Simple.pm` | `get(strip_root=True)` 把发行物目录名一并剥掉，模块实际落在 `test-perl/lib/`，PERL5LIB 多拼了一层发行物名 | PERL5LIB 指向 `<source_folder>/test-perl/lib`（strip_root 后的直接 lib 树），实测模块命中 |

## 源码修改

- 无 patches/*.patch 文件；config.guess/config.sub 的 OHOS 适配以
  conanfile.py `_patch_config_for_ohos()` 幂等程序内补丁实现（仓库既有形态：
  aircrack-ng/burp2 同款思路）。原因：上游 2024 版 config.sub 与仓库既有
  patch 文件的锚点（旧版行文）不匹配，程序内补丁可对三处锚点断言后精确插入，
  并在补丁失败时保持原文件（不产生半成品）。PF5 无涉及（无 patches/*.patch，
  无 `__OHOS__` 编译宏注入）。

## 依赖版本

- judy/1.0.5（ohpcd，OHOS armv8 binary 已发布）
- openssl/3.5.6（ohpcd，OHOS armv8 binary 已发布）
- pkgconf/3.0.5（tool_requires，构建期）
- Test-Command-Simple-0.05（仅测试面，CPAN 官方源，PERL5LIB 注入）

## 上游测试三步法申报（R51）

- **清点（适配前）**：上游测试 = `make check`（src/Makefile.am 唯一 test 契约）=
  ① TAP 套件 `t/test.pl`（perl Test::Harness 驱动，断言数运行期决定：套件对
  默认/-n2/-n4/-n6/-n8 五组线程形态循环跑 zone 校验）+ ② 三个 C 自测程序
  test64/test32hex/testcompose（各自打印 `All N tests successful.`，N 可数）。
- **运行**：设备采信轮 `conan create` 内 `make check` 真实执行；
  **计数口径：TAP 断言数（取 test.pl 的计划行/结果行）+ 三个 C 程序各自
  `All N tests successful.` 的 N，四分项取自同一份设备日志**，不与其它口径混用。
- **回填**：PR 正文统计表按最终设备日志复算（TOTAL=PASS+FAIL+SKIP+NOT_RUN），
  test_package 消费者测试与鸿蒙特有验证单列，不混入上游数。

## 验证结果

```bash
# 采信轮（conan_verify_round.sh）+ conan-verify 八门禁结果见 reports/ 与 PR 正文
```

## 交付物

| 文件 | 说明 |
|------|------|
| `<pkg>/bin/validns` | DNS/DNSSEC 区域文件验证器 CLI（judy/openssl 静态链入） |
| `<pkg>/share/man/man1/validns.1` | 手册页 |

## 注意事项

- `validns -V` 打印的是上游 PACKAGE_VERSION `0.11.0`，不是平台版本串
  8.00.11.0（版本映射见第一节）；test_package/test.sh 按真实值断言。
- `make check` 的 TAP 断言数是运行期值（线程形态循环），不同环境可能略有差异；
  统计以采信轮设备日志为准。
