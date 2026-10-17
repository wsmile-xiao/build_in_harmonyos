# lbdb 0.57 适配笔记

## 0. 包与源
- 包 `lbdb` / 版本 `0.57`（逐字一致，未归一化）。上游主页 https://www.spinnaker.de/lbdb/ 。
- 构建系统：autotools（`configure` + `configure.ac` + 生成的 Makefile，autoconf 2.72 生成）。
- 官方源 URL：`https://www.spinnaker.de/lbdb/download/lbdb-0.57.tar.gz`
  - 从下载页 grep 真实 href 得到（相对 `href="lbdb-0.57.tar.gz"`，解析目录 `/lbdb/download/`；同页有 `.asc` 分离签名 = 正式发布）。⛔ 未用 Debian 池址（PF7）。
  - sha256 一手实测：B 机连续 3 次 GET，均 208683 B、`cmp` 三件全等，sha256 = `212fe2e40df5ed3e5496bc5e821e4b0683a6c9523b8885e7e87b634bcf923a88`，与 Debian sid .orig 索引逐字节一致（仅作交叉核验）。
  - 站点 3/3 稳定可达（首页与下载页各 3 次采样字节数恒定），非间歇。

## 1. 一手语言 / shebang 普查（解包后 find + head -1）
SCT 台账"语言 c/cpp（c/cpp 文件 6、其它语言脚本 0）"**与盘上不符**，属解析漏计：
- 顶层 109 个文件。C 源 6 个：dotlock.c / fetchaddr.c / helpers.c / qpto8bit.c / rfc2047.c / rfc822.c；头 4 个：dotlock.h / helpers.h / rfc2047.h / rfc822.h。**C++ = 0**。
- `.cpp/.cc/.cxx/.pl/.pm/.py/.sh` 扩展名计数全为 0 —— 但命令面是 **45 个 `*.in` 模板**：configure 用 `AC_CONFIG_FILES` 展开成
  `lbdbq.sh munge.awk lbdb-fetchaddr.sh vcquery.pl lbdb-munge.sh lbdb_lib.sh nodelist2lbdb.pl palm_lsaddr.pl mutt_ldap_query.pl $MODULES_SH $TACAWK ...`。
- **shebang 直方图**（解包源文件第一行 == `#!`）：
  - `#! @SH@` 30 个（lbdbq + lbdb-fetchaddr + lbdb-munge + lbdb_lib + 全部 m_*.sh 查询模块）
  - `#! @PERL@` 3 个 + `#! @PERL@ -w` 1 个（nodelist2lbdb.pl / palm_lsaddr.pl / vcquery.pl / mutt_ldap_query.pl）
  - `#! @AWK@ -f` 2 个（munge.awk / tac.awk）
  - 另有 `#! /bin/sh`（configure/config.guess/config.sub/install-sh/mkinstalldirs/testsuite）与 1 个 `tests/gen-maildir => #!/usr/bin/perl`（测试脚手架，非交付命令）
  - Emacs Lisp 2 个（lbdb.el、lbdb_bbdb_query.el）+ `lbdb-pkg.el.in`；Objective-C 1 个（ABQuery.m，仅 macOS，configure 用 XCODEBUILD 守卫，OHOS 上不构建不安装）。
- 结论：本包是 **shell 脚本主导 + perl/awk/elisp 混编的多语言命令面**，"其它语言脚本 0"不成立。

## 2. ★运行期解释器探针（决定交付形态，B 机原文）
`command -v` / 绝对路径存在性 / 实跑：
```
perl -> /data/service/hnp/bin/perl        (perl 5.042.0 / v5.42.0 built for aarch64-linux；可运行)
bash -> /storage/Users/currentUser/.harmonybrew/bin/bash   (用户专属，不可移植)
sh   -> /bin/sh (toybox ash, 存在)
env  -> /usr/bin/env (存在)
python3 -> .harmonybrew/bin/python3
gcc -> MISSING   clang -> MISSING   (编译器只经 conan toolchain 注入)
aclocal -> MISSING
/usr/bin/perl   -> MISSING
/bin/perl       -> MISSING
/usr/bin/bash   -> MISSING
/bin/bash       -> MISSING
/usr/bin/python3-> MISSING
```
能力探针（toybox `/bin/sh` 实跑，脚本用到的 bash 语法逐条判"本平台可解析吗"）：
```
[[ ]]                -> ASH_DOUBLEBRACKET_OK
命名函数 f(){...}     -> ASH_FUN_OK
数组 arr=(p q)        -> ASH_ARRAY [p q]
${v//o/0}            -> ASH_SUBST f00BAR
[ x == y ]           -> ASH_STREQUAL_OK
local                -> ASH_LOCAL 1
/usr/bin/env perl    -> ENVPERL_OK
/usr/bin/env gawk    -> ENVGAWK_OK
/bin/awk（toybox）    -> TOYBOXAWK_OK
/data/service/hnp/bin/bash -c pwd  -> shell-init: error retrieving current directory: getcwd ... rc=1
```
用到 bash 语法的交付脚本：`lbdbq.sh.in`、`m_muttalias.sh.in`（`[[ ]]`）、`m_pine.sh.in`（数组/function）—— **toybox /bin/sh 全部实测支持**。
- **判据落点**：解释器（sh/awk/perl）在本平台都存在且可运行（perl 经 env 可用）⇒ **属 E049 家族处理 shebang，非"perl 缺失停手"情形**。lbdb 的核心命令面（lbdbq + shell 模块 + awk munge/tac + 编译的 C helper）只需 sh+awk；perl 只服务 4 个可选查询模块（m_fido/m_palm/m_ldap/m_vcf）。

## 3. 依赖 / 发布态（W0/R36）
- `preflight_check.sh lbdb/0.57` → 无依赖声明、无依赖需检查（首次适配正常）。
- 构建期链接：`Makefile.in` 用 `LIBICONV=@LIBICONV@` 仅链进 fetchaddr/qpto8bit；`AM_ICONV`（configure.ac 第 36 行）。OHOS libc(musl) 提供 `iconv`/`<iconv.h>` ⇒ 预期 `@LIBICONV@` 为空、无外部库依赖。`#include <iconv.h>` 出现在 rfc2047.c。
- 无 zlib/openssl/glib 等。⇒ **本包 requires 为空**。
- configure 探测的外部程序（finger/gpg/getent/abook/mutt…）都是运行期可选模块，`AC_PATH_PROG` 找不到即禁用该 m_* 模块，非构建依赖。

## 4. E007（config.guess 不识别 HarmonyOS）
- 实测：未打补丁时 `sh config.guess` rc=1 "unable to guess system type"（`uname -s = HarmonyOS`、`uname -m = aarch64`、release "HongMeng Kernel 1.12.0"）。config.guess 时间戳 2024-07-27 虽新，但仍无 HarmonyOS 分支。
- config.sub（2024-05-27）已接受 `aarch64-unknown-linux-ohos`（rc=0），但需 `ohos-linux` 内核-libc 别名。
- 处方（E007 明令 ⛔ 用 --build/--host 绕，会误判交叉编译、跳过 AC_RUN_IFELSE/AC_PATH_PROG 生成错 config.h）：用仓库脚本 `scripts/patch-autotools-ohos.pl <config.guess> <config.sub>`。**实测该脚本在本包锚点齐全（LIBC=android / NetBSD case 均在），Score 4/5 打补丁后**：
  - `config.guess` → `aarch64-unknown-linux-ohos`（rc=0，CC 置空也成立）
  - `config.sub aarch64-unknown-linux-ohos` → 原样回显 rc=0
- 因 CI 干净环境不注入 `OHC_SKILL_ROOT`（335 个 recipe 的 build() 调用会静默跳过），故把脚本产出的 diff **落成自包含补丁** `patches/0001-config-guess-sub-ohos.patch`（同 jigit 0001 思路），由 `apply_conandata_patches` 应用。
- configure 手工驱动：钉 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`（HNP bash 被拒 getcwd，autoconf 前言会用 $CONFIG_SHELL 重执 configure 致 "working directory cannot be determined"，jigit 同发现）；钉 `SH=/bin/sh AWK=/bin/awk` 让模板 `@SH@`/`@AWK@` 直接落到可移植解释器。

## 5. E049（shebang 可移植化）
- 根因：`AC_PATH_PROG(SH/PERL/AWK)` 把 **构建机绝对解释器路径**烧进生成脚本的 `#! @SH@/@PERL@/@AWK@`。bash 会被探测成 harmonybrew 用户专属路径（换机/换用户即失效）。
- 最终方案（配方 package()）：对 `bin/`、`libexec/` 下每个交付脚本，读第一行 `#!`，按解释器 basename 归一：
  - sh/ash/dash → `#! /bin/sh`（保留原 tail）
  - bash/ksh → `#! /bin/sh`（toybox ash 实测支持 lbdb 脚本用到的全部语法）
  - perl → `#! /usr/bin/env perl`（本平台无 /usr/bin/perl；perl 在 PATH 的 hnp）
  - awk/gawk/mawk/nawk → `#! /bin/awk -f`（toybox awk，恒在）
  - ELF 二进制（fetchaddr/qpto8bit/lbdb_dotlock）首行非 `#!` ⇒ 跳过，仅补可执行位。
  - 另在 configure 传 `SH=/bin/sh AWK=/bin/awk` 作为第一道，package() 归一是主案。**收尾-2 本轮按 config.log 一手回读，把"双保险"的成色写实**（同一次 `conan create`）——
    `SH='/bin/sh'`（**钉住了**；上游 configure.ac 的三段 bash/ksh/sh 探测外面都写着 `if test "x$SH" = x ; then`，命令行预设让三段全短路，顺带躲掉 `$BASH -posix` 这种 harmonybrew 用户专属路径）；
    `AWK='/data/service/hnp/bin/gawk'`（**没钉住**；`AC_PATH_PROG(AWK,...)` 展开为无条件赋值 `AWK=$ac_cv_path_AWK`（生成的 configure:5611），其后 `NAWK/GAWK/MAWK` 三段专用探测逐个覆盖）；
    `PERL='/data/service/hnp/bin/perl'`（**无可钉目标**；本机 `/usr/bin/perl`、`/bin/perl` 均 MISSING）。
    ⇒ 构建树对照读数 `munge` 首行就是 `#! /data/service/hnp/bin/gawk -f`（机器绑定），交付目录里变成 `#! /bin/awk -f`
    ——**归一层是真在承重的，不是摆设**；判"钉住了"必须回读 config.log，不能只看传了参数。

## 6. 其它坑
- **E002 /tmp 只读**：`lbdbq` 用 `tmpdir=${TMPDIR-/tmp}/query.$(hostname).$$`。消费者测试脚本显式 `export TMPDIR=<scratch>`，否则 mkdir 失败 exit 1。
- **HMDFS 0660**：configure/config.guess/config.sub/install-sh/mkinstalldirs 落地非可执行，build() 里逐个 `chmod +x`（jigit 同款）。
- `mutt_ldap_query.pl` 内含 `MODULES_PATH="/usr/local/lib ..."` 等默认值（在交付源码内，非配方/ conandata 注入，PF6 不扫源文件）；只影响可选 m_ldap，不影响 lbdbq 主体。

## 7. 已试失败方案（真实第一条错误，均已在盘上复现并修复）
- **create #1**：configure 跑到末尾，在生成/执行 `config.status` 时断于 E129
  `./config.status[745]: can't create ./confW1XoKr/subs1.awk: Permission denied`
  → `config.status: error: could not setup config files machinery`。
  根因：autoconf 2.72 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建私有 scratch 目录，
  HMDFS 上该目录建出后内核拒绝其中的 O_WRONLY 创建（toybox mktemp 语义），plain mkdir 才可写。
  修复：build() 内 `replace_in_file` 把 configure 该 here-doc 片段（单处，已核 count=1）换成
  `tmp=./conf$$-$RANDOM; mkdir "$tmp"`（同 jigit E129 处方）。
- **create #2**：build()+package()+make install 全部成功（iconv 在 libc 命中、无 libiconv 依赖），
  产物已建；失败只在 test_package：`lbdbq: inaccessible or not found`（rc=127）。
  根因：`VirtualRunEnv(scope="build")` 把包 bin 的 PATH 折进 **conanbuild** 环境，且无 layout() 的
  test_package 只聚合生成 `conanbuild.sh`（日志实证），我却 `self.run(env=["conanrun"])` → PATH 空。
  修复：test_package `env=["conanbuild"]`。
- **修 env 后 A9**：`lbdb-fetchaddr`（不带 -f）内部对默认 db 路径 `$HOME/.local/share/lbdb` 做
  嵌套 `mkdir -p`，HMDFS 上 chmod 被忽略 ⇒ 中间目录 `.local`/`.local/share` 缺属主 +x ⇒
  `mkdir: cannot create directory '.../.local/share': Permission denied`。
  修复：round trip 用 `lbdb-fetchaddr -f <scratch>/m_inmail.db`（写进已存在、可遍历的 scratch），
  并 `INMAIL_DB=<同一文件> lbdbq joe` 让 m_inmail 读它（`M_INMAIL_DB=${INMAIL_DB:-fallbackdb}`）。

## 8. 测试口径（rule4 / R51 / R34）
- 上游：`tests/` 是 7 个 autotest `.at` 套件、`AT_SETUP` 合计 **20 个用例**（静态清点与注册面见 §13.1–13.2），
  **已在交付形态下真机实跑**（`make -C tests check-local`）——执行 14 / 通过 12 / 跳过 6 / 失败 2，
  五维账本见 §13.2，两条失败例的第一条真实错误与根因链见 §13.3，日志在
  `reports/upstream-make-check.log`、`reports/upstream-testsuite.log`、`reports/upstream-skips-only.log`。
  ⚠ 本节此前写的"环境性不可在本平台执行（需真实 mutt/gnus、`tests/gen-maildir` 的 `#!/usr/bin/perl` 在本平台缺失）"
  **是首棒误判、已被 §13 的实跑推翻**——perl 实测在 `/data/service/hnp/bin/perl`（5.42.0）可运行（§2），
  6 枚 skip 的原因是 abook/mu/notmuch 三个外部程序缺失，2 枚失败是 HMDFS 无 `link(2)`（§13.3）；
  **两者都不是"没环境"**，按 R51 口径如实分栏呈现，不缩分母也不把 skip 写成 pass。
- 交付：消费者自测 `test_lbdb.sh`，静态断言站点 **10**（A1–A10，见脚本头注释），`SUMMARY lbdb consumer: total=.. passed=.. failed=..` 与站点同源。
- 鸿蒙特有：A5/A6/A7 直接验证解释器在"无 /usr/bin/perl、无 /bin/bash、perl 仅在 hnp"的平台现实下可解析；A9 端到端往返在 toybox /bin/sh + toybox awk 下驱动编译的 fetchaddr/lbdb_dotlock，证明无 bash 也能跑。

## 9. 构建/验证结果
- **conan create 端到端绿（第 3 次，本机 B）**：`CREATE_RC=0`。
  - RREV `75beb304afe7db959b8e31a4810f92a3`（**2026-09-28 收尾-7 给 `conandata.yml` 三处标量补双引号后翻档**；旧值 `5546d0463ecf118ef6daa8a192b92cdf` 是 09-27 00:15 那一档，见 `reports/conan-create.log:10` 现算）
  - PKGID `6b129b068851896169fae42d399fa922d239ce8a`
  - 包修订 PREV `fe8ca3de1de5c4e6dc9fd3d4917be2ac`
  - 包目录 `~/tmp/ch/home-lbdb/p/b/lbdb6dbfa375d0858/p`（build 目录 `.../b/build-release`）
- configure 读数：`checking for iconv... yes` / `working iconv... yes` /
  `compatible with its POSIX signature... yes` ⇒ **无 libiconv 依赖**；外部程序（finger/gpg/getent…）
  全部 `no` → 相应 m_* 模块优雅禁用。
- 交付产物（package bin/libexec 实测 20 脚本 + 3 二进制 + COPYING）：
  - bin: lbdbq、lbdb-fetchaddr（sh）、lbdb_dotlock（ELF）、nodelist2lbdb、mutt_ldap_query（env perl）
  - libexec: fetchaddr、qpto8bit（ELF）、munge（`#! /bin/awk -f`）、lbdb-munge/lbdb_lib、12 个 m_*（sh）、
    palm_lsaddr、vcquery（env perl）
  - **shebang 实测归一**：全部 shell→`#! /bin/sh`、4 个 perl→`#! /usr/bin/env perl`、awk→`#! /bin/awk -f`，
    0 个机器绑定路径（`SH=/bin/sh` configure 钉 **确实生效** + package() 归一为兜底双保险）。
- 消费者自测：`SUMMARY lbdb consumer: total=10 passed=10 failed=0`（A1–A10，静态站点 10 同源）。
  A9 round trip 原文 `lbdbq: 1 matches  joe@example.com  Joe Bloggs  <date>`（真驱动 fetchaddr+dotlock 二进制 + awk munge）；
  `m_finger_query: not found` 是未装模块的良性 `|| true` 噪音，非失败。
- **conan-verify / W3 本地 CI / `.ci-result.json`——已跑并绿**（首棒当时受 `conan create` 3 次上限所限未跑；
  现由取证-lbdb（08:18–08:21）与收尾-2（22:31–22:37）两轮补齐，逐节读数、两档 RREV 与 finish 逐步判决见 §11.1–11.7）。
  G4/L2/L4/L5 属工具查法所致的 SKIP（`@ohpcd/stable` 引用裸查不到包 ID），真生效面是 G0–G3；
  两条负信号 = **L2（4 条非阻塞 warn，判定 `pass`，见 §13.4）** 与 **L4（真 warn，见 §13.5）**，在 §13.4/§13.5 分栏披露，⛔ 对外只报"全绿"、⛔ 也不得把 L2 说成 `L2_RESULT=warn`。

## 10. 适用边界
- 命令面只依赖 toybox `/bin/sh` + `/bin/awk`；**无 /bin/bash、无 /usr/bin/perl** 平台下 lbdbq 主体仍可用（perl 仅 4 个可选查询模块，且 m_ldap 还需 perl Net::LDAP、m_fido/m_palm 需外部数据源，运行时优雅降级）。
- 若目标机 perl 不在 PATH，则 nodelist2lbdb/palm_lsaddr/mutt_ldap_query/vcquery 及 m_fido/m_palm/m_ldap/m_vcf 失效，但主查询链路（lbdbq + m_inmail/m_passwd/... + fetchaddr/dotlock/munge）不受影响。
- 消费者测试的 round trip 规避了 HMDFS 嵌套 `mkdir -p`（用 `-f` 写入已存在目录）；真实用户环境 HOME 下由 lbdb-fetchaddr 自建的 `.local/share/lbdb` 若遇同样权限限制，属 HMDFS 平台行为、非配方缺陷，已在 §7 记录。

## 11. 收口读数（取证-lbdb，B 机 `~/qzy/主理-74-lbdb-0.57`，本节首写时 HEAD `a544dbf72f`；**2026-09-28 收口档已由 §11.3–§11.7 逐条更新，凡与本节首写值冲突者以更新节为准**）

一条 `python3 scripts/ohc-run.py finish lbdb 0.57 built`（起先 `sh ~/tmp/uc2/gate.sh --light` 过闸、
`sh ~/tmp/uc2/build-slot.sh --kind short --wait 1800 --mem 2500` 拿机动短槽）覆盖
close-archive[2/10] + conan-verify[4/10] + W3 本地 CI[5/10]，共触发 `conan create` 2 次（预算 2 次用满）。
运行时刻 2026-09-27 08:17–08:21 CST；`--mem` 用的是机动短单的规定门槛 2500MB（开跑前
`gate.sh` 实测 MemAvailable=5524MB），**不是本包峰值实测量**——本包无重型编译单元，未另跑 memcap 探针。

### 11.1 conan-verify 逐节（`reports/conan-verify-report.md`，第 3 行 `**Verdict**: PASS`）

`## Gx: ✅ PASS` 是固定表头，判决只认下一行子行：

| 节（行号） | 子行原文 | 真判决 |
|---|---|---|
| L8 G0 | L9 `**Knowledge hit**: E490` | 命中知识条目（非阻塞） |
| L17 G1 | L18 `✅ name 声明` | 真过 |
| L31 G2 | L32 `✅ conan create 成功` | 真过 |
| L35 G3 | L36 `✅ 无系统同名库冲突（R26 通过）` | 真过 |
| L38 G4 | L39 `⚠️ 无法找到程序包 ID` | **SKIP**（不是真判过产物完整性） |
| L41 L2 | L42 `⏭️ 跳过（无 cache 路径）` | **SKIP** |
| L44 L4 | L45 `⏭️ 跳过（无 cache 路径）` | **SKIP** |
| L47 L5 | L48 `⏭️ 跳过（无 cache 路径）` | **SKIP** |

⇒ 本次 verify 真正生效的只有 G0/G1/G2/G3；G4 与 L2/L4/L5 因按裸引用查不到包 ID 而空转
（G2 用 `--user=ohpcd --channel=stable` 导出，缓存里是带 user/channel 的引用）。
**不得把该报告当成 L2/L4/L5 已验证的证据**；做过 L 级检查的是 W3（见 11.3）。

### 11.2 verify 侧 conan create 日志（`reports/conan-create.log`）

> **⚠ 本节是 2026-09-27 00:17 那一档的原文（`L10/L315/L316` 引的是旧 RREV `5546d046…` 与旧 CONAN_HOME `home-lbdb`）；该日志已于 2026-09-28 **17:04 那轮 finish 再次重生成（现件 105 行、缓存命中未重编译）**、行号与取值整体换档。**现行交付档** `75beb304afe7db959b8e31a4810f92a3` 见 §11.4（`conan-create.log:10` 实读）；**现件其余锚**：`(test package): Calling build()` `:89`、`SUMMARY lbdb consumer` `:104`。本节下面的 `L98/L315/L316/L342/L357` 是 **09-27 档原文**、现件已不存在，⛔ 当现行值引用。

- L10 `lbdb/0.57@ohpcd/stable: Exported: lbdb/0.57@ohpcd/stable#5546d0463ecf118ef6daa8a192b92cdf (2026-09-27 00:17:26 UTC)`
- L98 `lbdb/0.57@ohpcd/stable: Calling build()` ← 真编译，不是缓存复用
- L315 `Full package reference: ...#5546d0463ecf118ef6daa8a192b92cdf:6b129b068851896169fae42d399fa922d239ce8a#34e139dedb2371d32e0e7f2100e986c6`；L316 `Package folder ~/tmp/ch/home-lbdb/p/b/lbdbfe829febf98bd/p`
- （09-27 档）L342 `(test package): Calling build()`、L357 `SUMMARY …` —— **现件已换档**：`:89` `(test package): Calling build()`、`:104` `SUMMARY lbdb consumer: total=10 passed=10 failed=0`

### 11.3 W3 本地 CI（`reports/w3-local-ci.log`，**共 468 行 = 2026-09-28 17:07 收口档**；sha256 见本节下方「结果登记件 `.ci-result.json`」段——§11.4 是 RREV 分档、**没有 sha256**，早前「见 11.4 末」的指向已更正）

> **本节行号锚全部绑定 468 行这一档（2026-09-28 17:07）**——此前 473（09-27 08:21）、471（09-28 12:47）两档均已作废；**每次 finish 都会换档，换档后必须整节重新对齐**，⛔ 直接沿用旧锚。

- 门禁汇总（**468 行档实测**）：L23 `G0_RESULT=pass`、L63 `KC_RESULT=pass`、L90 `JC_RESULT=pass`、
  L454 `L0_RESULT=pass: all checks passed`、L455 `L1_RESULT=pass: test_package executed`、
  **L456 `L2_RESULT=pass: lbdb-fetchaddr version/help failed, lbdb_dotlock failed, lbdbq --version OK,
  mutt_ldap_query failed, nodelist2lbdb failed`**、L457 `L4_RESULT=warn: dangerous functions in patches`、
  L458 `L5_RESULT=pass: bin/ has content`、L433 `[ok] lbdb/0.57 — conan create passed`。
  - **L2 结果是 `pass`（第 4 轮 W4 P1 更正，此前本节误写成 `warn`）**：`reports/w3-local-ci.log:456` 实读
    `L2_RESULT=pass`；`L447-456` 是 `[step] L2` + **4 条 `[warn]`（非阻塞）** + `[ok] L2: lbdbq --version OK`（`:450`）。
    harness `ci/conan/build_and_test.sh:1685-1725` **只写 `pass`/`skip`、从不写 `warn`**，棒侧 `digest.txt:67`
    同为 pass ⇒ 「`L2_RESULT=warn`」在任何 lbdb W3 日志里都不存在。
  - **分栏保留**：4 枚 bin（`lbdb-fetchaddr`/`lbdb_dotlock`/`mutt_ldap_query`/`nodelist2lbdb`）不认 GNU 长选项
    ⇒ 4 条 `[warn]` 非阻塞、只有 `lbdbq --version` 返 0；这**不等于解释器缺失**——消费者断言 A3/A4（sh 横幅）
    与 A5/A6（两个 perl 交付脚本 rc=255 / rc=2，均非 127、无 "No such file or directory"）已各自通过，见 L425 前后。
  - **L4 是 warn（真正的 warn）**：点名对象是 L440 列出的 `patches/0001-config-guess-sub-ohos.patch`
    （其正文为 GNU config.guess/config.sub 上游脚本片段，非本包手写 C），假阳性依据见 §13.5。
- 消费者 10 断言逐条落地：L421–L430 `ok 1` … `ok 10`，全部 ok、无 `NOT OK`。
  A9（L429）原文含 `lbdbq: 1 matches joe@example.com` + `m_finger_query: inaccessible or not found`
  （后者是未装 `finger` 模块的 `|| true` 噪音，非失败）。
- 平台读数：L196,197 `checking build/host system type... aarch64-unknown-linux-ohos`、
  L206 `checking for iconv... yes`（⇒ 无 libiconv 依赖）、L173 `Apply patch (portability)`、
  L172,416 `Calling build()`、L330 `Calling package()`、L416 test_package `Calling build()`。
- **站点数算式（可复算）**：A1/A2 = `for t in lbdbq lbdb-fetchaddr` 固定 2 元表 × 1 判定 = 2；
  A3/A4 = 2；A5/A6 = `for perltool in nodelist2lbdb mutt_ldap_query` = 2；
  A7/A8 = 两个独立 `if`（`offenders -eq 0`、`inspected -ge 8`）= 2；A9 = 1；A10 = 1 ⇒ **2+2+2+2+1+1 = 10**。
  `ok()` 与 `bad()` 各且只各 `checks+1`，且处在互斥 `if/else` 两支 ⇒ 每次判定恒 +1；
  A7 前面的 shebang 扫描循环只累加 `inspected`/`offenders`，不产 check ⇒ total 与包内脚本数量无关，恒 10。
- 结果登记件 `.ci-result.json`（由 `finish` 自写、**每次 finish 都会重写**）——
  **仓内不落其字面哈希**：`integrity_hash` 与 `log_sha256` 都含时间戳，写死必过期、也会造成「两套哈希」误判。
  复算式（判据，非字面值）：`integrity_hash = sha256(f"{timestamp}:lbdb:0.57:0")[:16]`、
  `log_sha256 = sha256sum archives/l/lbdb/0.57/reports/w3-local-ci.log`；
  **三个真实读数（timestamp / integrity_hash / log_sha256）以文件实物为准，并在建 PR 时写入 PR 正文**
  ——正文是唯一既能承载最终值、又不移动 HEAD 的位置。
  （各历史档的具体取值见 git 历史，本节不再逐档抄录，⛔ 与现行实物比字面值。）

### 11.4 ★两档 RREV 如实分档

- **交付档（官方址）`lbdb/0.57#75beb304afe7db959b8e31a4810f92a3`**（**现行**）——`reports/conan-create.log:10` 实测 `Exported: lbdb/0.57@ohpcd/stable#75beb304afe7db959b8e31a4810f92a3 (2026-09-28 04:43:59 UTC)`。
  导出集仍是 `conandata.yml` + `conanfile.py` + `0001-config-guess-sub-ohos.patch` 三件（notes / MANIFEST / commands.json / 软件级两枚不进导出集）。
  **翻档根因＝2026-09-28 收尾-7 给 `conandata.yml` 的 `patch_file`/`patch_description`/`patch_type` 三处标量补了双引号**（W4 P2 整改），YAML 语义不变但字节变了 ⇒ 导出哈希变。
  **历史档**：`#5546d0463ecf118ef6daa8a192b92cdf`（2026-09-27 00:15:13 UTC 那次 export，交棒时的登记值），`§9`/`§11.7` 里引用它的地方均已标注日期。
- **W3 绿跑档（注入址）`lbdb/0.57#dcca5f48717a51f05012157ada2001bd`**（**现行**）——`reports/w3-local-ci.log:107` 实测 `Exported: lbdb/0.57#dcca5f48717a51f05012157ada2001bd (2026-09-28 04:45:29 UTC)`，`:153`/`:158` 与 `:392` 分别给出该档的 Cache / Build（PKGID `6b129b06…ce8a`）/ Full package reference。**历史档**：`#5534d6b28442c4a47567a7b5c69d841e`（09-27 那轮，原记于 L109）。
  可观测依据（只给判读法，不作 CI 断言；**锚点按 09-28 17:07 档、全文 468 行实读**——旧锚 L94/L473/L164/L98（473 行）与 L94/L471 等（471 行）均已作废）：`:93` `[step] Pre-download: extracting source URLs from conandata.yml...`、
  `:96` `[done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs`、
  本档**没有 `Sources correctly downloaded` 行**（依赖已缓存 ⇒ `Pre-download` 走 `[cached]` 分支，读日志时按此判读）、
  `:468` `[step] Pre-download: conandata.yml 已还原为官方 URL`（工作树 conandata.yml 已复原，
  `git diff` 中无该文件）。⇒ W3 的绿跑**不代表** CI 会用官方址首次下载；CI 机上 `predl_cache` 为空，
  后续棒请按 `[step] Pre-download` / `[cached]` / `[WARN] ... will rely on conan's download` 三类行判读。
- PKGID 两档同为 `6b129b068851896169fae42d399fa922d239ce8a`（现件 `w3-local-ci.log:158` 实读；`Full package reference`/`Package folder` 在 `:389`/`:390`）。
  **PREV 含 `--prefix` 绝对路径、属机器/目录绑定读数，换 CONAN_HOME 即变 ⇒ ⛔ 不作跨机一致性判据**；
  现行档取值见 `w3-local-ci.log:389` 的 `Full package reference` 末段，**旧档字面值（`34e139de…`/`c07a8ae8…`）已从本节撤掉**
  ——旧锚 `L394`（473 行档）与 `:392`（471 行档）均已作废，**现件 468 行档实读 `:389`**；具体数字以文件实物为准，见 §11.7 的同口径结论。
- 缓存内另有 `lbdb/0.57#518a9ac18bf572f223b7e714a3bbdf00 (2026-09-26 23:45:13 UTC)`，
  时间早于本棒且归属未核，不作为本棒证据。

### 11.5 finish 未绿步骤与遗留（如实登记）

- Step1 refresh-patch：`无法定位源码目录: orig=None, work=None` —— 构建发生在 conan 缓存内，
  本地无 orig/work 目录，符合预期；该步未落任何写入（`git diff` 可证）。
- Step2.5 G0 clean-verify：`找不到原始 tarball`，非阻塞。
- Step6 finalize-archive：`软件级缺失: README.md`（本棒已补，见 11.6）、`目录缺失: packaging`、
  `缺少 release tar.gz`、`缺少 debug tar.gz`、`状态不一致: notes=error: could not setup config files
  machinery vs manifest=built` —— 该告警是 finalize 的关键词扫描命中 §7 记录的**历史报错原文**
  （G2 与 W3 两次 create 实际 rc=0，`.ci-result.json exit_code=0`），非真实状态冲突；另 `notes.md 无对话记录`。
- Step7 check-knowledge-gap：`manifest.yaml: knowledge_count=3 unreferenced=3` ⇒ 检查器只认列表项内
  带 `ref:` / `knowledge_ref` 的写法（`scripts/ohc/check_knowledge_gap.py:52-66`），本棒已按该格式
  补齐三条 ref，并把 §12 的知识小节写成 ✅ bullet（同文件 28-41 行的抽取规则）。
  `E219/E253/E305 root_cause 为空` 与 1396 个待审草稿是仓库既有状态，不属本包。
- Step8 gen_summary：`gen_summary 失败: 'str' object has no attribute 'append'` —— 框架侧异常，
  本包无改动，交主窗。
- Step10 submit 就绪预检：`reports/test-report.md`、`packaging/`、`.staging-verified` 三项未做
  —— 不在本棒范围（本棒不建 PR、不做 submit）。
- 落完本节后重跑 `ohc-run.py close-archive lbdb 0.57 built` 刷新标记：manifest `status: built`、
  `.build-closed` 与 notes 末尾 `编译结束/最终状态` 块（未重跑整条 finish，W3 日志与行号锚保持不变）。

### 11.6 声明面（R38/L0k）与软件级两枚

- `archives/l/lbdb/commands.json`：仓库 schema（`templates/commands.json.template`，先例 `archives/l/a52dec`）
  无逐命令数组，声明面落在 `description` 内；本棒按已交付包实物逐枚列举：bin 5 + libexec 18 = 23 枚，
  含 11 个 `m_*` 模块。`binary` 保持 `false`（适配中未发布制品到仓库）。
- 双向集合差：包内 `bin`+`libexec` 23 枚全部出现在 description 中（正向差集为空）；
  反向唯一多出的候选名 `lbdb_get_matches` **实测不存在**——`grep -rn lbdb_get_matches` 在
  0.57 上游解包树（`~/tmp/uc2/z74-lbdb/src/lbdb-0.57`）与已交付包目录内命中均为 0，
  故判定其不属 0.57 命令面、不予声明。
- 软件级两枚：开跑前 `archives/l/lbdb/README.md` 与 `archives/l/lbdb/manifest.yaml` 均 MISSING
  （finalize 亦报 `软件级缺失: README.md`），已按 `archives/l/lddtree/` 先例形状补齐，内容只写盘上有依据的事实。


### 11.7 收尾-2 复核（2026-09-27 22:25–22:37，B 机，HEAD `78ea5914d6`）

- **环境**：worktree `~/qzy/主理-74-lbdb-0.57`；CONAN_HOME 换用本窗独占 `~/tmp/ch/home-qw2-lbdb`
  （由 `home-lbdb` 整体克隆、含 `extensions/`）。git 署名当场重钉为 `收尾-2`。
- **`preflight_check.sh lbdb/0.57` RC=0**（无外部依赖，与 §3 一致）；**`ohc-run.py recipe-search lbdb`** →
  top1 `lbdb/0.57 [autotools] score=0.5`（本包已在检索语料内）。
- **★conan-verify 第一跑是"假绿"，本轮抓到并纠正**：克隆来的 CONAN_HOME 已含缓存包，`--build=missing` 直接复用，
  `reports/conan-create.log` 里**没有** `Calling build()`/`Calling package()`，只有 test_package 10/10——
  而 `**Verdict**: PASS` 与 rc=0 两条件当时都成立 ⇒ **门禁事实卡 §2 的"缓存假成功"在 verify 上同样成立，
  判绿必须再核 create 日志真编译过**。`conan remove "lbdb/0.57@ohpcd/stable" -c` 后重跑才是真 create——
  `Calling build()`(L98)、5 枚 clang 编译行、`Calling package()`(L256)、`Package '6b129b06…ce8a' created`(L314)、
  A1–A10 全 ok + `SUMMARY lbdb consumer: total=10 passed=10 failed=0`(L347–357)、`**Verdict**: PASS`、`VERIFY_RC=0`
  （三一致 + 真编译）。证据 `~/tmp/uc2/qw2-lbdb/verify-run1.log`（假绿）、`verify-run2.log`（真绿）、
  `reports/conan-create.log`(23296 B) 与 `reports/conan-verify-report.md`（mtime 22:34，晚于本轮起点 22:31）。
- **RREV（09-27 22:31–22:37 那一轮）**：当时三度同 `5546d0463ecf118ef6daa8a192b92cdf`（首棒交付档 / 取证棒 `conan export` 复算 / 该轮 create）；**2026-09-28 收尾-7 给 `conandata.yml` 补标量引号后已翻档为 `75beb304afe7db959b8e31a4810f92a3`**（见 §11.4 与 `reports/conan-create.log:10`）。
  PKGID 全程同 `6b129b068851896169fae42d399fa922d239ce8a`（未变）。**PREV 换 CONAN_HOME 即变**（本轮
  `f853545ea2942c7b6fd19ce5913cf547`，旧档 `fe8ca3de…`/`34e139de…`）——PREV 含 `--prefix` 绝对路径、属机器/目录绑定读数，
  ⛔ 拿它当跨机一致性判据（§11.4 的两档口径仅对 RREV/PKGID 成立）。
- **`ohc-run.py finish lbdb 0.57 built` → RC=1（不是 9/9）**，逐步读数（`~/tmp/uc2/qw2-lbdb/finish-run1.log` 128 行）——
  [1/10] refresh-patch 跳过（构建在 conan 缓存内无 orig/work 目录）｜[2/10] close-archive ✅｜
  [3/10] G0 clean-verify ❌ `找不到原始 tarball`（非阻塞，同 §11.5）｜[4/10] conan-verify ✅｜
  **[5/10] W2 结构 + R36 依赖 + W3 本地 CI ✅✅（唯一的阻塞步通过）**，`.ci-result.json` 按**当轮** HEAD
  （2026-09-27 22:37 那一轮）重生成、`exit_code=0`；**字面哈希不在仓内抄录**（含时间戳、每轮必变），
  判据见 §11.3 的复算式，取值以文件实物为准｜
  [6/10] finalize-archive ⚠ RC=2（`packaging/` 缺、release/debug tar.gz 缺、`notes.md 无对话记录`）｜
  [7/10] check-knowledge-gap ❌ 1 类（`doc↔kv 540 对 ✅` 但 E219/E253/E305 `root_cause` 为空——仓库既有状态，非本包）｜
  [8/10] gen_summary ❌ `'str' object has no attribute 'append'`（框架缺陷，按事实卡 §4 只记录不绕行、不改共享框架）｜
  [9/10] PR 原子性 ✅ `仅含配方变更 (11 文件)`，无框架文件混入｜[10/10] submit 就绪预检 ⚠ 3 项未创建。
  摘要行印 `失败步骤: step5b, step8`、HANDOFF 尾巴印 `STEP_FAILED: Step6`——两处措辞不一致属框架侧，本包无改动。
- **[10/10] 三项的定性**：全仓 7753 个版本目录里 `packaging/` 仅 372、`reports/test-report.md` 仅 450、
  `.staging-verified` 仅 2 枚被跟踪 ⇒ 非建 PR 硬前置；建 PR 的硬闸是 create-pr 的 PF1–PF9 + R52（SKILL §3 Step 4-5）。
  本包逐项自查——PF1 单包（`git diff --name-only origin/main...HEAD` 只 11 枚 `archives/l/lbdb/**`）✅｜
  PF2 无制品 ✅｜PF3 `test()` 有 `self.run` ✅｜PF4 无 requires ✅｜PF5 补丁新增行含 `__OHOS__`
  （`patches/0001` 的 config.guess 分支，全仓 663 枚补丁同形态先例）⇒ R8 例外理由**已落笔**，见 §15｜
  PF6 配方/conandata 内无引号包裹的 `/usr/local` 字面量（仅上游源文件与生成的 env 脚本里有，非注入项）✅｜
  PF7 源址 `https://www.spinnaker.de/lbdb/download/lbdb-0.57.tar.gz` 官方 https、无池址无镜像 ✅｜
  PF8 `commands.json` `name=lbdb` / `type=tool` / `versions."0.57".ref=lbdb/0.57` 对齐 ✅｜
  PF9 分支 `feat/lbdb-0.57` 且变更全落 `archives/l/lbdb/0.57` + 软件级目录 ✅。
- **finish 静默改写横扫**：本轮 finish 对 `archives/l/lbdb` 的唯一改动是把 §12 之后的
  "编译结束/最终状态"页脚搬到文件末尾（`git diff` 可证），`git status` 未出现越界改动；
  **libXext 两枚 `M` 是他窗资产，本窗未碰、不提交**。CRLF 横扫——`archives/l/lbdb` 全部 11 枚跟踪文件
  `grep -c $'\r'` = **0**（含 notes.md 与两份新草稿）。
- **本轮对 notes.md 的三处订正**（都是"结论被自己的实测推翻"类，不是排版）——§5 把"双保险"改成按 config.log
  分色的实效账（AWK 实测没钉住）；§8 删去"上游测试环境性不可执行/缺 perl"的旧判语并指向 §13 的实跑五维账；
  §9 删去"conan-verify/W3/.ci-result 未跑"。

## 12. 发现与知识

- ✅ **E007**（config.guess 不识别 HarmonyOS）：GNU config.guess 2024-07-27 在 `uname -s`=HarmonyOS 上 rc=1；处方是把 config.guess/config.sub 重锚为 `aarch64-unknown-linux-ohos` 的自包含补丁 `patches/0001`，**禁止用 `--build/--host` 绕**（会误判交叉编译、跳过 `AC_RUN_IFELSE`/`AC_PATH_PROG` 而生成错 `config.h`）。本窗新证据：W3 与 verify 两次 create 均打出 `checking build/host system type... aarch64-unknown-linux-ohos`（w3 日志 build/host 两行），补丁经 `Apply patch (portability)` 正常应用。
- ✅ **E049**（autoconf `@SH@/@PERL@/@AWK@` 模板烧进构建机解释器路径）：本平台无 `/usr/bin/perl`、无 `/bin/bash`，perl 只在 `/data/service/hnp/bin/perl`。处方是 configure 钉 `SH=/bin/sh AWK=/bin/awk` + `package()` 按 basename 归一 shebang。本窗新证据：W3 内 A7/A8 断言 `scanned 20 installed scripts` 且 offenders=0，A5/A6 两个 perl 交付脚本 rc=255 / rc=2（非 127、无 No such file or directory），`L2_RESULT=pass`（`:459`；其上 `L450-459` 是 4 条非阻塞 `[warn]` + `[ok] lbdbq`）只反映 CI 用 `--version` 探测的口径而非解释器缺失。
- ✅ **E160**（cannot guess build type 且禁用交叉参数绕过）：与 E007 同源的表现型条目，本包由 `patches/0001` 解决，未使用任何 `--build/--host`；`conanfile.validate()` 只放开 `os in (Linux, OHOS)` 且 OHOS 限 `arch=armv8`。
- 🆕 **新增草稿 `DRAFT-lbdb-0.57-autoconf-var-shebang-configure-pin`**（`.kv` + `.md` 成对，随本 PR 的 `knowledge/drafts/`）——
  机制：**autoconf `#! @VAR@` 模板被 configure 用构建机探测路径填实**，并给出"哪些 VAR 钉得住"的判据
  （上游有没有 `if test "x$VAR" = x` 守卫）、"configure 传参是选做、交付期 basename 归一才是主案"的主次关系、
  以及"全量 shebang 扫描 + 扫描数 > 0"的验收断言形状。查重与一手证据见该草稿 `.md` 的"查重账"
  （`@SH@`/`@PERL@`/`@AWK@`、`SH=/bin`、`AWK=/bin`、`offender`、`机器绑定` 在 `knowledge/` 命中均 0；
  最接近的 E049/E037/date/libgctp/ac-cv-path-override 五条逐条给边界）。
  `ohc-run.py draft-review DRAFT-lbdb-0.57-autoconf-var-shebang-configure-pin` 预检
  `signature=✅ root_cause=✅ rec=✅`，TOP5 相似度最高仅 0.12（E052），预审建议 **create**。

## 13. 上游 autotest 20 用例真机实跑（实跑-lbdb，2026-09-27，B 机）

- 上游测试用例通过率：12/20（60%）——20 例全部实跑：执行 14、通过 12、跳过 6（缺 abook/mu/notmuch）、失败 2（lbdb-fetchmail / m_inmail，根因 HMDFS 无 link(2)，见 §13）

结论：**上一棒「上游 20 用例在本平台给不出有意义判定」的说法是错的**。20 例全部被驱动，
判决可复现，五维账本见 13.2（行号由脚本从入库日志里现算，非手填）。

### 13.1 驱动方式（一手读码 + 一手试跑）

- 注册面：`tests/Makefile.in:21-22` `TESTSUITE_AT = m_muttalias.at m_abook.at m_inmail.at
  m_vcf.at m_mu.at m_notmuch_addrlookup.at`；`tests/Makefile.in:38`
  `check-local: atconfig atlocal $(TESTSUITE)` → 规则体
  `$(SHELL) $(TESTSUITE) AUTOTEST_PATH=$(abs_top_srcdir) USE_LOCAL_LIB=$(abs_top_srcdir)`；
  `configure.ac:238` `AC_CONFIG_TESTDIR([tests])`。`testsuite.at` 用 6 条 `m4_include`
  把用例并进**随包发出**的 `tests/testsuite`（3391 行），不需 autom4te 再生。
- **可用命令只有 `make -C tests check-local`**：顶层与 tests/ 都没有 `check` 目标，
  `make -j1 check` 实测 rc=2、`make: *** No rule to make target 'check'. Stop.`。
  ⇒ 此前 MANIFEST.yml 里的 `make -C tests check` 是跑不通的命令，已订正。
- `AUTOTEST_PATH`/`USE_LOCAL_LIB` 指向本地构建产物，不需先 install；本包是 in-tree 构建
  （`srcdir=.`，`tests/atconfig` 的 `abs_top_srcdir` 就是构建树本身）⇒ **在 conan 构建目录
  原地可跑，无需额外喂环境**（除把 `/data/service/hnp/bin` 等解释器目录带上 PATH）。

### 13.2 五维账本（静态总数 / 可执行 / 实测通过 / 跳过 / 失败）

| 维度 | 数 | 来源 |
|---|---|---|
| 静态总数 | 20 | `grep -c AT_SETUP tests/*.at` 逐档 1/8/4/1/1/5+0=20；注册面见 13.1 |
| 实际执行 | 14 | `reports/upstream-make-check.log:50`「ERROR: 14 tests were run,」 |
| 实测通过 | 12 | 同文件 :10,20-25,29-33 |
| 跳过 | 6 | 同文件 :14,37-40,44 |
| 失败 | 2 | 同文件 :18-19；汇总 :50+1/:50+2 |

逐套：m_muttalias 1/1、m_abook 1 skip、m_inmail 8（6 ok + 2 FAILED）、m_vcf 5/5、
m_mu 4 skip、m_notmuch_addrlookup 1 skip。三份日志原样入库：
`reports/upstream-make-check.log`（判决面）、`reports/upstream-testsuite.log`
（autotest 详节 758 行：Failed tests 摘要 :132、Skipped tests 摘要 :141、
首条失败详节自 :159、两条 `exit code was 1, expected 0` 在 :176 与 :185）、
`reports/upstream-skips-only.log`。

6 例 skip 的具体原因（不是「没环境」一句话）：
`AT_SKIP_IF([! which abook])`（m_abook.at:20）、`AT_SKIP_IF([! which mu])`
（m_mu.at:19/35/61/87）、`AT_SKIP_IF([! which notmuch-addrlookup])`＋`:20 [! which notmuch]`
（m_notmuch_addrlookup.at:19-20）；本机 `command -v abook/mu/notmuch/notmuch-addrlookup`
四枚全 MISSING，属真实外部程序缺失。`tests/gen-maildir` 的 shebang 确实写死
`#!/usr/bin/perl`（本平台无此路径，perl 在 `/data/service/hnp/bin/perl`），但它只被
m_mu.at 与 m_notmuch_addrlookup.at 使用，这 6 例已先因缺程序 skip ⇒ gen-maildir
没有额外扣掉任何用例，12 例通过用例都不依赖它。

### 13.3 2 例 FAILED 的第一条真实错误与根因链（一手复现）

失败形态：`./m_inmail.at:21: exit code was 1, expected 0`（testsuite.log:176）与
`./m_inmail.at:30: exit code was 1, expected 0`（:185）——库文件内容其实**写对了**，
挂的是进程退出码。脱离 autotest 用 `sh -x <build>/lbdb-fetchaddr -f m_inmail.utf8 -d "NO DATE"
< testmail1` 单步复现：trace 末条是 `$dotlock -u m_inmail.utf8` 返 1，而 `lbdb-fetchaddr`
脚本（`lbdb-fetchaddr.sh.in` 主流程）最后一条命令就是它 ⇒ 其退出码成为整条命令的退出码。
往下钻：

1. `lbdb_dotlock -r 10 -f f1` 返 0，但 **`f1.lock` 从未被创建**（`od -c f1.lock`
   → No such file）。同目录 `ln a b` → rc=1，
   `ln: cannot create hard link from 'a' to 'b': Operation not permitted`
   ⇒ **HMDFS 不支持 link(2)（EPERM）**。
2. `dotlock.c` 的 `link (nfslockfile, lockfile)` **返回值不检查**；随后
   `stat (nfslockfile).st_nlink` 恒为 1（≠2）⇒ 重试计数涨过 Retry=10，
   `DL_FL_FORCE` 分支去 `unlink (lockfile)`（文件本就不存在）后继续循环；耗尽
   HARDMAXATTEMPTS 后 `unlink (nfslockfile); return DL_EX_OK`——**dotlock_lock() 把
   「从未拿到锁」当成功返回 0**。
3. 于是 `lbdb-fetchaddr` 照常 `touch $db.dirty`，最后 `$dotlock -u "$db"` 走
   `dotlock_unlock()`：`i = unlink (lockfile)` → ENOENT，`if (i == -1) return DL_EX_ERROR`
   ⇒ 返 1 ⇒ 整条命令 rc=1 ⇒ 用例 3、4 FAIL。用例 5-10 只做只读查询、不经加锁路径，故 ok。

定性：**平台能力缺失（HMDFS 无硬链接），不是配方没喂环境**——PATH / LD_LIBRARY_PATH /
生成物路径都不是原因（同一命令在只读路径上全绿，且 link() 的 EPERM 是在同一目录里直接测出）。

后果与边界（不得写成「只是测试跑不过」）：`lbdb-fetchaddr` 在 HarmonyOS PC 上
**每次调用都返回非 0**，MUA 钩子（mutt 的 `pipe_message`/`sendmail` 式接法）会把
「写库成功」当成失败。消费者 10 例全绿是因为 A9 只比库文件内容、不看退出码
⇒ 两套测试互补，不能互相替代。

能否接进 `build()` 当红门：实测**只跑 6 例 skip 时 testsuite rc=0**
（`reports/upstream-skips-only.log`，末行「6 tests were skipped.」）
⇒ autotest 不把 skip 判失败。所以只要给 `dotlock.c` 加一条无硬链接回退
（`link()` 失败时改 `rename (nfslockfile, lockfile)`，或直接用
`O_WRONLY|O_CREAT|O_EXCL` 建 `<db>.lock`），`make -C tests check-local` 就能变成
14/14 通过 + 6 skip 的**绿色硬门**。**本棒未自行加这个源码补丁**：
它会改动交付二进制、翻 RREV，属交付面决策 ⇒ 交主窗裁决（证据、行号、可绿判定已给全）。
本轮因此**未改 conanfile.py / conandata.yml / patches/**。

### 13.4 L2 的 4 条 warn + 1 条 ok（原文、逐枚定性与处置；末行 `L2_RESULT=pass`）

原文（`reports/w3-local-ci.log:447-456`，468 行档）：
```
[step] L2: Smoke test (version/help check)...
[warn] L2: lbdb-fetchaddr --version/--help failed (non-blocking)
[warn] L2: lbdb_dotlock --version/--help failed (non-blocking)
[ok] L2: lbdbq --version OK
[warn] L2: mutt_ldap_query --version/--help failed (non-blocking)
[warn] L2: nodelist2lbdb --version/--help failed (non-blocking)
L2_RESULT=pass: lbdb-fetchaddr version/help failed, lbdb_dotlock failed, lbdbq --version OK, mutt_ldap_query failed, nodelist2lbdb failed
```
「5 枚 bin 里只有 lbdbq --version 返 0」**不等于其它 4 枚是坏的**。对**已打包交付件**
（`.../p/bin/`，不是构建树）逐枚实测，四个互不相同的原因：

| bin | `--version` rc | stderr 首行 | 定性 |
|---|---|---|---|
| lbdbq | 0 | `lbdbq version 0.57` | 上游实现了长选项 |
| lbdb-fetchaddr | 1 | `mkdir: '/storage/Users/currentUser/.local/share/lbdb': Permission denied` + `Can't create ...` | 脚本只实现短选项：`-v` 实测 rc=0、`-h` 实测 rc=0（打自己的 Usage）；`--version` 不被识别后落到默认 DB 分支，要建 `~/.local/share/lbdb`，而本机 `~/.local/share` 是 `drwx--S---`、当前 uid 写不进去（自造 `z9probe` 同样 EACCES）⇒ **上游不认长选项 + HOME 权限面**，不是解释器缺失 |
| lbdb_dotlock | 1 | `unrecognized option: -` + 上游 usage | getopt 串是 `"dtfur:"`，本无 `--version`；打自己的 usage ⇒ 上游 CLI 面，非缺陷 |
| mutt_ldap_query | 2 | `Can't locate Net/LDAP.pm in @INC ... line 22.` | **perl 缺 Net::LDAP 模块**（`perl -MNet::LDAP -e 1` 同错；`/data/service/hnp/perl.org/perl_5.42.0` 的 @INC 里没有 LDAP.pm）⇒ 该命令在本机**功能不可用**，是未声明的运行时依赖缺口（全树只有 mutt_ldap_query.pl 一处 `use Net::LDAP`），必须进正文披露 |
| nodelist2lbdb | 255 | `Usage: ... nodelist.XXX [points24.YYY]` | 自己的 usage + 非 0 退出，本无 `--version` |

处置：L2 的探测口径＝「每枚 bin 都该支持 GNU `--version`/`--help`」，上游 5 枚只有 2 枚
部分实现 ⇒ warn 属 **harness 口径问题，不改交付件、不算阻塞**。但两条真实能力面
（`~/.local/share` 不可写、`mutt_ldap_query` 缺 Net::LDAP）加上 13.3 的退出码缺陷
**必须进 PR 正文披露**。禁止再保留「只有 lbdbq --version 返 0」这类不解释的裸陈述。

### 13.5 L4 warn（点名 0001 补丁）的原文、定性与处置

原文（`reports/w3-local-ci.log:438-440` 与 `:457`，468 行档）：
```
[step] L4: Scanning patches for dangerous functions...
[warn] L4: Dangerous functions found in patches:
.../archives/l/lbdb/0.57/patches/0001-config-guess-sub-ohos.patch
L4_RESULT=warn: dangerous functions in patches
```
扫描器在 `ci/conan/build_and_test.sh:1469`：
`DANGER=$(grep -rlE '(strcpy|sprintf|gets|strcat)\b' "$PATCH_DIR" ...)`。
对 0001 跑同一条正则，**唯一命中是补丁第 28 行**：
` 	# NetBSD (nbsd) targets should (where applicable) match one or`
——它是 config.guess 的**上下文行（本补丁未改动的上游注释）**，命中的是
「tar**gets**」里的 `gets` 子串：正则只有右边界 `\b`、**没有左边界**。
⇒ 定性：**harness 正则假阳性**；0001 只替换 config.guess/config.sub 的 OHOS 三元组表，
新增行里没有任何 strcpy/sprintf/gets/strcat 调用，不是交付缺陷。
处置：不改补丁（那是动上游归档内容）、不改扫描器（框架件，本棒无权限），但在正文/notes
主动写清命中行与假阳性依据——**CI 静态审查若用同一条无左边界正则，这条 warn 会再现**，
先把依据备好，免得被判「补丁含危险函数」。

### 13.6 本轮改动边界与 RREV/PKGID

- 只动：`notes.md`（§13 + 通过率行）、`test_package/MANIFEST.yml`、`manifest.yaml`，
  新增 `reports/upstream-make-check.log`、`reports/upstream-testsuite.log`、
  `reports/upstream-skips-only.log`。
- **本节原写的「未动 conandata.yml ⇒ RREV 不变 / 本轮没翻档 / W3 与 `.ci-result.json` 未重生成」三句已被**本分支自己的后续提交推翻，作废**（第 3 轮 W4 P1）**：2026-09-28 收尾-7 的 P2 整改给 `conandata.yml` 三处标量补了双引号，而 conandata 在导出集内 ⇒ 交付档翻档为 `75beb304afe7db959b8e31a4810f92a3`，W3 也于 12:47 重跑并重写 `.ci-result.json`。**现行实测**：交付档 RREV `75beb304afe7db959b8e31a4810f92a3`（`reports/conan-create.log:10`）、W3 注入档 `dcca5f48717a51f05012157ada2001bd`（`reports/w3-local-ci.log:107`）、PKGID `6b129b068851896169fae42d399fa922d239ce8a`（两档同值、未变）。
- **本节当轮改动**：`notes.md`（§13 + 通过率行）、`test_package/MANIFEST.yml`、`manifest.yaml`，新增 `reports/upstream-make-check.log`、`reports/upstream-testsuite.log`、`reports/upstream-skips-only.log`；其后另有 `conandata.yml`（标量引号）、`test_package/test_lbdb.sh`（`set -euo pipefail`）、`notes.md` §15（R8 例外）三处（09-28 收尾-7）。
- **教训（W4 第 3 轮 P1 一句话）**：**「我没改它」不是证据，「diff 里没有它」才是**——给 YAML 补引号也属于改，会翻导出哈希；申报前必须 `git log -p -- <导出集文件>` 与 `reports/*.log` 实读对账。
- 两套数字分开、互不混算：
  `SUMMARY lbdb upstream autotest: total=20 ran=14 passed=12 skipped=6 failed=2`
  `SUMMARY lbdb consumer: total=10 passed=10 failed=0`

### 13.7 复现命令（主窗/审计棒照跑即可）

```
export CONAN_HOME=$HOME/tmp/ch/home-lbdb
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:/data/service/hnp/bin:$PATH
cd <conan 构建目录>            # in-tree：srcdir=.
make -C tests check-local      # rc!=0 当且仅当有非 skip 失败
/bin/sh ./testsuite AUTOTEST_PATH=$PWD/.. USE_LOCAL_LIB=$PWD/.. 2 16 17 18 19 20   # 只跑 skip 集，rc=0
ln a b                         # 验证 HMDFS 无 hardlink：Operation not permitted
```
### 13.8 上游判决日志随 PR 入库（收尾-2 纠偏，2026-09-27 22:56，B 机）

- §13.2 的行号引用与 `manifest.yaml` 的 `evidence_logs:` 都指向 `reports/upstream-*.log`，但 `reports/` 在全局
  `.gitignore` 内 ⇒ 上一笔提交 `78ea5914d6`（标题写"上游测试证据日志入库"）**实际只改了 notes.md 五行、日志并没进仓**
  （`git show --stat 78ea5914d6` 只有 `notes.md | 5 +++--`，`git check-ignore -v` 指向 `.gitignore:96 reports/`）——
  评审按正文路径取不到证据，属 rule4 同源缺口。
- 仓库先例——`archives/*/reports/*.log` 已有 **75 枚被跟踪**（本窗 `git ls-files "archives/*/reports/*.log" | wc -l`
  实测；如 `archives/b/bctoolbox/5.3.115/reports/upstream-test-full-feature.log`、
  `archives/a/abook/0.6.1/reports/conan-create.log`；上一版记的 72 系 09-27 的旧计数，按第 2 轮审计更正）
  ⇒ "证据日志随包入库"是既定做法，本窗把 §13 引用的三枚判决面日志用 `git add -f` 精确补进本分支——
  `upstream-make-check.log`(2480 B)、`upstream-testsuite.log`(28743 B)、`upstream-skips-only.log`(711 B)。
- **适用边界（第 2 轮审计 P3）**：只入**判决面**日志，不入每次 verify/finish 重生成的件；本包这 3 枚正是
  §13.2 行号引用的原件。若审查按字面口径认为 `.log` 不应随 PR，处置＝把这 3 枚移出并**同步改
  `manifest.yaml` 的 `evidence_logs` 与 §13.2 行号引用**（改指 notes 摘录），届时按该口径执行——PR 正文
  已把这条边界写出来。
- **入库件就是 §13.2 引用的那一份**（不是重跑件）——头部两行原样为
  `make: Entering directory .../home-lbdb/p/b/lbdb6dbfa375d0858/b/tests'` 与
  `/bin/sh ./testsuite AUTOTEST_PATH=... USE_LOCAL_LIB=...` ⇒ **确系 conan 交付形态（构建目录内）实跑**；
  尾部判决 `ERROR: 14 tests were run,` / `2 failed unexpectedly.` / `6 tests were skipped.`（14 执行 − 2 失败 = 12 通过，
  14 + 6 skip = 20 总数，与 §13.2 五维账本逐项对得上）。
- ⛔ 未入库 `conan-create.log` / `w3-local-ci.log` / `conan-verify-report.md` / `.ci-result.json`——
  它们每次 verify/finish 都重生成（`.gitignore` 亦注明"质量报告（每次重新生成）"），绝对读数已原样抄进
  §11.1–§11.4 与 §11.7 供复核。
- 棒侧目录 `~/tmp/uc2/z74-lbdb-tests/` 里的 `03-make-check.log` 只有 49 B，内容是
  `make: *** No rule to make target 'check'.  Stop.`——那是**已废弃的 `make check` 尝试**（§13.1 已记：顶层与
  tests/ 都没有 `check` 目标），判决面全文只在上面三枚入库件里；两者不是同一份东西，⛔ 拿 03 号文件当判决证据。

## 14. 路径 B 声明（3+2，B判定=create，2026-09-28 整改棒补）

- 适配路径：路径 A（基础适配）+ 路径 B（知识库扩展；B判定=create，检索账与 draft-review 见 §12）
- 使用知识库：知识图谱既有机制 E007（config.guess/config.sub 重锚 aarch64-unknown-linux-ohos，同 jigit 1.22 先例）、E129（autoconf 2.72 config.status 的 mktemp scratch 目录在 HMDFS 被拒建 → 配方改 plain mkdir）、E049（shebang 归一家族）；verify G0 命中 E490（autotools 脚本权限）
- 知识库扩展：knowledge/drafts/DRAFT-lbdb-0.57-autoconf-var-shebang-configure-pin.{kv,md}（同 stem 成对随本 PR 入库；@VAR@ shebang 模板的可钉性判据与交付期 basename 归一主案）
- 关联 Issue：#3526（知识库扩展 Issue：【知识库扩展】lbdb 0.57：@VAR@ shebang 模板的可钉性判据与交付期 basename 归一主案）

## 15. R8 平台宏例外理由（`patches/0001` 新增 `__OHOS__` 的四点说明，2026-09-28 收尾-7 补）

W4 独立审计（2026-09-28）对本包判出的唯一 P1 = R8：`patches/0001-config-guess-sub-ohos.patch:7` 的新增行
`+#elif defined(__OHOS__)`（及其下一行 `+    LIBC=ohos`）属"补丁引入平台宏"，而 R8 要求**例外须在 PR 中说明理由**。
本节即该理由（PR 正文同步收录同一段）：

1. **无 POSIX 等价物**：该行位于 `config.guess` 的 libc 识别探针内——先 `cat <<-EOF > "$dummy.c"` 写出
   `#if defined(__ANDROID__)` / `#elif defined(__GLIBC__)` / … 的判别式，再交给 `$CC_FOR_BUILD -E` 预处理取
   `LIBC=` 的值。判据是**编译器预定义宏**，shell 侧没有任何可移植写法能拿到同一判据（`uname -s` 拿不到 libc，
   `ldd --version` 在本平台不可用）。这正是 iron-rules R8 与 `.gitcode/review-memory.md` 第 5 条点名的
   "**识别 libc 的探针程序**"例外场景。
2. **追加分支是实质逻辑、对非鸿蒙平台完全透明；但本机不走这条分支（如实记，⛔ 不把它当生效兜底）**：
   按 iron-rules R8「四不」表给出的正确做法——用 `#elif defined(__OHOS__)` **追加**新分支。diff 仅 +2 行，
   `#elif defined(__ANDROID__)`、`#else` 及其下 `__UCLIBC__ / __dietlibc__ / __GLIBC__ / __LLVM_LIBC__ / musl`
   全部既有分支一字未动，其它平台取值与上游逐字相同（R8 的核心要求"修改对非鸿蒙平台透明"）。
   **第 2 轮审计 P3 要求补的两点如实披露**：
   (i) 本机 `uname -s` = `HarmonyOS` ⇒ 该 libc 探针段整体位于 `case $UNAME_SYSTEM in Linux|GNU|GNU/*)` 之内
       **本机不执行**；真正给出 triplet 的是同一补丁新增的 `*:HarmonyOS:*:*` 分支——
       `config.log:160` 实测 `checking build system type... aarch64-unknown-linux-ohos`（本窗复核同值）。
   (ii) 新增的 `+    LIBC=ohos` 是 **4 空格缩进**，而该 heredoc 为 `cat <<-EOF`（`<<-` **只剥离 TAB、不剥空格**），
       下游取值又是 `grep '^LIBC'`（**行首锚定**）+ `sed 's, ,,g'` ⇒ 即使在"uname 报 Linux 且编译器已定义
       `__OHOS__`"的同族机器上，**这一行也取不到值**。故本补丁在本包真正生效的是 `*:HarmonyOS:*:*` 与
       `config.sub` 的 `ohos-linux` 别名两处；该 2 行宏改动按"例外须说明"留痕，**不宣称它是生效兜底**。
   同一补丁另两处改动**不含平台宏**：`config.guess` 新增 `*:HarmonyOS:*:*` 分支输出
   `${MACHINE}-unknown-linux-ohos`、`config.sub` 新增 `ohos-linux` 别名。
3. **同形态先例**：本仓 `archives/*/*/patches/*.patch`（`git ls-files` 计 13120 枚）中"新增行含 `__OHOS__`"
   的实测 **663 枚**（本窗 `grep -rl "^+.*__OHOS__" archives --include="*.patch" | wc -l`，与审计员复核值一致）；
   逐字同形先例见 `archives/a/advancescan/1.18/patches/0004-config.guess.patch:206`。
4. **门禁处置留痕**：PF5 对该形态 fail-closed。按 iron-rules R8 的工具化条款"例外场景需 PR 说明理由后
   `--no-preflight` 显式跳过（留痕可审计）"——本 PR 经 `$P run` 的 GitCode API 通道创建，该通道不执行
   PF1–PF9（等价于已跳过），**本节即该留痕**；若改经 `scripts/gitcode_pr.py create-pr` 通道重建，必须显式带
   `--no-preflight` 并保留本节。

附（一手读数：说明该 libc 探针分支在本机不生效、属兜底路径）：本机 `uname -s` = `HarmonyOS`，该探针段整体位于
`case $UNAME_SYSTEM in Linux|GNU|GNU/*)` 之内 ⇒ 本机不执行；实际 triplet 由同补丁新增的 `*:HarmonyOS:*:*` 分支
给出——`config.log:160` 实测 `checking build system type... aarch64-unknown-linux-ohos`。
---

**编译结束**: 2026-09-28 17:04
**最终状态**: built
