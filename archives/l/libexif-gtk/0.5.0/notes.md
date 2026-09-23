# libexif-gtk 0.5.0 适配笔记

## 编译环境
- 构建系统: **autotools**（configure + make；上游 release tarball 自带 configure/Makefile.in）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）、GNU Make 4.4.1、autoconf 2.72、pkg-config 0.29.2
- 目标平台: OpenHarmony/HarmonyOS PC aarch64（`os=OHOS os.version=6.0 arch=armv8 compiler=clang15`）
- 状态: **built**（本地 conan create 通过；未上传制品仓、未提 PR）
- 变体: **GTK3**（`--with-gtk3`；上游默认 gtk2，Debian 打包同为 GTK3）

## 源码与版本核验
| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/libexif/libexif-gtk |
| tag / commit | `v0.5.0` / `990b5ec933d9558a48562dc408c68d450736bd45`（2020-08-31T09:02:22Z） |
| 源码 URL | https://github.com/libexif/libexif-gtk/releases/download/v0.5.0/libexif-gtk-0.5.0.tar.gz |
| 大小 / sha256 | 475056 B / `b8ca3729e2ccfd4ee047b99a4a8696c7bb8222f9cd1fa8fd698a393673bfdf3f` |
| 顶层目录 | `libexif-gtk-0.5.0/`（109 个文件） |

> **取源决策**：GitHub tag 自动 tarball 与 Debian `orig.tar.gz`（56462 B）**都不含 `configure`**，
> 需 `autoreconf`（本机与 CI 无 automake/libtool）；而 release 附件（475056 B）是 `make dist` 产物，
> 已含 `configure` / `Makefile.in` / `po/Makefile.in.in`，**直接 configure 即可**。
> 制品仓中 `automake/1.18` 虽可消费（`conan download` exit 0），仍优先选官方 release 资产（R39 官方源）。

## 依赖
- 直接依赖（上游构建文件实证）：
  - `libexif/0.6.26.1` —— `configure.ac:78 GP_CHECK_LIBRARY([LIBEXIF],[libexif])`、`-lexif`、9 个源文件 `#include <libexif/…>`
  - `gtk/3.24.43` —— `configure.ac:67 GP_CHECK_LIBRARY([GTK],[gtk+-3.0])`、`$(GTK_CFLAGS)/$(GTK_LIBS)`
  - `pkgconf`（pkg-config 可执行）—— `configure.ac:19 PKG_PROG_PKG_CONFIG`；**不加 tool_requires**：
    pkgconf 配方明确不产出 `pkg-config` 别名（pkgconf/3.0.6 conanfile.py:636 断言其不存在），
    autotools 的 `PKG_PROG_PKG_CONFIG` 只查 `pkg-config`；CI profile 的 PATH 含
    `/data/service/hnp/bin/pkg-config`（实测 0.29.2），与同族 gtkspell3/3.0.10-r3 做法一致。
  - `gettext` —— 上游 NLS 需要，但本配方显式 `--disable-nls`（见下文），**不作依赖**。
- 传递依赖：`gtk+-3.0.pc` 的 Requires 闭包（glib/cairo/pango/gdk-pixbuf/atk/fribidi/libepoxy 及更深层）
  由 `conan graph info --requires=gtk/3.24.43 -r=ohpcd` 实测 24 节点，全部 `conan download` exit 0。
  `gdk-pixbuf` 虽被源码 `gtk-exif-browser.c:40` 直接 include，但由 gtk+-3.0.pc 提供，不单列。

## 编译步骤（真实命令）
```bash
# 1. 依赖的 pkg-config 前缀（conan install + PkgConfigDeps 由配方 generate() 承担；
#    探索阶段用独立 build 目录模拟）
conan install --requires=libexif/0.6.26.1 --requires=gtk/3.24.43 \
  -r=ohpcd --build=never -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> -g PkgConfigDeps

# 2. configure（GTK3 变体 + rpath/NLS 关闭）
PKG_CONFIG_PATH=<deps> CC=clang CFLAGS="-fPIC -O2" \
  ./configure --prefix=$HOME/usr/local --with-gtk3 --disable-rpath --disable-nls

# 3. 构建 / 安装（E074：HMDFS 上串行 make）
make -j1 && make install DESTDIR=$HOME/tmp/test-install-libexif-gtk-0.5.0
make check          # 上游无测试目标，仅递归空跑（exit 0）
```

## 遇到的问题与解决方案

| # | 现象（首个错误，原文） | 根因 | 最小修改 | 重验证 |
|---|---|---|---|---|
| F1 | `./config.guess[1602]: can't create /storage/Users/currentUser/tmp/cgXXXXXX/dummy.c: Permission denied` → `./config.guess: unable to guess system type` → `configure: error: cannot guess build type; you must specify one` | ① config.guess 2020-01-01 vintage 无 HarmonyOS 分支；② `set_cc_for_build` 用 `umask 077` 建临时目录，HMDFS 下变不可写 | 按 E007 用 SKILL 自带 `scripts/patch-autotools-ohos.pl` 打补丁；该脚本对 2020 vintage 只命中 1/5 处，且此 vintage 主 case 分支用 `echo …; exit` 而非 `GUESS=` 变量，故手工把插入块的 `GUESS=${MACHINE}-unknown-linux-ohos` 改成 `echo "${MACHINE}-unknown-linux-ohos"; exit`，并在 config.sub 的 basic OS 白名单加入 `linux-ohos*` | `./config.guess` → `aarch64-unknown-linux-ohos`（exit 0）；`./config.sub aarch64-unknown-linux-ohos` → 同值（exit 0） |
| F2 | `./config.status[1037]: can't create ./confXXXXXX/subs1.awk: Permission denied` → 报错 `could not setup config files machinery` | E136：`umask 077 && mktemp -d "./confXXXXXX"` 在 HMDFS 上生成不可写的 `drwx--S---` 目录 | configure 的 ac_tmp 块改为 `umask 022` + `${HOME}/tmp/confXXXXXX`（3 行，同族 libexif/0.6.26.1 同款）。改 configure 即同时修好 config.status 脚本（其内容来自 configure 的 heredoc） | configure 全程通过：`configure: creating ./config.status` 后连续输出 10 个 `creating …` 行，exit 0 |
| F3 | `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: bind_textdomain_codeset`（`>>> referenced by ../libexif-gtk/.libs/libexif-gtk3.so`）→ `make[2]: *** [Makefile:402: test-libexif-gtk] Error 1` | 上游 12 个源文件无条件调用 `bind_textdomain_codeset()`；`#ifdef ENABLE_NLS` 的 `#else` 分支只定义了 `textdomain/gettext/dgettext/dcgettext/bindtextdomain` 5 个 no-op 宏，漏了 `bind_textdomain_codeset`。OHOS 无 libc libintl（configure 实测 `GNU gettext in libc… no` / `in libintl… no` → `whether to use NLS… no`），该符号无人提供，进入 .so 的未定义符号表 | 14 个同 prologue 文件（其中 12 个实际调用）的 no-op 宏块各补 1 行 `#  define bind_textdomain_codeset(Domain,Codeset) (Domain)` | `make -j1` exit 0；`llvm-nm -D --undefined-only libexif-gtk3.so.5.1.0 | grep -i textdomain` 无输出；上游示例程序 `tests/test-libexif-gtk` 链接并运行成功 |
| F4 | test_package 编译：`pango/pango-coverage.h:28:10: fatal error: 'hb.h' file not found` | gtk/3.24.43 是"扁平包"（不声明 `cpp_info.requires`），CMakeDeps 目标传不出 pango→harfbuzz 的传递头目录 | test_package 改用 pkg-config 解析完整 Requires 链（`pkg_check_modules(libexif-gtk3)`，gtkspell3-3.0 同款先例），并在 build() 里把 generators 目录前置进 `PKG_CONFIG_PATH` | `-- Checking for module 'libexif-gtk3'` → `Found libexif-gtk3, version 0.5.0`；编译链接通过 |
| F5 | test_package 运行：`Error loading shared library libexif-gtk3.so.5: Permission denied` + `Error relocating …: gtk_exif_browser_get_type: symbol not found` | **patchelf 重写后的 ELF 不被 OHOS 加载器接受**（同 ada-bar-codes/005 记录的约束）。此前为清理 libtool 硬编码的构建机 RUNPATH 加了 `patchelf --remove-rpath` | 移除 patchelf 步骤。RUNPATH 残留（指向构建机 conan 缓存）**无害**：OHOS 加载器先查 `LD_LIBRARY_PATH` 再查 `DT_RUNPATH`，Conan 运行环境始终提供完整 `LD_LIBRARY_PATH`；同仓已发布 GTK3 库（gtkspell3/3.0.10-r3）同样带该残留 | 移除后 test_package 运行 6/6 断言通过；同文件 `dlopen` 探针 OK（重写前 → `Permission denied`，重写后原件 → OK，直接对照实验） |
| F6 | test_package 编译警告 `call to undeclared function 'gtk_exif_content_list_get_type'` | 测试源只 include 了 `<libexif-gtk/gtk-exif-browser.h>`（该头不转发 content-list 头） | 测试源补 `#include <libexif-gtk/gtk-exif-content-list.h>` | 编译零警告 |
| **F7**（首轮 CI 暴露） | CI `conan-build-test` ❌：`mkdir: '/storage/Users/currentUser/tmp/conf8316-11777': No such file or directory` → `config.status: error: cannot create a temporary directory in .` | F2 的修法把 ac_tmp 指向 `${HOME}/tmp`，但**未创建该父目录**：本地探索机 `~/tmp` 恰好存在（TMPDIR 默认即 `~/tmp`）→ 本地全绿；CI worker 的 `$HOME` 可写却没有 `tmp/` 子目录 → `mktemp -d` 报 ENOENT，错误落在 config.status 阶段 | ① `0003-configure.patch` 两条分支各加 `mkdir -p`（`mkdir -p "${HOME}/tmp" && mktemp -d …`；fallback `mkdir -p "$tmp"`）；② 配方 `build()` 兜底 `Path(os.environ["HOME"])/"tmp".mkdir(parents=True, exist_ok=True)`（同族 libexif/0.6.26.1 的 E002 同款） | 隔离复现（`HOME=<存在但无 tmp/ 的目录>`）对照实验：旧补丁 exit 1 且报错与 CI 逐字一致；新补丁 exit 0 并自动创建 `$HOME/tmp`；修复后 `conan create` exit 0（6 checks, 0 failed）、W3 全门禁 pass |

## 关键设计决策
1. **`--disable-nls`（显式）**：上游 `libexif-gtk/Makefile.am` 的 `LIBADD` 未包含 `$(INTLLIBS)`，
   而开启 NLS 后 glib 的 proxy-libintl 头会把 `bindtextdomain/gettext/…` 重定向到
   `g_libintl_*`（实现在 glib 包自带的 libintl.so，本库未链接）→ .so 仍会留下未定义符号。
   显式关 NLS 后所有 i18n 调用走文件自带 stub（配合 F3 修补），构建确定、可复现；
   代价是不发布翻译文件（`po/` 不安装），对控件库功能无影响。
2. **`--disable-rpath`**：不把安装前缀写进产物 rpath（Debian 同款）。
   注意：libtool 仍会为"系统搜索路径之外"的依赖目录写入 RUNPATH（F5 已说明为何不清洗）。
3. **shared=True（默认）**：非系统同名库，按 Conan 动态依赖链管理；与同族 GTK3 控件库
   （gtkspell3、libhandy、gtksourceview3、ayatana-ido 等）一致。系统同名库静态化（R26）不适用本库。
4. **commands.json：不需要**（R38 不适用）：安装产物只有 `lib/` + `include/`，无 `bin/` 可执行文件。

## 上游测试入口（事实）
- `Makefile.am` / `tests/Makefile.am` / 各子目录：**无 `TESTS=`、无 `check_PROGRAMS`**（grep exit 1）；
  `make check` 只输出各目录 `Nothing to be done for 'check'.`，exit 0。
- 唯一程序 `tests/test-libexif-gtk.c`（`noinst_PROGRAMS`）是**交互式示例**：`gtk_init()` → 建窗 →
  `gtk_exif_browser_new()` → `exif_data_new_from_file(argv[1])` → `gtk_main()`，无断言、无退出码语义。
- 上游 `.travis.yml` 自述 `# There are no automated tests to run`；`README` 亦称之为 example program。
- 本配方已用 gtk 包自带的 `broadwayd`（HTML5 后端）在**无 X11/Wayland** 环境下真实运行该示例，
  4 个参数化用例全部通过（统计见 `reports/test-report.md`）。

## 验证结果
```bash
conan create archives/l/libexif-gtk/0.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → BUILD + TEST 全部通过；test_package 6 checks, 0 failed（含 1 条鸿蒙特有用例 OHOS-1）
```

**首轮 CI（PR #11607 / build #54325）曾失败于 `conan-build-test`（F7：`${HOME}/tmp` 父目录不存在，本地不复现），
已按上表修复并重验证：**
```bash
# ① 隔离复现 CI 场景（秒级）：HOME 存在但无 tmp/ 子目录
mkdir -p $SCRATCH/fakehome && HOME=$SCRATCH/fakehome ./configure …   # 旧补丁 exit 1（报错与 CI 一致）
                                                                     # 新补丁 exit 0，且自动创建 $HOME/tmp
# ② 修复后本地全量门禁
conan create archives/l/libexif-gtk/0.5.0 …        # exit 0；Package built/created；test_package 6 checks, 0 failed
zsh ci/conan/build_and_test.sh archives/l/libexif-gtk/0.5.0   # JC/L0/L1/L2/L5 pass，Pass rate 100%
```
产物（conan 包）：`include/libexif-gtk/*.h`（14）、`lib/libexif-gtk3.so{,.5,.5.1.0}`、
`lib/pkgconfig/libexif-gtk3.pc`、`licenses/COPYING`。

## 未执行项（按要求停在本地门禁）
- 未 `commit` / `push` / 创建 PR / 上传制品仓 / 远端 Review；
- 未执行 W4（Pre-PR 独立审计）——本轮任务清单止于 finish + W2/W3 + PR 文件原子性检查。

## 依赖版本
- libexif 0.6.26.1、gtk 3.24.43（及其 24 节点闭包，全部制品仓已发布可消费）
- clang 15.0.4、GNU Make 4.4.1、autoconf 2.72、pkg-config 0.29.2

---
**编译结束**: 2026-09-21（本地 staged，未发布）
**最终状态**: built

---

## 对话记录

### 对话 #1 — 依赖前置核验（W0）
- 目标：确认 libexif-gtk/0.5.0 的全部第三方依赖已发布可消费，不编译、不改动。
- 动作：`conan download <dep> -r=ohpcd --only-recipe` 逐个探测 27 个依赖 + 4 个负向对照；
  `conan graph info --requires=gtk/3.24.43 -r=ohpcd` 取闭包 24 节点。
- 结果：27/27 `exit 0`；负向对照（不存在的包、目标库自身、错误包名 `gtk+`、错误版本 `libexif/0.6.26`）全部 `exit 1`。
- 结论：强制第三方依赖缺口 0，可进入适配。

### 对话 #2 — 源码/测试入口核验 + init-build + 语言预检
- 取源：GitHub release 资产 `libexif-gtk-0.5.0.tar.gz`（475056 B，sha256 `b8ca3729…`，自带 `configure`）。
- `init-build`（`OHC_PROJECT_DIR` 指向本 worktree；首次误落在 SKILL 安装目录，已清理并重跑）。
- `lang-preflight`：`task=cpp, detected=c` —— C 语言（同族），继续主流程。
- 上游测试入口清点：无 `TESTS=`/`check_PROGRAMS`，唯一程序为交互式示例。

### 对话 #3 — 首次 configure 失败（F1）与三元组修复
- 首个错误：`config.guess: unable to guess system type`（伴 HMDFS 权限失败）。
- 根因：config.guess 无 HarmonyOS 分支 + `umask 077` 临时目录不可写。
- 修复：SKILL 自带 `patch-autotools-ohos.pl` + 手工校正（echo/exit 形式）+ config.sub 白名单。
- 重验证：`config.guess` 直出 `aarch64-unknown-linux-ohos`。

### 对话 #4 — config.status 失败（F2 / E136）与 i18n 链接失败（F3）
- F2：configure 临时目录权限 → 改 `${HOME}/tmp` + `umask 022`，configure 全流程通过。
- F3：`bind_textdomain_codeset` 未定义符号 → 14 文件补非 NLS 桩，`make` 通过，.so 无残留未定义符号。
- 上游测试实际执行：`broadwayd` + 5 个用例（3 有效 EXIF / 1 无 EXIF 负向 / 1 无参数），5 通过。

### 对话 #5 — conan 配方与测试包（F4/F5）
- `conan-init` 生成骨架 → 补齐 conanfile.py / conandata.yml(17 补丁) / manifest / test_package。
- F4：test_package 报 `hb.h` 找不到 → 改 pkg-config 链接（gtkspell3 先例）。
- F5：patchelf 清理 RUNPATH 导致 OHOS 加载器拒绝 → 撤销该步骤（对照实验留证）。
- `conan create` 通过（test_package 6 断言，含鸿蒙用例 OHOS-1）。

### 对话 #6 — conan-verify / finish / W2-W3 / 文件原子性
- `conan-verify`：G0–G4 全 PASS（L2/L4/L5 因校验器取不到包缓存路径而跳过，另做 L4 等价 readelf 复核）。
- `finish built`：W3 本地 CI 模拟首轮被 JC1/JC5 拦截，拦截对象是 **origin/main 中既有的
  `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
  `archives/k/kics/2.1.20/.staging-verified`**（非本任务产物；因本任务按约定不 commit，
  junk_check 退化为整仓 full 模式才扫到）。以 CI 的 PR-diff 模式（`JUNK_PR_DIFF`）重跑，W3 通过。
- 文件原子性：PR 等价 diff 仅 25 个文件，全部位于 `archives/l/libexif-gtk/0.5.0/`。
---

**编译结束**: 2026-09-21 02:32
**最终状态**: built
