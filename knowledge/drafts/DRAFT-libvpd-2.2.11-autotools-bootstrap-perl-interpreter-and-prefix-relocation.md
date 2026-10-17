# OHPC conan tool_requires 的 autoconf/automake/perl 包 Perl 解释器与数据前缀不可重定位

> 对应草稿: `knowledge/drafts/DRAFT-libvpd-2.2.11-autotools-bootstrap-perl-interpreter-and-prefix-relocation.kv`
> 来源: task libvpd-2.2.11-r01-pc7-28（feat/libvpd-2.2.11）· Path B 知识库扩展

## 问题

以官方 tag tarball（不含生成的 `configure`，如 libvpd 2.2.11）为源码的 autotools 库，
在 conan recipe `build()` 内做 bootstrap（`aclocal` → `autoheader` → `automake --add-missing` → `autoconf`）时，
连续出现三类错误：

| 错误 | 直接原因 |
|------|----------|
| `Can't locate strict.pm in @INC`（@INC 为 `//lib/perl5/5.42.2/...`） | autom4te/autoconf/autoheader 的 `.real` 脚本 shebang 硬编码 **conan perl**（5.42.2），其编译期 @INC 为损坏前缀 `//lib/perl5` |
| `Perl_my_cxt_init: symbol not found`（加载 `auto/Cwd/Cwd.so`） | aclocal/automake 的 `.real` 脚本 shebang 硬编码 **系统 perl**（5.42.0），却加载了 conan perl 5.42.2 的 XS 模块（conanbuild env 把其模块目录前置进 `PERL5LIB`） |
| `autom4te: m4sugar/m4sugar.m4: no such file or directory` | `autom4te.cfg` 中 `--prepend-include '//share/autoconf'` 为损坏前缀 |

根因一句话：**同一 bootstrap 进程内出现两个 ABI 不兼容的 perl 解释器，且 autoconf/automake/libtool 包把数据前缀烘焙成损坏的 `//share/...`。**

## 根因详解

- ohpcd 的 `automake/1.18` 包：`.aclocal-real`/`.automake-real` shebang = `#!/data/service/hnp/bin/perl`（系统 perl 5.42.0），
  Perl 模块目录需 `PERL5LIB=<pkg>/share/automake-1.18`（烘焙的 `'//share/automake-1.18'` 不可用）。
- ohpcd 的 `autoconf/2.72` 包：`.autom4te-real`/`.autoconf-real`/`.autoheader-real` shebang = conan perl（`.../perlbad96edf51f7f/p/bin/perl`，5.42.2），
  其编译期 @INC 为 `//lib/perl5/5.42.2/...`（不重定位，必须靠 PERL5LIB 提供模块）；
  数据目录 env 默认值 `'//share/autoconf'` 损坏；`autom4te.cfg` 的 `--prepend-include '//share/autoconf'` 损坏。
- ohpcd 的 `perl/5.42.2` 包 env 把其模块目录列表前置进 `PERL5LIB` → 系统 perl 脚本加载 5.42.2 XS → ABI 崩。
- ohpcd 的 `libtool/2.5.4` 包：`pkgauxdir` 烘焙为 `'//share/libtool/build-aux'` → `libtoolize --force` 直接报错。

## 方案（配 libvpd/2.2.11 实做验证）

在 `build()` 内生成包装器目录 `build_folder/autotools-bin`：

1. 为 `autom4te`、`autoconf`、`autoheader` 各写一个 sh 包装器，
   统一用 **系统 perl** 执行包内 `.autom4te-real`/`.autoconf-real`/`.autoheader-real`，
   并 `export`：
   - `autom4te_perllibdir=<autoconf 包>/share/autoconf`
   - `AC_MACRODIR=<autoconf 包>/share/autoconf`
   - `AUTOM4TE_CFG=<副本 autom4te.cfg>`（把 `//share/autoconf` 替换为真实路径）
2. bootstrap 各命令统一前缀：
   `PATH=<wrp>:/data/service/hnp/bin:$PATH AUTOM4TE=<wrp>/autom4te AUTOCONF=<wrp>/autoconf AUTOHEADER=<wrp>/autoheader PERL5LIB=<automake 包>/share/automake-1.18`
   （`AUTOM4TE`/`AUTOCONF`/`AUTOHEADER` env 钉住是必要的：aclocal 用 `$AUTOM4TE`、
   automake 用 `$AUTOCONF` 解析，会绕过 PATH 前缀直接命中包内 bin→real 链）。
3. 跳过损坏的 `libtoolize`：`cp <libtool 包>/share/libtool/build-aux/ltmain.sh config/`，
   `aclocal` 经 `ACLOCAL_PATH=<libtool 包>/share/aclocal` 取 libtool.m4。
4. 配套 HMFS 修复（E011 等既有条目）：configure 生成的 `config.status` 用
   `umask 077 && mktemp -d` 建临时目录被 HMFS 归一化（0700→0760，组无 x）阻塞时，
   `sed -i 's/umask 077/umask 002/g' config.status` 后重跑。

## 验证

- `conan create` 全程通过（configure 全部检查 yes；C/C++ 双库链接成功；test_package 1/1）。
- 消费者验证 + HarmonyOS 专项测试（`__OHOS__`、dlopen、pack/unpack 往返）ALL PASS。
- `.ci-result.json` exit_code=0；W3 本地 CI 模拟 PASS。

## 适用边界

- **适用**：OHPC/HMFS 上使用 ohpcd `autoconf/2.72` `automake/1.18` `libtool/2.5.4` `perl/5.42.2`
  tool_requires 构建「无生成 configure 的 tag 源码」autotools 库的场景。
- **反例/边界**：标准 Linux 工具链（单 perl、真实前缀、非 HMFS）无此问题；已携带
  生成 configure 的 release tarball 不需要 bootstrap，不受影响。

## 查重关系

- 与 E116（`Can't locate Automake/Config.pm`，建议从源码编译 automake）同族但新增差异：
  本条目针对 ohpcd 既有二进制工具包，验证「wrapper + env 钉住」不改包、不做源码编译的解法。
- 与 E049（shebang 硬编码可移植性）部分重叠：本条目覆盖 conan 包内双 perl ABI 冲突与
  数据前缀（autom4te.cfg/AC_MACRODIR）的 env 重定位，均可跨库复用。
- 与 E011/E052/E060/E110/E112/E114/E118/E125（HMFS config.status umask）互为配套，不重复。