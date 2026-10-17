# libcaca 0.99.beta20 适配笔记

## 编译环境

- 构建系统: autotools（dist tarball 自带预生成的 `configure`，autoconf 2.71；`AC_CONFIG_AUX_DIR(.auto)`，只有顶层一个 configure，无 AC_CONFIG_SUBDIRS）
- 平台任务: contrib-8136（libcaca 0.99.beta20），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建（build = host）
- 编译器: clang/clang++ 15.0.4
- 依赖: `ncurses/6.4`、`zlib/1.3.1`（均已发布）；构建期 `cppunit/1.15.1`（tool_requires）
- 上游: https://github.com/cacalabs/libcaca tag `v0.99.beta20`（GitHub API 实证：非 fork、未归档；WTFPL）
- 源码 sha256: `8ad74babc63bf665b0b2378d95b4da65b7493c11bd9f3ac600517085b0c4acf2`（本机与设备实拉逐字节一致）
- 状态: built（G0/G1/G2/G3 全过，test_package 18/18）

## 源码面貌（摸底结论）

- 主体 **C**：92 个 `.c`、8 个 `.cpp`（可选 C++ 绑定）、22 个 `.h`；库本体在 `caca/`（+ `driver/`），头在 `caca/`，工具在 `src/` 与 `tools/`，示例在 `examples/`
- 可选绑定子目录 `cxx/ java/ python/ ruby/ caca-sharp/`——本配方全部关闭，交付物只有 C 库与（默认启用的）C++ 绑定
- configure 选项：`--enable-{kernel,slang,ncurses,win32,conio,x11,gl,cocoa,network,vga,csharp,java,cxx,python,ruby,imlib2,debug,profiling,plugins,doc,cppunit,zzuf}`
- 上游测试面：`caca/t/`，由顶层 `make check` 递归（`caca/Makefile.am: SUBDIRS = . t`）执行 `TESTS = simple check-copyright check-source check-win32 caca-test`；`caca-test` 是 cppunit 套件（canvas 4 + dirty 6 + driver 1 + export 1 = 12 个用例），仅在 `--enable-cppunit` 时构建
- zlib 支持**无法关闭**：`AC_CHECK_HEADERS(zlib.h)` + `AC_CHECK_LIB(z, gzopen, ...)` 无条件自动探测

## 语言判定（R47）

`ohc-run.py lang-preflight` 报 `detected_language=python`（`build_system: setuptools`，依据是 dist 里的 `python/setup.py`）。**该判定不成立**：`python/setup.py` 属于可选 SWIG 绑定子包，项目顶层的构建系统是 autotools（`configure.ac` + `Makefile.am` + 预生成 `configure`），交付物是 C ABI 库 `libcaca`。按 AGENTS.md §1.2「混编项目按主体语言判，主体为 C/C++ 即在范围内」，本库主体是 C（92 个 `.c`），且配方已 `--disable-python/ruby/java/csharp`，构建面不含任何非 C/C++ 语言。工具误判的根因是优先级「manifest > 构建系统 > 源码统计」在 tarball 根目录扫描时命中了绑定子目录的 manifest。

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify libcaca 0.99.beta20 --project-dir "$PWD"
```

配方内 OHOS 分支的关键机器码：`_resolve_shell()`（bash 优先，zsh 兜底）、
`_restore_script_modes()`（E490）、`_relax_umask_in_configure()`、`_configure_args()`、
`_build_environment()`（显式重建 CPPFLAGS/LDFLAGS/LIBS 与 CPPUNIT_CFLAGS/CPPUNIT_LIBS）、
`_run_ohos()`（导出 SHELL/CONFIG_SHELL 并 `< /dev/null`）。因 automake 的
`all-recursive` 依赖 POSIX 词分割，`make` 必须与 configure 用同一个 bash（见下 #5）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `KeyError: 'cppunit' not found in the dependency set` | Conan 2 的 `test_requires` 在配方自身 `generate()` 里不可见（只在 test_package 阶段进入 `self.dependencies`） | 改用 `tool_requires("cppunit/1.15.1")`，`self.dependencies.build["cppunit"]` 即可取到包目录 |
| 2 | `FileNotFoundError: .../libcaca-source.tar.gz`（conan 的 `download()` 内抛出） | 该错误把网络/TLS 失败伪装成"目标文件不存在"，URL 与 HTTP 状态全部丢失 | 配方自实现 `_fetch()`：显式 CA（`certifi.where()` → `$CONAN_HOME/cacert.pem` → `$SSL_CERT_FILE`，找不到 fail-fast）、3 次重试、`.part` 暂存 + 原子改名、sha256 校验。第二次重跑时日志直接给出 `downloaded 1099916 bytes (HTTP 200) from <URL>`，定位成本从"猜"变成"读" |
| 3 | `'Environment' object has no attribute 'save_script'` | `save_script()` 属于 `Environment.vars()` 返回的 `EnvVars`，不属于 `Environment` | `environment.vars(self).save_script(...)` |
| 4 | `configure: error: cannot find ncurses development files`（四个头探测全失败） | conan 生成的 `conanautotoolsdeps.sh` **只被 conan 自己的 `Autotools()` 助手 source**；配方用裸 subprocess 跑 configure 时 conan 不把 build env 写进 `os.environ`（config.log 里 CPPFLAGS 只剩设备环境自带的 `-I<prefix>/include`） | `_build_environment()` 显式重建 `CPPFLAGS/LDFLAGS/LIBS`（ncurses 的 `-I/-L` 与 `-lformw -lmenuw -lpanelw -lncursesw`），设备原有值追加在后 |
| 5 | `zsh:cd: no such file or directory: kernel caca src examples tools cxx caca-sharp python ruby java doc` | **zsh 不对未加引号的变量展开做 IFS 词分割**；automake 的 `all-recursive` 用 `for subdir in $list` 遍历 SUBDIRS，zsh 下整串成为一个单词 | 构建 shell 改为平台 profile 自带的 `/data/service/hnp/bin/bash`（同时满足 `exec 7<&0` 与词分割）；`/system/bin/sh`（toybox）因不支持多位数 fd 重定向仍不可用 |
| 6 | `configure: error: Package requirements (cppunit) were not met: No package 'cppunit' found` | 设备**没有 pkg-config**；`PKG_CHECK_MODULES([CPPUNIT], [cppunit])` 因此失败 | 导出 `CPPUNIT_CFLAGS`/`CPPUNIT_LIBS`：该宏在 `$CPPUNIT_CFLAGS` 非空时短路，根本不会调用 pkg-config（configure 自己的报错文案即提示此路），无需引入 pkgconf |
| 7 | `common-image.c:164: incompatible integer to pointer conversion assigning to 'char *' from 'int'` | 上游缺陷：`src/common-image.c` 调用返回指针的 `_caca_alloc2d()` 却未包含声明它的 `caca/caca_internals.h`；C99 起隐式声明按 int 处理返回值，64 位目标上指针被截断（上游 GCC 只 warning，clang 15 的 `-Wint-conversion` 是 error） | 补丁 0001：补上 `#include "caca_internals.h"`（`AM_CPPFLAGS` 已含 `-I$(top_srcdir)/caca`，无需改构建文件） |
| 8 | `ld.lld: error: duplicate symbol: move`（`conio.o:(move)` × `lib_gen.o in libncursesw.a`） | 上游缺陷：示例 `examples/conio.c` 定义文件作用域数组 `int move[X_BOARD]`，与 ncurses 为宏函数生成的真实符号 `move` 撞名；启用 ncurses 后端即冲突 | 补丁 0002：改为 `static int move[...]`（`grep -rn '\bmove\b' examples/*.c` 实证除 conio.c 自身外无引用，语义等价） |
| 9 | test_package 链接 `undefined symbol: gzgets / gzopen` | libcaca 的 `caca/file.c` 用 zlib 流函数，而 zlib 支持自动探测且无法关闭；配方未声明 zlib，设备自身 prefix 下的 zlib.h 让 configure 打开了该支持，静态 `libcaca.a` 因此带上无人解析的 `-lz` | 声明 `requires("zlib/1.3.1")`，把 `-I/-L/-lz` **前置**注入（压过设备自身 prefix 的头），并在 `package_info` 的 `caca` 组件里 `requires = ["zlib::zlib"]` 向消费者传播 |
| 10 | `CMake.test() got an unexpected keyword argument 'output_on_failure'` | Conan 2.29 的 `CMake.test()` 无该参数 | 改 `cmake.test()`；另接一条 `self.run(<binary>, env="conanrun")` 直接跑消费者程序，把 18 项断言逐条打进日志当证据 |
| 11 | `Cannot load recipe ... conanfile.py not found`（export 段整段消失） | 设备上有**两个** `agent_worker.sh` 同时轮询同一 mailbox，同一 job 被并发执行两次；两个 `conan create` 并发导出同一 recipe，后者覆盖前者的缓存目录，留下"已登记 revision 但目录缺失"的残留 | 任务脚本首行加 `mkdir` 互斥锁；被污染的缓存条目用 `conan remove "libcaca/*" -c` 清掉再重跑（清出 3 个残留 revision） |

## 源码修改

2 个补丁（均为上游真实缺陷，语义等价修复）：

1. `patches/0001-src-common-image-declare-caca_alloc2d.patch` —— `src/common-image.c` 补 `#include "caca_internals.h"`，让 `_caca_alloc2d()` 是声明而不是隐式 int 返回（64 位指针截断 UB）。
2. `patches/0002-examples-conio-static-move.patch` —— `examples/conio.c` 的 `move` 状态表加 `static`，消除与 ncurses `move()` 的重复符号。

其余 11 项问题均在构建期机器码内解决，未改动上游源码。

## 依赖版本

- `ncurses/6.4`（终端后端；头 `include/ncurses.h`，库 `libncursesw/libpanelw/libmenuw/libformw`）
- `zlib/1.3.1`（`caca/file.c` 的 gz* 流层；由 `package_info` 向消费者传播）
- `cppunit/1.15.1`（tool_requires，仅构建期跑上游 caca-test）

## 验证结果（设备实机实测，2026-09-14）

上游套件（配方 `build()` 内 `make -j1 check` 执行，比上游 CI 只跑 `./configure && make` 更强）：

```text
Making check in t
PASS: simple
PASS: check-copyright
PASS: check-source
PASS: check-win32
PASS: caca-test
Testsuite summary for libcaca 0.99.beta20
# TOTAL: 5
# PASS:  5
# FAIL:  0
```

消费者测试（test_package，ctest 与直接执行双跑）：

```text
1/1 Test #1: test_libcaca .....................   Passed    0.03 sec
100% tests passed, 0 tests failed out of 1

ok 1 - caca_get_version() reports 0.99.beta20
ok 2 - caca_create_canvas(40, 20) returns a canvas
ok 3 - canvas width is 40
ok 4 - canvas height is 20
ok 5 - caca_put_str places 'l' at (1,1)
ok 6 - caca_put_str places 'a' at (7,1)
ok 7 - foreground attribute round-trips as white
ok 8 - drawing marks at least one dirty rectangle
ok 9 - caca_export_canvas_to_memory("caca") produces a payload
ok 10 - caca_get_export_list() lists at least one codec
ok 11 - second canvas created for re-import
ok 12 - caca_import_canvas_from_memory succeeds
ok 13 - re-imported canvas keeps width 40
ok 14 - re-imported canvas keeps height 20
ok 15 - re-imported canvas keeps the text content
ok 16 - caca_create_dither(32bpp RGBA) succeeds
ok 17 - caca_dither_bitmap returns 0
ok 18 - dithered bitmap writes characters into the canvas
1..18
# 18 checks, 0 failures
```

门禁：G0 PASS、G1 PASS、G2 PASS、G3 PASS，`✅ 配方验证通过: libcaca 0.99.beta20`。

## 已知噪音（不影响结论）

- `make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo*: Operation not permitted`：hmdfs 不支持 make 的 jobserver fifo（E549 同族），make 退化为无 jobserver 仍正常并行/串行完成。
- `id: bad uid 20020100`、`configure:test: integer expression expected: unknown`：设备 uid 未在 /etc/passwd 中登记导致的既有噪音，与配方无关。
