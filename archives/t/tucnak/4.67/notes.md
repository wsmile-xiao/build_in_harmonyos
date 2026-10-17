# tucnak 4.67 适配笔记

## 编译环境
- 构建系统: autotools（GNU autoconf/automake/libtool；两阶段：libzia 静态库 → tucnak in-tree）
- 编译日期: 2026-10-12
- 编译器: OHOS 平台 clang（宿主 x86_64 交叉构建 → 目标 aarch64-unknown-linux，OHOS sysroot）
- 状态: published

## 编译步骤

源码是两个 tarball（tucnak + libzia），必须以**同级目录**解包：tucnak 的
`configure` 找不到已安装的 `libzia.pc` 时会去找 `../libzia` 目录，静态链接
`../libzia/src/.libs/libzia.a` 并读取 `../libzia/bin/zia-config`。

1. `source()`：解包 tucnak 与 libzia 两个 tarball 到 `source_folder/{tucnak,libzia}`。
2. libzia（stage 1）：
   `./configure --host=aarch64-unknown-linux-ohos --build=x86_64-pc-linux-gnu --enable-static --disable-shared --without-sdl --without-sdl_ttf --without-png --without-ftdi --without-bfd --prefix=<build>/zia`
   然后 `make -j<jobs> -C src libzia.la`（只建静态库，见问题 4）。
3. tucnak（stage 2，in-tree 构建）：`./configure --host=aarch64-unknown-linux --build=x86_64-pc-linux-gnu --with-pkg=tucnak --prefix=/ --without-gpm --without-hamlib --without-fftw3 --without-portaudio --without-rtlsdr --without-hidapi --without-sndfile --without-alsa`
   然后**先** `perl font2inc.pl`（cwd=`data/`，见问题 7）**再** `make -j<jobs>`。
4. `package()`：`make install DESTDIR=$package_folder`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `zerror.c:190` 编译失败：`char *` 初始化用 int 表达式 | 上游 bug：configure 把 `Z_STRERROR_R_RETURNS_INT` 写进 `config.h`，但没有任何 libzia 源码 include 它（只读 `include/zconfig.h`）；glibc 的 `strerror_r` 返回 `char*` 恰好走对分支，OHOS/musl 返回 `int` 就走错 | `CFLAGS`/`CPPFLAGS` 显式传 `-DZ_STRERROR_R_RETURNS_INT` |
| 2 | libzia 链到宿主 x86_64 glib | pkg-config 默认搜索路径找到宿主 `/usr/include/glib-2.0` | `PKG_CONFIG_LIBDIR`/`PKG_CONFIG_PATH` 指向 PkgConfigDeps 生成目录 |
| 3 | libtool `'//lib/libpcre2-8.la' is not a valid libtool archive` | 制品仓 pcre2/10.45 的 `.la` 带设备残留（`libdir='//lib'`） | 在 build 目录生成修正后的 `.la` 副本并前置到 `LDFLAGS`（不改 conan 缓存） |
| 4 | libzia `make all` 报 `Can't open 'libzia.so.map'` | `src/Makefile.am` 无条件声明 `.so.d: libzia.la map2d` 目标，link map 仅共享库构建产出 | 只静态构建 + `make -C src libzia.la` |
| 5 | tucnak configure 拒绝 `aarch64-unknown-linux-ohos` | 捆绑的 2018-02-22 config.sub 不认 `-ohos` | tucnak 的 `--host` 用不带 `-ohos` 的 gnu 拼写（configure.ac 无 host_os 分支，值惰性） |
| 6 | `subs1.awk: Permission denied`（CI #83509） | CI worker 的 HMDFS 工作区 umask 077，`config.status` 临时目录对同用户不同进程不可读写（知识库 E011） | 补丁 `0001-fix-config-status-hmdfs-umask.patch`：libzia/tucnak 两处 `configure` 的 AC_OUTPUT 临时目录 `umask 077→022` |
| 7 | `./font2inc.pl: /usr/bin/perl: bad interpreter: No such file or directory`（CI #85140/#85246/#85283/#85303） | 真机 CI worker **无 `/usr/bin/perl`**（平台 perl 只在 PATH），内核按 shebang 绝对路径解析解释器，PATH 无关 | `build()` 在 `make` 前用 PATH perl 预跑 `perl font2inc.pl`，`make` 见产物已新即跳过 shebang 规则 |
| 8 | `use of undeclared identifier 'T_EVEN'/'T_STARTING_AC'` 等（CI #85454） | 第一轮修复预跑了全部 perl 生成器（含 `intl/gen-intl`）；该脚本的 `#define T_*` 管线用 `cat -n`，而真机 `cat` 不支持 `-n`，于是残缺 `language.h` 覆盖了 tarball 预置的完整版 | **只**预跑 `font2inc`；`src/{language,txts}.{h,inc}` 一律用 release tarball 预置版（mtime 等于 make 前置，make 天然跳过其规则） |
| 9 | push 后构建仍跑旧 head（CI #85444） | checkout 竞态 | 判「修复无效」前先把失败日志的 RUN 行/行号与当前配方逐行对质 |

## 源码修改

- `patches/0001-fix-config-status-hmdfs-umask.patch`：把 libzia 与 tucnak 两个**生成的**
  `configure` 脚本中 AC_OUTPUT 创建临时目录的 `umask 077` 改为 `022`（各 2 处）。
  该片段出自 autoconf 模板，只存在于生成的 configure、不在 configure.ac 里，故只能改生成文件。
- 未修改任何上游源码；未改任何上游测试用例。

## 依赖版本

- `glib/2.88.0` — 硬依赖：libzia 的 `include/zerror.h`、`include/zstr.h` 无 `HAVE_GLIB` 保护直接
  `#include <glib.h>`，10 个源码文件直接 include，无 glib 无法构建（configure 缺 pkg-config 时只是
  不打印，编译期才失败）。
- `pcre2/10.45`、`zlib/1.3.1` — glib 的传递依赖。
- **不依赖** ncurses / gettext：tucnak 自带终端处理（`src/` 无 `<curses.h>`），`intl/` 仅 `.lng` 语言数据文件。

## 验证结果

本地同源门禁（2026-10-12，干净 worktree `7e3856d83d`，profile `ohos-aarch64-wsl`）：

```bash
CI_BRANCH=feat/tucnak-4.67 CONAN_PROFILE=ohos-aarch64-wsl \
  CI_PACKAGES=archives/t/tucnak/4.67 zsh ci/conan/build_and_test.sh
# G0_RESULT=pass
# L0i: dependency in registry: glib/2.88.0        [ok]
# L0j: version not in registry yet (first publish) [ok]
# L0k: commands.json valid (type=tool)             [ok]
# L0m: directory structure valid                   [ok]
# JC_RESULT=pass (JC_ERRORS=0)
# L0_RESULT=pass   L1_RESULT=pass   L1e: 破坏性反向验证通过
# L2_RESULT=skip (本地 x86_64 宿主无法运行 aarch64 产物，非阻塞)
# L4_RESULT=pass   L5_RESULT=pass
# GATE_EXIT=0
# Full package reference: tucnak/4.67#ceb8553a99b33c4ab62351bf1dd37fe3:98f347dcf321956504d75721b6275954954bb9f8#4c2d1a1cd0ada3696f6f9799cd49ec62
# bin/tucnak sha256: 1b8a13c4d008d2f3479c13635d978af807a78ad4d6cd74410740dd5532687073
```

- `conan create` rc=0；`test_package` 的 3 条断言通过：`bin/tucnak` 存在 + AArch64 ELF
  (magic + `e_machine=183`)；`tucnak --version` banner 含 4.67 的运行断言在 aarch64 worker 执行。
- L1e 破坏性反向验证通过：移走 `bin/`、`lib/` 后测试确实失败 → 测试实质依赖被测包（非空壳）。
- 平台 CI：**build #85524 pass**（head `7e3856d83d`，worker CI-008，2026-10-12 05:05–05:12）。
  历史红：#85140/#85246/#85283/#85303（问题 7）、#85444（问题 9）、#85454（问题 8）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/tucnak` | 主程序（AArch64 ELF，`e_machine=183`，仅 NEEDED `libc.so`） |
| `bin/soundwrapper` | 音频包装程序 |
| `lib/tucnak/tucnak.d` | tucnak 模块描述 |
| `share/tucnak/` | `cty.dat`、`titlpage.html`、`tucnakrc` 及 `tucnakvexc*`/`tucnakwiz` 等数据文件 |
| `share/applications/tucnak.desktop` | 桌面入口 |
| `share/pixmaps/tucnak.{png,xpm}`、`share/tucnak/doc/{NAVOD.pdf,NAVOD.sxw,AUTHORS,ChangeLog,TODO}` | 图标与文档 |
| 合计 | `package()`：Packaged 24 files |

## 注意事项

1. **不要预跑 `intl/gen-intl`**：真机 `cat` 无 `-n`，残缺 `language.h` 会静默覆盖 tarball 预置完整版
   → 满屏 `T_*` 未声明（问题 8）。tarball 预置的 `src/{language,txts}.{h,inc}` 已够用。
2. **不要预跑 `intl/fixlang.pl`**：它就地改写 `.lng` 文件，使其新于 `src/language.inc`，反而迫使
   `make` 重跑 intl 规则。
3. **只预跑 `data/font2inc.pl`**（`perl font2inc.pl`，走 PATH perl），因为只有 `src/fonts.{h,inc}`
   是构建期生成、其规则经 shebang `#!/usr/bin/perl -w` 执行（问题 7）。
4. tucnak 的 `--host` 必须用**不带 `-ohos`** 的 gnu 拼写（问题 5）；libzia 用准确三元组。
5. **不要断言 `tucnak --help`**：上游用 getopt `":c:dgh:ikmst?x"`，`h` 带参数，`--help` 会把 `elp`
   当 home 目录导致 core dump。只断言 `--version`（getopt 命中 `i`/`s` 走 info banner）。
6. 判「修复无效」前先比对失败日志的 RUN 行/行号与当前配方，防旧 head 竞态（问题 9）。
