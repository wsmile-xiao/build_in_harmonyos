# xdelta 1.1.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（配方已完成，真机预检待 HMBS 后台执行）

## 编译步骤

```bash
cd archives/x/xdelta/1.1.3/
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方流程（conanfile.py）：AutotoolsToolchain 生成 configure 参数
（OHOS 真机为原生构建，不手工传 --build/--host，由 Toolchain 按 profile
原生模式生成；静态库），
PkgConfigDeps + AutotoolsDeps 双生成器提供 pkg-config 与 CPPFLAGS/LDFLAGS，
`generate()` 末尾做 CONFIG_SHELL 存活探测并覆盖 profile 值，
`Autotools.configure()` → `make -j1` → `make check -j1` →
显式执行上游测试 `test/xdeltatest` 并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记 →
`make install`，删除 `*.la`/`*.dylib`，安装 `COPYING` 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游源码 URL 与校验值无法在本机直接下载验证（SourceForge/ Debian 镜像返回 403） | 本机 Windows 网络受限 | 采用 Debian `.dsc` 官方元数据中的 pristine-upstream sha256（`f1c9c40a…ff94eddf`，242101 字节，与 SourceForge 242.1 kB 一致）+ MD5 交叉核对；conan 在真机下载时会自动校验，不一致会快速失败 |
| 2 | 上游 `configure.in` 为 2001 年版本，`config.sub` 可能不识别 aarch64 | 年代久远的三元组 | 先按 a52dec 成例固定 `--build/--host`；若真机 configure 报 `config.sub` 无法识别，下一轮追加 `config.sub` 更新补丁（POSIX 兼容方式，不引入平台宏） |
| 3 | 上游测试未接入 `make check` | `test/Makefile.am` 只定义 `noinst_PROGRAMS`，无 `TESTS` | 配方在 `build()` 中显式查找并执行 `test/xdeltatest`，用真实退出码生成 `HMBS_UPSTREAM_TEST_RESULT`（discovered=1，即上游唯一的测试程序） |
| 4 | `xdelta delta` 的退出码 1 表示“发现差异”，不是失败 | man 页 RETURN VALUES 约定 | 测试脚本把 delta 的 0/1 视为成功，仅 2 判失败，并额外断言产物非空 + patch 重建后逐字节一致，杜绝空文件比空文件的假通过 |
| 5 | zlib 对齐到 1.3.1.1 后图冲突消失，但依赖走源码构建，libffi configure 报 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127） | profile 的 CONFIG_SHELL 指向 hnp bash，而该 worker 缺失此路径；configure 重 exec 缺失解释器 | 换策略：版本号保持对齐，改从构建链路 hardening——① 补 `AutotoolsDeps` 生成器，让传递头库经 CPPFLAGS/LDFLAGS 到达 configure；② `generate()` 在真机上探测可执行 shell 并覆盖 CONFIG_SHELL（配方 buildenv 优先于 profile）；③ test_package 同样做 shell 存活探测；④ 上游测试执行加 `env="conanrun"`，共享库依赖可加载 |
| 6 | 上轮 hardening 只覆盖本包，libffi 仍以相同 Error 127 失败（第三方包构建不受本配方 buildenv 影响） | 图计算出 static glib → 全链源码构建；libffi 源码构建在缺 bash worker 上必死 | 再换策略：依赖选项对齐已发布二进制——`configure()` 置 `glib shared=True`（ohpcd glib/2.84.0.1 二进制即 shared），使其 STATIC 子依赖（libffi/pcre2）被标 skipped、无需构建；xdelta 自身保持静态，CLI 经 conanrun 加载共享 glib |
| 7 | 强制 glib shared=True 后，真机仍以同一 libffi Error 127 失败（第二策略周期：上一周期三次尝试连续未通过，换根因假设与实现路线） | 上一周期"static glib 展开全链源码构建"的假设是错的：仓库内 glib/2.88.0.1 配方已证实 libffi 在 OHOS 制品仓无可用二进制（"not published in the registry"，故内建为 meson subproject），任何含外部 libffi 节点的图在缺 bash worker 上必倒——与 shared 取值无关；强制 shared 反而偏离已发布二进制 | 改用 glib/2.88.0.1（libffi 内建，无外部 libffi 节点；pcre2/10.45 published、zlib/1.3.1.1.1.1 built 且为 makefile 构建不依赖 bash；xdg-dbus-proxy/0.1.7 同一闭包已在真机 built）；zlib 直依赖同步为 1.3.1.1.1.1 与 glib pin 一致；撤销 shared 强制；glib 要求加 transitive_headers/libs（xdelta.h 引用 glib 类型，下游自动继承） |
| 8 | 真机 configure 报 `C compiler cannot create executables`（gcc 探测为 `/data/service/hnp/bin/clang`，随即存活检查 no） | 初判为配方硬编码 `--build/--host=aarch64-unknown-linux-gnu` 把原生构建伪装成交叉构建；删除后复检仍以同一方式失败，该假设被证伪（见 row 9） | 删除手工 `--build/--host`（由 AutotoolsToolchain 按 profile 原生模式生成；该清理本身正确并保留）；`build()` 中 configure 失败时转储 `config.log` 尾部 60 行供下轮定位；test_package/MANIFEST.yml 补 `upstream_tests_exist/total/count_method/audit` 门禁字段 |
| 9 | 删除 triplet 后复检仍失败，但本轮转储的 `config.log` 给出真因：`configure[1087] exec /data/service/hnp/bin/clang` 报 `inaccessible or not found`——profile 的编译器路径在预检沙箱内根本不可执行（与此前 libffi 轮 `/data/service/hnp/bin/bash: inaccessible or not found` 同一模式） | profile `tools.build:compiler_executables` 指向的 hnp clang 在预检沙箱不可 exec；`Autotools.configure()` 沿用该坏值，存活检查必然失败；与 triplet/flags 无关 | 按 kyoto-tycoon 先例运行时探活：`generate()` 新增 `_probe_shell/_probe_compiler`（候选逐个执行版本命令实测，顺序 profile 值→环境值→hnp 固定路径→OHOS SDK llvm→PATH），命中则写入配方 buildenv 覆盖 profile；`build()` 重探活并以内联 `CC/CXX/CONFIG_SHELL` 前缀手工执行 configure（configure 参数仍经 `load_toolchain_args` 取 Toolchain 生成值），`make` 命令行追加同一 `CC/CXX` 透传子 make；未命中则保留原值并告警，让失败保持可见 |
| 10 | 预检 `generate()` 直接崩溃：`Error in generate() line 105 cc = self._probe_compiler("c") / ConanException: [conf] 'tools.build:compiler_executables:c' does not exist` | `_probe_compiler` 用逐语言后缀键 `tools.build:compiler_executables:c/cpp` 取 profile，但该 conf 在 conan 2.30 的合法名是 dict 型 `tools.build:compiler_executables`（profile 写法 `={"c": "...", "cpp": "..."}`，x264/xeyes/xtrans 均按 dict 取）；带后缀的键不在配置表内，`check_type=str` 直接抛异常，与编译器是否可执行无关 | 新增 `_conf_compiler(key)` 按 dict 读取（`check_type=dict`，异常/非 dict/空值一律返回 None），`_probe_compiler` 改调它取 `c`/`cpp`；其余探活顺序不变，未命中仍保留 Toolchain 默认并告警 |
| 13 | 真机推进到 `ltconfig: you must specify a host type if you use `--no-verify'` → `configure: error: libtool configure failed`（config.guess 行首锚定修复已生效，host/build 检查通过） | 旧 autoconf 不检查 `config.sub` 退出码：1999 年版 config.sub 根本不认识 `aarch64`/`x86_64` CPU，巨型 machine case 直落 `*) Invalid`、stdout 为空，`$host` 为空串一路传到 `ltconfig --no-verify` 才报错；此前三处 `linux-ohos` 修改只覆盖 OS 维，未覆盖 CPU 维 | `_patch_config_for_ohos` 加第 4 步：按文件自身惯例（`arm` 裸名与 `arm-*` 并存）给裸 CPU 表加 `aarch64 \| x86_64`、带厂商表加 `aarch64-* \| x86_64-*`，锚定整行且 `count==1` 才替换；本地对官方 tarball 仿真四种三元组：`aarch64-unknown` 走新增 `aarch64-*`、`x86_64-unknown` 走新增 `x86_64-*`、`arm-unknown` 走既有 `arm-*`、`i686-unknown` 走既有 `i[34567]86-*`，OS 白名单与直通段全命中，下游默认 OS/厂商段经核对不改写 |
| 12 | 真机 configure 中断：`config.guess[224]: syntax error: unexpected '*:HarmonyOS:*:*'`（本轮预检，编译器存活检查已过） | `_patch_config_for_ohos` 用子串 `*:NetBSD:*:*)` 做 `str.replace`，命中 `atari*:NetBSD:*:*)`（真实 224 行）并将其撕成 `atari` + 新分支，shell 解析失败；通用 `*:NetBSD`（真实 596 行）根本没被触及 | 改用行首锚定正则 `^[ \t]*\*:(NetBSD\|FreeBSD):\*:\*\)` 定位通用分支（优先 NetBSD、回退 FreeBSD），按偏移插入；删除 `patches/` 下两个静态 diff（上下文已被证伪且 `conandata.yml` 无 `patches` 声明，运行时锚定编辑是唯一补丁通道）；本地用官方 tarball 仿真验证：旧逻辑复现 224 行撕裂、新逻辑落点 596 行且 `atari` 行完整、嵌套 `case/esac` 各 +1 平衡，`config.sub` 三处落点不变 |
| 11 | 真机 configure 中断：`checking host system type... configure: error: can not guess host type; you must specify one`（config.log 证实编译器存活检查已过，`gcc=/harmonybrew/bin/clang` 可执行） | 上游随包的 1999 年版 `config.guess` 无 HarmonyOS 分支（`uname -s=HarmonyOS` 无法映射，E007）；`config.sub` v1.1 无 `linux-ohos` 三元组概念（无 `android-linux`/`linux-uclibc` 锚点，E007 通用脚本 3 处 `config.sub` 修改全部 warn）。此前 `--build/--host` 绕过已按 E007 禁令删除，不恢复 | 按 E007 路线以 POSIX 补丁解决（零平台宏，PF5 干净）：① `patches/0001` 在 `config.guess` 的 `*:NetBSD` 前插入 `*:HarmonyOS` 分支，输出 `aarch64-unknown-linux-ohos`——用旧脚本的 `echo+exit 0` 风格而非新脚本的 `GUESS=` 风格（含 `UNAME_MACHINE` 归一化）；② `patches/0002` 在 `config.sub` 做三处兼容 1999 结构的修改（`KERNEL-OS` 切分接受 `linux-ohos*`、`-linux-ohos*` 进 OS 白名单、`-linux-ohos*` 直通避免被重写为 `linux-gnu`）；`build()` 首行的 `apply_conandata_patches` 自动落地，无需改 configure 调用 |

| 14 | 真机 configure 止于 `checking for GLIB - version >= 1.2.8` → `configure: error: Test for GLIB failed`（host/build 检查与编译器存活检查均已过，前三周期假设被证伪） | 上游 `configure.in` 用 `AM_PATH_GLIB(1.2.8)` 经 `glib-config`（glib1 工具）取值，而配方提供 glib2（无 glib-config，只有 pkg-config glib-2.0），`AC_PATH_PROG(GLIB_CONFIG, glib-config, no)` 恒为 no；与 triplet/config.sub/编译器路径无关 | 新增 `_write_glib_config_shim()`：真机上落盘 POSIX sh 垫片 `glib-config`，`--cflags/--libs/--version` 转给 `pkg-config glib-2.0`（`gmodule/gthread` 映射 `*-2.0`，`pkg-config→pkgconf` 回退），`generate()` 经 buildenv 注入 `PATH+GLIB_CONFIG`，`build()` 重建垫片并内联进手工 configure 命令；源码实际只用 glib 通用类型（`edsio.h` 的 `<glib.h>` + gint/guint/gboolean/GHashTable，`library.c` 的 gmodule 调用在 `#if 0` 内禁用），glib2 头库兼容，版本 2.88>=1.2.8 自然通过 |

| 15 | 上轮静态垫片已上线仍以同一指纹失败：config.log 的 AM_PATH_GLIB 测试程序出现空版本字面量 `if ((glib_major_version != ) \|\| ...)`，即 `$GLIB_CONFIG --version` 在真机输出为空，测试程序连编译都过不了 → `no_glib=yes` → `Test for GLIB failed`（build() line 322 证实新代码已运行，非同步滞后） | 第一路线“垫片运行时转调 `pkg-config --modversion glib-2.0`”在真机 pkg-config 发现链上无输出（可执行文件/PKG_CONFIG_PATH/.pc 命名任一环节皆可致空，远端无法区分）；空值经 sed 后全空，属运行时发现脆弱，非 flag 内容错误 | 换第二路线零运行时发现：① 新增 `_write_glib_config_static()`，在真机上从 `self.dependencies["glib"]` 聚合 cpp_info（`aggregated_components()`，失败则手工合并 root+components）直接烘焙 `-I/-D/-L/-l` 与依赖版本号，单引号转义后写入静态 `glib-config`；② `tc.configure_args` 追加 `--disable-glibtest`（宏自带 `AC_ARG_ENABLE(glibtest)` 逃生舱，跳过编译运行测试，此时 --version 仅显示用）；PATH+GLIB_CONFIG 注入与手工 configure 内联保持不变 |

| 16 | 真机编译止于 `libedsio/library.c` → `edsio.h:488:8: error: redefinition of '_GQueue'`（glib `gqueue.h:49` 已定义同名结构体） | xdelta 1.1.3 自带 glib1 时代的 GQueue 兼容实现（`edsio.h` 的 `struct _GQueue` + `g_queue_*` 声明与宏、`edsio.c` 尾部的同名实现），与配方提供的 glib2（`glib/2.88.0.1`）头文件直接冲突；与 configure/triplet/编译器探活无关 | 新增 `patches/0001-glib2-gqueue.patch`（Debian #490257 / Gentoo `xdelta-1.1.3-glib2.patch` 同路线）：① 删除 `edsio.h` 的整段 `/* Missing glib stuff */` 兼容块；② 删除 `edsio.c` 尾部的同名本地实现；③ 三处调用点切到 glib2 API（`g_queue_get_size→g_queue_get_length`、`g_queue_push→g_queue_push_tail`、`g_queue_pop→g_queue_pop_head`，`g_queue_new/free` 沿用 glib2 原生实现）；`conandata.yml` 声明该补丁，`source()` 新增 `apply_conandata_patches` 落地；已核对全源码树旧符号仅存于被删块内（`g_list_free_1` 仅出现在被删实现中），无残留引用 |

| 17 | 真机编译在 GQueue 修复后止于 `libedsio/default.c:297`：`{ long x = source->alloc_buf; ... }` 报 2 个 `error: incompatible pointer/integer conversion [-Wint-conversion]`（新版 clang 默认把该警告当错误） | 上游 1999 年代码假设指针可隐式存入 `long`；OHOS aarch64 虽为 LP64（`long` 足够宽），但新 clang 禁止隐式指针↔整数转换；与 GQueue 补丁无关，是同一 32 位时代代码在新工具链下的下一处硬错误 | 新增 `patches/0002-64bit-pointer-cast.patch`（Arch 上游 `intptr_t` 精修路线）：① `default.c` 补 `#include <stdint.h>`；② 该行改用 `intptr_t x = (intptr_t) source->alloc_buf; … = (void *) x;` 显式转换；已全源码树扫描确认这是唯一隐式指针↔整数转换点（`default.c:313` 的 `(long)ret` 为显式转换，不触发；其余 `long` 均为真实整数用途），`(*ptr) = buf` 两处仅为 signedness/qualifier 警告，不阻断构建 |

| 18 | 真机编译在前两补丁后止于 `xdmain.c:1444:24: error: static declaration of 'xd_handle_table' follows non-static declaration`（前置声明在 67 行） | 同一文件 67 行用 `extern` 前置声明、1444 行用 `static` 定义该表，新版编译器拒绝同一符号先 extern 后 static；与 glib/64 位补丁无关，是 2001 年代码在新工具链下的下一处硬错误 | 新增 `patches/0003-xdmain-static-table.patch`（Debian #297844 修法）：把 67 行前置声明改为 `static`，与 1444 行定义一致；已全源码树核对该符号仅在 `xdmain.c` 内使用（561/761 行取地址），无跨翻译单元引用，改 static 不影响链接 |
| 19 | 三处编译补丁生效后 link 阶段止于 `No rule to make target '.../b/libedsio/libedsio.la', needed by 'xdelta'`（make[2] 在 build-release 内直接失败，无子目录构建错误；与编译器无关） | 上游 2001 年 in-source 假设：顶层 `Makefile.am` 用 `$(top_srcdir)/libedsio/libedsio.la` 引用构建树产物（`test/Makefile.am` 另有两处 `$(top_srcdir)/*.la`），Conan 异地构建下 .la 落在 build 树而顶层 Makefile 去 source 树找，必然失配（Cygwin 移植曾把同一行改为 builddir 相对路径）；上一周期三补丁有效（预检日志确认 3 个补丁导出应用，错误由编译期推进到 link 期），非假设无效而是同一构建的下一阶段错误 | 新路线（构建系统修复，非编译补丁）：`build()` 新增 `_patch_vpath_for_out_of_tree()`，把 `$(top_srcdir)/*.la` 字面替换为 `$(top_builddir)/*.la`；同步改 `Makefile.in`（真机无 automake，configure 实际实例化的是 .in，单改 .am 无效）与 `Makefile.am` 保持一致；`$(top_builddir)` 对 in-source/VPATH 双兼容；幂等，未命中则告警而不静默跳过 |
| 20 | 上轮 VPATH（.la）修复生效后构建推进到 `test/`，止于 `xdeltatest.c:49: fatal error: 'xdelta.h' file not found`（编译行仅有 `-I. -I<srcdir>/test -I.. -I<srcdir>/libedsio`，无 srcdir 顶层包含路径；与编译器无关） | `test/Makefile.am` 的 `INCLUDES` 缺 `-I$(top_srcdir)`（xdelta.h 位于 srcdir 顶层，VPATH 下 `-I..` 指向 build 顶层无此头；同为 2001 年 in-source 假设，Cygwin 移植把同一行改为 `-I$(top_srcdir)/libedsio -I$(top_srcdir)`）；上一轮 `.la` 改 builddir 方向的策略有效（No-rule 消失、顶层与 lib 库已建成），本轮是反方向缺口，需补 srcdir 包含路径而非改 builddir 引用 | 同一 `_patch_vpath_for_out_of_tree()` 内加第二段：以 `INCLUDES` 行首锚定、正則确认无独立 `-I$(top_srcdir)` 令牌后追加该 flag；`Makefile.in` 与 `Makefile.am` 同步改；幂等，未命中告警 |

## 上游测试审计

- 上游存在测试（`upstream_tests_exist: true`）：Debian 源码树含 `test/` 目录，
  内有 `test/xdeltatest.c`、`test/README.test`、`test/Makefile.am`；
  jmacd/xdelta 的 v3.1.0→v3.2.0 清理提交明确列出
  `xdelta1/test/xdeltatest.c (681 lines)`、`xdelta1/test/Makefile.am`、
  `xdelta1/runtest`，证明 1.1.3 时代即自带该测试程序。
- `test/Makefile.am` 把 `xdeltatest` 编译为 `noinst_PROGRAMS`，
  链接 `libxdelta.la` + `libedsio/libedsio.la` + `-lz` + `$(GLIB_LIBS)`，
  即对被测库的实质调用。
- Debian 打包补丁 `test/xdeltatest.c (4 行，fix ftbfs on hurd)` 证明该测试会被实际编译。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.88.0.1 | 仓库内配方（meson；libffi 内建为 subproject，闭包内无外部 libffi 节点；xdg-dbus-proxy/0.1.7 同一闭包已在真机 built） |
| zlib | 1.3.1.1.1.1 | 仓库内配方（makefile 构建，不依赖 hnp bash；与 glib/2.88.0.1 的 pin 严格一致，避免图冲突） |

xdelta 1.1.3 原始依赖 glib1.2，Debian 已在 1.1.3-9 时代将其移植到
glib2.0（`configure.in: fix glib linking` + pkg-config 查找），
本配方沿用该路线，依赖 glib2（本版取 glib/2.88.0.1，glib2 API 向后兼容）。

## 验证结果

```bash
# 真机预检由 HMBS 后台执行，本轮为未提交工作树，未执行真机。
# 预期验证命令（conan create 日志）：
#   make check（上游 harness，无 TESTS 时为 no-op 成功）
#   test/xdeltatest（上游唯一测试程序，退出码 0=通过）
#   bash test_xdelta.sh（4 项消费者 CLI 功能测试 + HMBS_TEST_PACKAGE_RESULT 标记）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/xdelta | 差分命令行工具 |
| lib/libxdelta.a | 差分核心库（静态） |
| lib/libedsio.a | 可扩展 DSIO 库（静态） |
| include/xdelta.h | 公共头文件 |
| lib/pkgconfig/xdelta.pc | pkg-config 文件（上游自带 xdelta.pc.in） |

## 注意事项

- 本配方默认静态库（`shared=False`）：libxdelta/libedsio 非系统同名库，
  静态可避免旧 libtool `.la` 在 OHOS 上的安装问题；CLI 工具不受影响。
- 测试全部使用任务独立 `TMPDIR` 下的临时目录，不污染 `/tmp`。
- 后续若真机 configure 失败，优先补 `config.sub` 三元组识别补丁；
  若 `test/xdeltatest` 需要参数或输出断言格式特殊，按真机日志调整解析。
- 待观察（非本轮改动域）：本轮 `config.log[1087]` 的链接命令含 `-lffi` 与
  pcre v1 的 `-I/-L`（`.../p/pcre23869309333782/...`），与“glib/2.88.0.1 闭包
  内无外部 libffi”假设矛盾——预检实际解析的 glib 修订版可能来自与笔记假设
  不同的 remote/配方。若编译器修复后链接报缺 `-lffi`，下轮核对真机实际解析
  的 glib 修订来源与传递闭包，再定依赖调整，不在本轮盲改。
| 21 | 真机上游测试 `test/xdeltatest` 启动即崩溃：`/scratch/jmacd/source-code-data: No such file or directory` → `WARNING FAILURE` → `Signal 6 (core dumped)`，exit 134（build() line 437→720） | test/xdeltatest.c 把作者私有语料库硬编码为绝对路径（1.1.3 为 `/scratch/jmacd/source-code-data`，后继版本为 `/tmp/big.1`），test1() 首行即 stat/fopen 该路径，缺失则 perror+fail()+abort()；作者注释自认“a real test wouldn't require this configuration”——属环境固件缺失，与被测 delta/patch 功能无关；另上游测试内经 execl("../xdelta") 启动被测 CLI，相对的是子进程 cwd，conan 默认 cwd 为 build 根时会指错位置 | 配方新增 `_provision_upstream_test_data()`（build() 中 VPATH 修复后、make 前调用）：扫描 `test/xdeltatest.c` 的 `cmd_data_source` 字面量，在构建树生成确定性 ~4MiB 固件（固定种子，覆盖 harness 要求的 1.5*(cmd_size+changes*insertion)≈1.6MiB 并留 margin），编译前把字面量重写为固件路径（幂等、字面匹配，未命中告警）；`_run_upstream_test()` 固定 `cwd=dirname(test_bin)` 使 `../xdelta==build/xdelta`，并只记录 diff/gzip 探活供下轮诊断（本轮不改动这些分支）；不断言删减、不跳过 profile |
| 22 | 上轮固件供给生效后复检推进到新失败点：`/tmp/xdeltatest.52286.0: Read-only file system` → `WARNING FAILURE` → abort，exit 134（HMBS 平台诊断 [readonly_tmp]） | 上游 `test/xdeltatest.c` 硬编码 `TEST_PREFIX "/tmp/xdeltatest"` 做暂存文件（含两处 `system("rm -rf " TEST_PREFIX "*")` 编译期字面拼接），而真机 /tmp 只读；与被测功能无关，属平台文件系统子能力限制 | 沿用零断言删减路线（与 row21 不同策略、非重复）：同一 `_provision_upstream_test_data()` 内追加第二段——取 HMBS 注入的可写 `TMPDIR`（回退 build 树），编译前把 `/tmp/xdeltatest` 字面量全量替换为 `$TMPDIR/xdeltatest`，宏与两处 system 拼接点一次性一致；同时修正早退逻辑（fixture 已命中时仍继续处理 TEST_PREFIX）；不断言删减、不跳过 profile |
| 23 | 前两轮修复生效后复检推进到 diff 基准分支：`diff: Unknown option 'rcs'` → `delta command failed` → abort，exit 134（xdelta 自身多组 delta/verify 已跑通，main 按序先跑 xdelta profile 再进 diff/gzip 基准分支） | 上游 `cmd_profiles` 第二项把 `/usr/bin/diff` 以 `--rcs -a` 调用做参照基准；真机自带 diff 非 GNU 实现，不支持该参数；与 xdelta 功能断言无关，属基准参照工具缺失（守则：缺组件必须补齐后再测，不得豁免） | 补齐路线（与 row21/22 不同域、非重复）：① `build_requirements()` 新增 `tool_requires("diffutils/3.12")`（仓库内已适配 application，OHOS built，无构建依赖）；② 供给方法内定位其 `bin/diff` 真实可执行路径，编译前把测试源码 `/usr/bin/diff` 字面量重写为该路径，上游参数与三 profile、全部断言保持原样；未命中则不改并告警；`/bin/gzip` 本轮无损坏证据，保持不动 |
| 24 | CI #52738 link 止于 libedsio/edsiotest: old.lld undefined g_libintl_bindtextdomain/dgettext/textdomain/gettext/dcgettext/dngettext,静态 libglib-2.0.a 引用而 -lintl 明明在链接行 (真机预检 passed,CI 必现,与编译器/config 无关) | 烘焙 glib-config 的聚合顺序把 -lintl 放在 -lglib-2.0 之前 (-lgio-2.0 -lintl -lgthread ... -lglib-2.0),静态左->右一次扫描先丢弃 -lintl,后见 glib 未定义符号时无库可解;另 -lintl 若命中系统真实 libintl 而非 glib 代理 libintl(仅 g_libintl_* 符号) 同样无解 | _write_glib_config_static 内把 -lintl/-lintl_glib 移到旗标末尾并缺省补 -lintl,再在 glib 自身 libdir 优先的已烘焙 -L 使 -lintl 解析到代理 libintl,使生成 Makefiles 携带正确顺序,不新增 gettext 显式依赖避免 SONAME 冲突,不断言删减;刻意不追加绝对路径 libintl.a(预检证实 libtool --mode=link 拒收非 libtool 对象,追加即报 cannot build libedsio.la) |
