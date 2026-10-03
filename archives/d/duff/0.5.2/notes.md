# duff 0.5.2 适配笔记（上游 0.5.2；OHOS / HarmonyOS PC aarch64）

> **版本策略（R37）**：上游 tag 为 `0.5.2`（源码 URL/sha256 不变）；包版本 `duff/0.5.2`，即**首次适配**版本号（不加修订后缀）。
> 本文 §4–§8 的逐步记录录制于同一套配方的施工过程，配方内容与最终交付完全一致（仅包版本号 / 归档目录名不同）。
> §8.1 为本次 `duff/0.5.2` 交付的复核复跑证据链。

- 目标库：**duff 0.5.2**（上游版本 = 包版本 **`duff/0.5.2`**）（重复文件查找 CLI，C + Autotools）
- 上游：源码仓库 https://github.com/elmindreda/duff （作者 Camilla Berglund）
  官方项目页/发布：http://duff.sourceforge.net/ （SourceForge）
- 适配日期：2026-09-30（首次施工记录 2026-09-27）
- 构建系统：Autotools（configure.ac + Makefile.am + po/），无 libtool
- 语言预检：`lang-preflight` → detected=c（任务语言 cpp，C/C++ 兼容族，继续）
- 归档：`archives/d/duff/0.5.2/`（conan ref：`duff/0.5.2`）

## 1. 依赖核验（W0，适配前）

```
$ export CONAN_HOME=<zero-cache>; conan remote add ohpcd <...> --force --index 0
$ conan download "zzz-nonexistent-pkg/9.9.9" -r=ohpcd --only-recipe   # rc=1（对照组）
$ conan download "gettext/0.22.5.1" -r=ohpcd --only-recipe            # rc=0
$ conan download "gettext/0.22.5.1:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"  # rc=0
```
结论：**唯一强制第三方依赖 = gettext/0.22.5.1**（配方已发布 + OHOS/armv8 binary 可消费）。
依据（configure.ac 逐行）：`AM_GNU_GETTEXT([external])`、`src/Makefile.am:7 duff_LDADD = @LIBINTL@`、
`lib/gettext.h` → `#include <libintl.h>`、`src/duff.h:29 #define _(String) gettext(String)`。
OHOS sysroot 的 `libintl.h` 无函数声明、`libc.so` 无 `gettext/textdomain` 符号、无 `libintl.a/.so`
→ “系统自带” 证伪，必须由 conan 包提供（host 运行依赖 + build 工具）。

## 2. 源码获取与核验

```
$ curl -sSL -m 90 -o duff-0.5.2.tar.gz \
    https://github.com/elmindreda/duff/archive/refs/tags/0.5.2.tar.gz   # http=200
$ sha256sum duff-0.5.2.tar.gz
149dd80f9758085ed199c37aa32ad869409fa5e2c8da8a51294bd64ca886e058        # 两次独立下载一致
$ tar tzf duff-0.5.2.tar.gz | wc -l      # 46
```
- 上游 tag 为 `0.5.2`（**无 v 前缀**，GitHub releases 为空）。
- SourceForge 官方发布 tarball 本环境**不可达**：`curl https://sourceforge.net/projects/duff/files/` rc=52、
  `.../rss?path=/` rc=35、`downloads.sourceforge.net/project/duff/duff/0.5.2/duff-0.5.2.tar.gz` rc=28。
- 快照形态：**只有 46 个文件**，无 `configure` / `Makefile.in` / `config.h.in` /
  `build-aux/` / `po/Makefile.in.in`，`m4/` 下只有 `ChangeLog` → 必须自行引导。

## 3. 上游测试入口核验（R51）

```
$ grep -rn 'TESTS\|check_PROGRAMS\|BUILD_TESTING' Makefile.am src/Makefile.am lib/Makefile.am man/Makefile.am
rc=1                                     # 无任何测试注册
$ ls -d tests test                       # 不存在
$ find . -maxdepth 2 -type d             # ./lib ./m4 ./man ./po ./src（无 tests/）
$ make check
make[1]: Nothing to be done for 'check'. # lib/src/po/man 四目录均无测试
$ grep -n 'SHA1_TEST\|SHA256_TEST' src/sha1.c src/sha256.c ...   # 唯一可执行上游测试入口
README.SHA:126-133  "Define SHA1_TEST to compile a simple test program ... \
                     > gcc -Wall -O2 -DSHA1_TEST -o test sha1.c"
```
**结论：上游无自动化测试套件**；可执行的上游测试入口是 `-DSHA{1,256,384,512}_TEST` 编译期自测
（4 算法 × 3 条 NIST 样例向量 = 12 项，期望值写在各 `shaX.c` 头部注释）。
`make check` 为空（不是失败，也不是通过），test_package 不替代上游测试统计。

## 4. 首次真实错误与修复（按发现顺序）

### 4.1 `aclocal` 缺失 → 引导工具链
```
$ autoreconf -i
Can't exec "aclocal": No such file or directory at .../Autom4te/FileUtils.pm line 299.
autoreconf: error: aclocal failed with exit status: 2                      # rc=2
```
根因：HNP 环境只有 autoconf 家族，缺 automake（aclocal/automake）。修复：conan
`tool_requires("autoconf/2.72") automake/1.18 gettext/0.22.5.1` 提供工具（配方 build_requirements）。

### 4.2 `AM_GNU_GETTEXT` 宏缺失 → 补 gettext 基础设施
```
configure.ac:11: warning: macro 'AM_GNU_GETTEXT' not found in library
configure.ac:11: error: possibly undefined macro: AM_GNU_GETTEXT
autoreconf: error: autoconf failed with exit status: 1                     # rc=1
```
根因：Git 快照的 `m4/` 为空（`ACLOCAL_AMFLAGS = -I m4`），gettext 的 `gettext.m4`/`nls.m4`/`po.m4`
等未被 aclocal 找到。修复：`ACLOCAL_PATH=<gettext>/share/aclocal`。

### 4.3 gettext 包内 `autopoint`/`gettextize` 不可用
```
$ autopoint -f
autopoint: *** Missing version: please specify in configure.ac through a line
'AM_GNU_GETTEXT_VERSION(x.yy.zz)'                                          # rc=1
$ gettextize -f -c --no-changelog
gettextize[399]: cd: //share/gettext: No such file or directory            # rc=1
```
根因（读脚本确认）：gettext 包以 `prefix="/"` 构建（`bin/autopoint:30 prefix="/"`），
`gettext_datadir` 解析成 `//share/gettext`；且上游 `configure.ac` 没有
`AM_GNU_GETTEXT_VERSION`，autopoint 拒绝执行。
修复（沿用仓内 authselect / libzbar / centerim5 做法）：`AUTOPOINT=true` 跳过坏工具，
把 `share/gettext/po/` 的 `Makefile.in.in`、`Rules-quot`、`quot.sed`、`boldquot.sed`、
`en@quot.header`、`en@boldquot.header`、`insert-header.sin`、`remove-potcdate.sin`
与 `share/gettext/config.rpath`、`ABOUT-NLS` 复制进源码树。`autoreconf -fi` → rc=0。

### 4.4 E007：`config.guess` 不识别 HarmonyOS
```
uname -s = HarmonyOS
configure: error: cannot guess build type; you must specify one             # rc=1
```
修复：`perl $SKILL/scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub`
（配方内以等价文本替换实现，autoreconf 之后执行；**不使用** `--build/--host` 绕过，R1）。
验证：`./build-aux/config.guess` → `aarch64-unknown-linux-ohos`。

### 4.5 E114：`config.status` 临时目录在 HMDFS 上不可写
```
./config.status: line 623: ./confIdkObn/subs1.awk: Permission denied
config.status: error: could not setup config files machinery              # rc=1
```
根因（复现实验）：`configure` 内 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\``，
HMDFS 下建出的目录是 `drwx--S---`（setgid + 0700），写 `subs1.awk` 被拒；同目录 `umask 022`
时得到 `drwxr-s--x` 可写。修复：去掉 `umask 077`（mktemp 与 mkdir 回退两条路径），
configure → rc=0，生成 `Makefile`/`src/config.h`/`po/Makefile`。

### 4.6 上游：NLS 静默关闭（不注入 gettext 时）
```
checking for GNU gettext in libc... no
checking for GNU gettext in libintl... no
checking whether to use NLS... no                                         → config.h 无 ENABLE_NLS
```
不注入 gettext 的 `include/`+`lib/` 时 `USE_NLS=no`，duff 的 `_()` 退化为原文，译文全部丢失
（功能退化，非报错）。修复：`requirements("gettext/0.22.5.1")` → AutotoolsDeps 注入
`CPPFLAGS/LDFLAGS` → `checking for GNU gettext in libintl... yes` / `whether to use NLS... yes`
→ `#define ENABLE_NLS 1`，`Makefile: LIBINTL = .../lib/libintl.so`。

### 4.7 `po/` 构建失败：缺 quot 规则
```
make[2]: *** No rule to make target 'remove-potcdate.sin', needed by 'remove-potcdate.sed'.  Stop.
→ 补齐 remove-potcdate.sin 等文件后：
File en@boldquot.po does not exist. If you are a translator, you can create it through 'msginit'.
make[1]: *** [Makefile:201: stamp-po] Error 2                             # rc=2
```
根因：`po/LINGUAS` 声明 `en en@quot en@boldquot sv`，`en@quot`/`en@boldquot` 由 gettext 的
quot 规则（`po/Rules-quot`）生成，而生成的 `po/Makefile` 未包含该规则文件——上游
`po/Makevars` 缺 `include $(srcdir)/Rules-quot`（gettextize 不写这一行）。
修复：`patches/0001-po-Makevars.patch` 补上 → `make` rc=0，
生成 `en.gmo / en@quot.gmo / en@boldquot.gmo / sv.gmo`。

## 5. 真实构建与安装（exploration，模式 B）

```
$ ACLOCAL_PATH=<gettext>/share/aclocal AUTOPOINT=true autoreconf -fi        # rc=0
$ perl patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub  # rc=0
$ (去掉 configure 中 umask 077)
$ ./configure --prefix=$DEFAULT_PREFIX CC=clang CFLAGS="-fPIC -O2" \
      CPPFLAGS=-I<gettext>/include LDFLAGS=-L<gettext>/lib                  # rc=0
$ make -j2                                                                  # rc=0
$ make install DESTDIR=$TEST_PREFIX                                         # rc=0 → staging
$ make check                                                                # rc=0（无测试：Nothing to be done）
```
staging 产物：`bin/duff`、`share/locale/{en,en@quot,en@boldquot,sv}/LC_MESSAGES/duff.mo`、
`share/man/man1/duff.1`、`share/doc/duff/README.SHA`、`share/duff/join-duplicates.sh`。
`readelf -d bin/duff` → `NEEDED libintl.so.8`、`NEEDED libc.so`（musl）。

## 6. 上游测试实测（详见 reports/test-report.md 与 logs/t_log.txt）

- **A 组 上游自测入口（12 项，全通过）**：`clang -Wall -O2 -DSHA{1,256,384,512}_TEST -DHAVE_CONFIG_H -Isrc`
  编译 4 个自测程序并比对 NIST 向量（`"abc"` / 448-bit / 1,000,000×`'a'`）→ 12/12 PASS。
- **B 组 上游 CLI 行为 + 安装物检查（33 项全部通过 + 1 跳过；其中 CLI 行为 30 + 安装物 3）**：真实执行安装的 `duff`，覆盖 `-r/-e/-z/-t/-d sha1|sha256|sha384|sha512/-0/-l/-f/-q/-a/-P/-L/-H/-h/-v`
  与错误路径；跳过 1 项 = `-p` physical 硬链接语义（HMDFS 不支持创建硬链接，`ln` 报 EPERM）。
- **C 组 OHOS 平台契约（10 项，全通过）**：AArch64 ELF、`libintl.so.8`、musl `libc.so`、
  `ENABLE_NLS=1`、`config.guess` 产出 `aarch64-unknown-linux-ohos`、4 个语言目录入包、
  `LANGUAGE=sv` 下实际输出瑞典语（`filer i grupp`）、C locale 英文对照。
- 合计：**55 PASS / 0 FAIL / 1 SKIP**（分组计数：上游 NIST 自测 12 + CLI 行为/安装物 33 + OHOS 契约 10 = 55；SKIP 1 = `-p` 硬链接语义）。命令与原始输出见 `duff-logs/audit-0.5.2/2_suite_local.log`；完整用例清单与命令见 `reports/test-report.md`。

## 7. 遗留 / 已知限制

- HMDFS 不能创建硬链接（`ln` → `EPERM`），`-p`（physical）语义无法在 OHOS 上用例验证；
  文档已注明。
- `-L`/`-H` 下指向目录的符号链接会因与目标目录同 `(dev, inode)` 被 `has_recorded_directory()`
  去重（上游 `duffdriver.c` 既有语义，非平台问题）；已用实测输出确认。
- `configure`/`Makefile.in`/`config.guess` 等为构建期生成文件，平台修复在 `build()` 中
  autoreconf 之后施加（不打补丁到生成物，避免与 autoreconf 版本耦合）。

### 4.8 conan 配方阶段：`autoconf/2.72` 的 perl 污染系统 autoreconf
```
duff/0.5.2@ohpcd/stable: RUN: ACLOCAL_PATH="..." AUTOPOINT=true autoreconf -fi
Can't load '/storage/.../.conan2/p/perlbad96edf51f7f/p/lib/perl5/5.42.2/aarch64-linux-thread-multi/auto/Cwd/Cwd.so'
  for module Cwd: Error relocating ...: Perl_my_cxt_init: symbol not found
Compilation failed in require at /data/service/hnp/bin/autoreconf line 48.
ERROR: ... Error in build() method ... ConanException: Error 255
```
根因：`tool_requires("autoconf/2.72")` 的传递依赖 `perl/5.42.2` 把 `PERL5LIB` 注入 build 环境，
而 `autoreconf` 是系统 perl 脚本，加载 conan perl 的 `Cwd.so` 时符号不兼容。
修复：`build_requirements()` 不声明 autoconf（OHOS 镜像自带 autoconf/autoreconf/autoheader 2.72），
只声明 `automake/1.18` + `m4/1.4.19` + `gettext/0.22.5.1`；依赖图中不再出现 perl，autoreconf rc=0。

### 4.9 conan 配方阶段：gettext 的 `cpp_info.libs` 过度链接导致 conftest 失败
```
/data/service/hnp/bin/clang ... conftest.c -lintl -lgettextpo -lasprintf -ltextstyle
ld.lld: error: unable to find library -lasprintf
configure: error: C compiler cannot create executables
```
根因：gettext/0.22.5.1 的 `cpp_info.libs` 含 `asprintf`，但包内 `lib/` 无 `libasprintf`
（只有 libintl/libgettextpo/libtextstyle/libgettextlib/libgettextsrc）。
修复：`generate()` 中 `deps.environment.define("LIBS", ["-lintl"])`（duff 只需 libintl）。
验证：`checking whether the C compiler works... yes`、`checking for GNU gettext in libintl... yes`。

## 8. conan create / conan-verify 实测（clean 构建）

```
$ conan create archives/d/duff/0.5.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
→ G2 PASS；test_package 21 PASS / 0 FAIL
$ python3 scripts/ohc-run.py conan-verify duff 0.5.2
→ G0/G1/G2/G3/G4 PASS，L2/L4/L5 因工具侧问题跳过（见 §9），RC=0
```
包内容（`conan cache path duff/0.5.2@ohpcd/stable:<pkgid>`）：
`bin/duff`、`licenses/COPYING`、`share/locale/{en,en@quot,en@boldquot,sv}/LC_MESSAGES/duff.mo`、
`share/man/man1/duff.1`、`share/doc/duff/README.SHA`、`share/duff/join-duplicates.sh`（无 lib/、include/，符合纯 CLI 包）。

人工补齐 L2/L4/L5 等价证据：
- L2 smoke：`<pkg>/bin/duff -v` → `duff 0.5.2`（rc=0）
- L4 安全属性：`Type: DYN (PIE)`、`GNU_RELRO`、`GNU_STACK RW`（NX）、`BIND_NOW` → 全硬化
- L5 基线：`bin/duff` sha256 = `c3381818390d899864384c489603a23b63e99550b4deab2ef641887f6654bd82`

### 8.1 `duff/0.5.2` 复核复跑（交付最终证据链）

```
$ conan-verify duff 0.5.2                       → RC=0，G0/G1/G2/G3/G4 PASS；test_package 21/21
$ finish duff 0.5.2 built                        → W3 本地 CI 阻塞门禁通过（Pass rate 100% (1/1)），status=built
                                                     .ci-result.json: exit_code=0
$ 上游测试套件（本地构建轮次，duff/0.5.2）          → 55 PASS / 0 FAIL / 1 SKIP
$ test_package（conan create 内，duff/0.5.2）      → 21 PASS / 0 FAIL
$ sh join-duplicates.sh <dir>                      → EXIT=1（HMDFS 不支持 ln 硬链接；其 duff 前半段单独运行 EXIT=0）
```
日志：`$HOME/Desktop/ran_workspace/duff-logs/audit-0.5.2/{finish.log,1_suite_local.log,2_suite_package.log,1_t_log_local.txt,2_t_log_package.txt}`
、`duff-logs/v1_conan_verify_0521.log`；报告：`reports/{conan-verify-report.md,conan-create.log,w3-local-ci.log,test-report.md,audit-result.json}`。

> 说明：本节复核复跑在**同一份配方内容**上完成（包版本与归档目录为 `duff/0.5.2`），
> 上游源码 URL 与 sha256 不变；§4–§7 的逐步错误记录均录自同一套配方逻辑。

## 9. 工具侧问题与测试环境陷阱（本次实测发现）

1. **conan-verify G4 包 ID 发现失败 → L2/L4/L5 跳过**：G4 用
   `conan list <ref>:* --format=json` 后按 `listing["Local Cache"][software][ref]` 取包，
   但实际 JSON 结构是 `listing["Local Cache"][<完整 ref>]`（第一级键就是 `duff/0.5.2@ohpcd/stable`），
   于是 KeyError → "⚠️ 无法找到程序包 ID"，`_cache_path` 未赋值，L2/L4/L5 全部"跳过"。
   已人工补齐等价证据（见 §8）。
2. **test_package 环境 PATH 命中 toybox grep**：conanrun 下 `grep` 解析到 `/system/bin/grep`
   （toybox 0.8.12），对二进制文件（`.mo`）内容检索恒返回 0 命中；改用 gettext 包自带
   `msgunfmt` 把 `.mo` 还原成文本再断言（同时验证 catalog 结构）。
3. **LOCALEDIR 绝对路径 vs Conan 可重定位布局**：`--prefix=/` 使二进制内
   `LOCALEDIR=//share/locale`，payload 落在 `<pkg>/share/locale`；从 cache 直接运行不加载译文，
   `TEXTDOMAINDIR` 不能覆盖（libintl 在显式 `bindtextdomain` 后忽略该变量，已实测）。
   该差异已在 README「LOCALEDIR 契约」写明，test_package 只断言 payload 真实性与内置路径。
---

**编译结束**: 2026-09-30 23:13
**最终状态**: built
