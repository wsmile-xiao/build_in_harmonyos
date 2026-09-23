# pdf2svg 0.2.4 鸿蒙 PC 适配笔记

## 状态（2026-09-20）

- 依赖图求解 + 安装：**PASS**（本地 probe：15 个 host 包，fontconfig override 消解 version conflict）
- 上游自动化测试：**无**（tarball 无 `tests/`，`Makefile.am` 只有 `bin_PROGRAMS = pdf2svg`，见下"上游测试评估"）
- 构建实跑：由 CI（OHOS aarch64 原生构建）执行，本文件只记录**静态核验**与**方案取舍**
- 被测行为：`test_package/test_pdf2svg.sh` 对已安装的 `bin/pdf2svg` 做 6 项端到端断言

## 编译环境

- 构建系统: autotools（tarball 自带 `configure` / `Makefile.in` / `install-sh` / `depcomp` / `missing`）
- 编译器: clang 15（OHOS SDK，musl + libc++）
- 目标: aarch64-unknown-linux-ohos
- 包类型: `application`（只有 `bin/pdf2svg`，无可链接库、无可 include 头）
- 依赖: poppler/25.12.0.2、cairo/1.18.4、glib/2.84.0.1、fontconfig/2.18.1.1（override）

## 版本号说明（R37）

tarball 的 git tag 是 **v0.2.4**，但上游 `configure.ac` 里
`AC_INIT(pdf2svg, 0.2.1, ...)` **从未随发布递增**；tarball 自带的 `configure`
更陈旧 —— 它还在查 `cairo >= 1.2.6`，而 `configure.ac` 已经改成 `cairo >= 1.16`。

本包版本按 **tag** 记为 `pdf2svg/0.2.4`。程序自身不打印版本号（`pdf2svg.c`
没有 `--version` / `-V` 选项），所以版本一致性无法从产物侧反查 —— 这也是
L2 的 `--version` 冒烟探测对本包只给 non-blocking warn 的原因。

## 方案取舍：不调用 pkg-config（核心决策）

上游 `configure.ac` 用两条 `PKG_CHECK_MODULES` 声明依赖：

```
PKG_CHECK_MODULES(CAIRO,       cairo >= 1.16)
PKG_CHECK_MODULES(POPPLERGLIB, poppler-glib >= 0.5.4)
```

**本配方完全不调用 pkg-config**，而是走 `PKG_CHECK_MODULES` 自带的
`AC_ARG_VAR` 逃生口：生成的 `configure` 在 `if test -n "$CAIRO_CFLAGS"` 分支
（第 3674/3691 行）与 `if test -n "$POPPLERGLIB_CFLAGS"` 分支（第 3766/3783 行）
都非空时**直接采用**，不再执行 pkg-config。

### 为什么不用依赖包自带的 `.pc`（实测证据）

制品仓里各依赖包**自带**的 `.pc` 文件记录了**构建机的前缀**：

| .pc | 实测 prefix / Libs | pkg-config 会给出的结果 |
| --- | --- | --- |
| `cairo.pc` / `cairo-svg.pc` | `prefix=/` | `-I/include/cairo -L/lib -lcairo` |
| `poppler-glib.pc` / `poppler.pc` / `poppler-cpp.pc` | `prefix=/storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p` | 指向**另一台构建机**的 hash 目录（实际目录是 `poppl2e264df4b3b30`） |
| `glib-2.0.pc` | `prefix=/`，`Libs: -L${libdir} -lglib-2.0 -lintl` | `-L/lib -lglib-2.0 -lintl` |

把这些目录放进 `PKG_CONFIG_PATH` 的后果不是"找不到模块"，而是
**pkg-config 静默成功**却返回错误路径 —— 失败点从 `configure` 后移到
`compile`/`link`（找不到头文件、找不到库），排查成本更高。

替代方案（由 `cpp_info.aggregated_components()` 直接算 `-I` / `-L` / `-l`）
是最短的、只依赖制品仓**真实布局**的路径，也在本仓有先例（libxp/1.0.4、
xauth/1.1.4）。

### 两个实现细节

1. **必须用 `aggregated_components()`，不能用根 `cpp_info`。**
   glib 的 `include/glib-2.0`、`lib/glib-2.0/include`（`glibconfig.h`）与
   `include/gio-unix-2.0` 只存在于**组件**里；根 `cpp_info.includedirs` 只有
   一层 `include`，用它拼 CFLAGS 会让 `#include <glib.h>` 失败。
2. **不照抄 poppler 的 `cpp_info.libs`。**
   那是 `['poppler','poppler-glib','poppler-cpp']` 的**根级并集**，会白白拖进
   `poppler-cpp`。pdf2svg.c 只 include `<poppler.h>` / `<poppler-document.h>` /
   `<poppler-page.h>`（即 `poppler-glib`），因此链接行只写 `-lpoppler-glib`。

## 依赖图与 override

`poppler/25.12.0.2` 钉 `fontconfig/2.18.1`，`cairo/1.18.4` 钉
`fontconfig/2.18.1.1` —— 两个**精确**钉在图里直接撞 version conflict：

```
Conflict between fontconfig/2.18.1.1 and fontconfig/2.18.1 … originates from cairo/1.18.4
```

取较新的 `fontconfig/2.18.1.1`（`override=True`）。版本默认 `package_id` 模式是
`minor_mode`，poppler 的 package_id 不变，**制品仓里已发布的 poppler 二进制被
原样复用**，不触发源码重建。

求解出的 host 依赖共 15 个：boost、cairo、expat、fontconfig、freetype、glib、
lcms2、libjpeg-turbo、libpng、libtiff、libwebp、openjpeg、pixman、poppler、zstd；
build 依赖为空。

## configure 的 OHOS 运行期修补（不改源码，只改生成的 configure）

`build()` 的 `_patch_configure()` 对上游自带的 `configure` 做**两处**就地改写，
都是平台必需：

1. `umask 077` → `umask 022`：`config.status` 在 HMDFS 下用 `umask 077` 建临时
   目录会得到不可写/不可执行的目录（E002/E114）。
2. `ac_pwd=\`pwd\`` → `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"`：HMFS 下
   `getcwd` 不可达（HMBS `[shell_getcwd]`），配合 `build()` 里预置的
   `os.environ["PWD"]` 兜底。

**不跑 `autoreconf`**：tarball 里 `configure` / `Makefile.in` / `install-sh` /
`depcomp` / `missing` 配套齐全（`AM_INIT_AUTOMAKE([foreign])`），没有重建理由；
而且重新生成会让"生成的 configure 与上游 tarball 交付物一致"这一前提失效
（上游自带的 configure 与 configure.ac 的问版本号本来就不一致）。

另外 `build()` 里显式 `os.chdir(self.build_folder)` —— conan 的
`Autotools.configure()` **不会自己 chdir**（configure 在进程当前目录执行），
不切换就是 in-source 构建。

## 三元组的说明（不是绕过）

本包 `configure.ac` **没有** `AC_CANONICAL_*`，既不跑 `config.guess` 也不跑
`config.sub`。配方给 `--build=aarch64-linux --host=aarch64-linux` 的目的是：

- 让 `host_alias` 有值、`configure` 走 **non-cross** 分支；
- 挡住 profile 在跨机场景下可能注入的 `linux-ohos` 三元组（0.2.4 自带的
  `config.sub` 不认 `ohos`）。

CI 是 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64` 的**原生 OHOS 构建**
（host profile == build profile），此时 `AutotoolsToolchain` 本来就不会发出任何
`--host`/`--build`/`--target`；这两个参数是给三元组上保险，**不是**把 OHOS
伪装成别的系统。

## 上游测试评估

`upstream_tests_exist: false`。审计依据（三条独立判据）：

1. `tar tzf pdf2svg-0.2.4.tar.gz` 顶层**无** `tests/` / `test/` / `check/` 目录；
2. `Makefile.am` 全文只有 `bin_PROGRAMS = pdf2svg`、`pdf2svg_SOURCES`、
   `pdf2svg_CFLAGS`、`pdf2svg_LDADD`，**没有** `TESTS` / `check_PROGRAMS` /
   `check-local` / `TESTS_ENVIRONMENT`，`AM_INIT_AUTOMAKE([foreign])` 也不启用
   默认测试；
3. 无 `meson.build` / `CMakeLists.txt`，不存在另一套构建系统携带测试。

因此 `build()` **不调用** `make check` —— 调用会以
`No rule to make target 'check'` 失败，而不是"跳过测试"。被测行为改由
`test_package` 覆盖。

## test_package 设计（R34：二进制即被测 API）

`test_package/test_pdf2svg.sh` 真实执行**已安装的** `bin/pdf2svg`，6 项断言
（`/discovered=6`）：

| # | 调用 | 期望 |
| --- | --- | --- |
| 1 | 无参数 | stdout 有 `Usage: pdf2svg`，退出码 **254**（`main()` return -2） |
| 2 | `pdf2svg fixture.pdf out1.svg` | 退出码 0，`out1.svg` 非空且含 `<svg`（不给页号 → 默认第 1 页） |
| 3 | `pdf2svg fixture.pdf all-%d.svg all` | 退出码 0，产出 `all-1.svg` + `all-2.svg`（输出参数是 printf 格式串） |
| 4 | `pdf2svg no-such-file.pdf out4.svg` | stderr 有 `Unable to open file`，退出码 **253**（-3） |
| 5 | `pdf2svg fixture.pdf out5.svg 99` | `Page does not exist`，退出码 **252**（-4） |
| 6 | 比较 `all-1.svg` 与 `all-2.svg` | 两者内容**必须不同**（证明按页取页，而不是重复第 1 页） |

设计要点：

- **夹具 PDF 由 conanfile 用纯 Python 写出**（`_write_fixture_pdf`），2 页、
  纯矢量（矩形/折线，**无字体**）。xref 表的字节偏移是**算出来**的而不是手写
  常量，所以改内容流不会失配。无字体意味着渲染路径不经过
  fontconfig/freetype 的字体匹配，CI worker 上没有字体也不影响断言。
- **运行期寻库**（HMBS `[stale_runtime_library]`：OHOS loader 可能忽略
  `LD_LIBRARY_PATH`）：从已安装的 `bin/pdf2svg` 的 `DT_NEEDED` 出发做 **BFS**，
  把真正会被加载到的依赖 `.so` **绝对路径**经 `LD_PRELOAD` 注入。
  实现是纯 Python 解析 ELF64（读 section header 里的 `SHT_DYNAMIC` 与其
  `sh_link` 指向的字符串表），不依赖 `readelf`/`ldd` 存在于 worker 上。
  **不采用**"依赖包 libdir 里的 `.so` 全部 preload"：闭包外的库（例如 glib
  附带的 `libgirepository-2.0.so.0`）若某个 `DT_NEEDED` 在本次依赖图里不存在，
  `LD_PRELOAD` 会让进程直接起不来。
  conan 缓存里的库是 `.so` → `.so.N` → `.so.N.M.K` 符号链接链，HMFS 对
  symlink 物化不可靠（E050），故只取**非符号链接的实体文件**（loader 按
  SONAME 登记，效果等价）。
- **scratch 目录由 conanfile 传入**（`<build_folder>/pdf2svg-scratch`）并在其中
  写好 `fixture.pdf`：OHOS 的 `/tmp` 是 erofs 只读（E002），不能就地写夹具。
  脚本里把 `TMPDIR` / `TMP` / `TEMP` 都指向该目录。
- 脚本用 **HMBS 注入的 `$SHELL`/`$CONFIG_SHELL`**（POSIX sh）执行，不硬编码
  `/data/service/hnp/bin/bash`（HMBS `[shell_getcwd]`）；不用 `set -e/-u` /
  `pipefail`（toybox ash 拒绝），每条断言自己收 `rc` 并始终打印输出，让加载器
  错误能进 CI 日志。

## 已知限制

- 本包只有 CLI 产物，无 `cpp_info.libs` / `includedirs`（`package_info()` 里
  显式清空），下游不能把它当库链接 —— 这是工具的正常形态。
- `test_package` 对运行期 `.so` 闭包做了 BFS 注入，但**未**断言闭包完整性
  （若某个 `DT_NEEDED` 解析不到，会被当作 OHOS 系统库交给系统 loader）；
  这条以"断言 6 项行为全过"作为端到端证据。

## 参考

- 上游: https://github.com/dawbarton/pdf2svg
- 同批先例（`PKG_CHECK_MODULES` AC_ARG_VAR 逃生口）: `archives/l/libxp/1.0.4`、`archives/x/xauth/1.1.4`
- 同批先例（`DT_NEEDED` BFS + `LD_PRELOAD`）: `archives/x/xeyes/1.3.1`
