# duff

duff 是一个命令行重复文件查找工具：递归扫描给定路径，先按文件大小分桶，再抽样比较，最后用消息摘要（sha1/sha256/sha384/sha512）或逐字节比较确认，按“簇”输出重复文件及其摘要。

## 功能概述

- 递归（`-r`）扫描文件与目录，支持目录符号链接策略 `-P`/`-L`/`-H`
- 快速筛选：按大小分桶 + 前缀抽样（`-l` 控制激活抽样的最小文件大小）
- 摘要确认：`-d sha1|sha256|sha384|sha512`（默认 sha1）
- 逐字节确认：`-t`（thorough）
- 输出模式：`-e`（excess，仅列每簇多余副本）、`-f`（自定义簇头格式）、`-0`（NUL 分隔）、`-q`（静默）、`-z`（忽略空文件）、`-p`（physical，不把硬链接视为重复）
- 随包提供 `join-duplicates.sh`（用 duff 输出驱动硬链接合并）与 man 手册

## OHOS 适配

- **构建系统**：Autotools（`configure.ac` + `Makefile.am`），**上游 Git tag 快照不含 configure**，`build()` 内自行 `autoreconf -fi` 引导。
- **工具链**：`tool_requires` `automake/1.18` + `m4/1.4.19` + `gettext/0.22.5.1`；环境自带 autoconf/autoreconf（不声明 `autoconf/2.72` 是因为它的传递依赖 `perl/5.42.2` 会注入 `PERL5LIB`，使系统 `autoreconf` 加载不兼容的 `Cwd.so` 而中止：`Perl_my_cxt_init: symbol not found`）。
- **E007**：GNU `config.guess`（2024-07-27）不识别 `uname -s = "HarmonyOS"`，`configure` 报 `cannot guess build type; you must specify one`；在 `autoreconf` 之后补 `*:HarmonyOS:*:*)` 分支（产出 `aarch64-unknown-linux-ohos`）与 `__OHOS__` libc 探测，**不使用** `--build/--host` 伪造三元组。
- **E114**：`configure` 中 `(umask 077 && mktemp -d "./confXXXXXX")` 在 HMDFS 上生成 `drwx--S---` 临时目录，`config.status` 写 `subs1.awk` 报 `Permission denied → could not setup config files machinery`；去掉该 `umask 077`。
- **gettext 引导**：gettext 包内的 `autopoint`/`gettextize` 以 `prefix="/"` 构建（`gettext_datadir` 解析为 `//share/gettext`），且 `configure.ac` 无 `AM_GNU_GETTEXT_VERSION`，两者都不可用；改用 `ACLOCAL_PATH=<gettext>/share/aclocal` + `AUTOPOINT=true`，并把 `share/gettext` 下的 po 基础设施（`Makefile.in.in`、`Rules-quot`、`quot.sed`、`boldquot.sed`、`en@*.header`、`insert-header.sin`、`remove-potcdate.sin`）与 `config.rpath`、`ABOUT-NLS` 复制进源码树。
- **依赖链接**：`AutotoolsDeps` 会把 gettext 的 `cpp_info.libs`（`intl/gettextpo/asprintf/textstyle`）整体写入 `LIBS`，而包内没有 `libasprintf`，`conftest` 链接 `-lasprintf` 直接失败（`C compiler cannot create executables`）；`generate()` 中把 `LIBS` 收敛为 `-lintl`。

- **NLS**：OHOS（musl）libc 不提供 `libintl`（sysroot 的 `libintl.h` 无函数声明、`libc.so` 无 `gettext`/`textdomain` 符号、无 `libintl.a/.so`），`configure` 会把 `USE_NLS` 静默判为 no、译文全部丢失。`gettext/0.22.5.1` 作为**运行期依赖**提供 `libintl.h` + `libintl.so`，使 `configure` 判定 `whether to use NLS... yes`；`en`/`en@quot`/`en@boldquot`/`sv` 四个语言目录随包安装到 `share/locale`。
- **补丁**：`patches/0001-po-Makevars.patch` —— `po/Makevars` 补 `include $(srcdir)/Rules-quot`（`po/LINGUAS` 声明的 `en@quot`/`en@boldquot` 需要 gettext quot 规则，缺此行 `po/` 的 `make` 报 `File en@boldquot.po does not exist`）。
- **已知平台限制**：HMDFS 不支持创建硬链接（`ln` 报 `EPERM: Operation not permitted`），因此 `-p`（physical，硬链接语义）无法在 OHOS 上构造用例验证；`-P`/`-L`/`-H` 符号链接策略可正常执行（`-L`/`-H` 下指向目录的符号链接会因与目标目录同 inode 而被去重，属上游 `process_path()` 既有语义）。
- **LOCALEDIR 契约（重要）**：译文由 autoconf 以绝对路径编译进二进制。Conan 打包使用默认可重定位布局（`--prefix=/` + `DESTDIR=<pkg>`），因此二进制内 `LOCALEDIR` 为 `//share/locale`（等价 `/share/locale`）、payload 位于 `<pkg>/share/locale`。**直接用 `<pkg>/bin/duff` 运行时译文不加载（英文原文）**；把 `<pkg>/share/locale` 部署到根前缀 `share/locale` 后译文生效。`TEXTDOMAINDIR` 等环境变量无法覆盖（程序显式调用 `bindtextdomain`）。


## 依赖关系

| 类型 | 依赖 | 说明 |
|------|------|------|
| 运行 | `gettext/0.22.5.1` | 提供 `libintl.so.8`（NLS 译文加载）；OHOS libc 不含 libintl |
| 构建 | `automake/1.18`、`m4/1.4.19` | `autoreconf -fi` 引导（Git 快照无 configure） |
| 构建 | `gettext/0.22.5.1` | gettext m4 宏、po 基础设施、`xgettext`/`msgfmt`/`msginit` |
| 构建 | 镜像自带 `autoconf`/`autoreconf`/`autoheader`（2.72） | **不**声明 `tool_requires(autoconf/*)`：其传递依赖 `perl` 会注入 `PERL5LIB` 破坏系统 `autoreconf` |

## 参考资料

- 官网/官方发布：http://duff.sourceforge.net/
- 源码仓库：https://github.com/elmindreda/duff
- 适配归档：`archives/d/duff/0.5.2/`（包版本 `duff/0.5.2` = 上游 0.5.2，R37 首次适配版本号；`notes.md` 含逐步真实命令与错误记录）
