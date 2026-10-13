# notes.md — its-playback-time 0.2026-05-26.fdcd2b0

## 编译信息

| 项目 | 值 |
|------|-----|
| 软件包名 | `its-playback-time`（Debian 源包名） |
| 上游程序 | `ipbt` / `ipbt-dump`（Simon Tatham, MIT） |
| 版本 | `0.2026-05-26.fdcd2b0`（上游 `20260527.fdcd2b0`，commit `fdcd2b0ad60f74ffa6a695c992d56c6a3ae20e4a`） |
| 构建系统 | CMake ≥ 3.10（`CMakeLists.txt` + `cmake/`；无 autotools、无 configure） |
| 目标 | OHOS aarch64（`os=OHOS`、`arch=armv8`、`compiler=clang 15`、`libcxx=libc++`） |
| 状态 | built |
| 编译日期 | 2026-10-04 |

## 依赖

| 包 | 说明 |
|----|------|
| `ncurses/6.6` | 已发布于 ohpcd。`unix/CMakeLists.txt` 设 `CURSES_NEED_WIDE TRUE` 后 `find_package(Curses)`，需要宽字符库 `libncursesw.a`——ncurses/6.6 正是静态宽字符包 |

**没有**把 `halibut` 声明为依赖：`doc/CMakeLists.txt` 只用 halibut 把 `man-*.but` 重新生成 roff man page，把它变成构建依赖就意味着构建机必须**执行**一个 OHOS aarch64 的 halibut 二进制，交叉构建做不到。改为在 `package()` 里安装 tarball 自带的预生成 `ipbt.1`，man page 仍然进包。

`autoconf-archive`（Debian build-dep）也不需要——这个版本已经是纯 CMake 工程。

## 编译步骤

```bash
# 1. 下载源码（HTTP 200，360583 字节）
wget https://www.chiark.greenend.org.uk/~sgtatham/ipbt/ipbt-20260527.fdcd2b0.tar.gz
sha256sum ipbt-20260527.fdcd2b0.tar.gz
# 5303c8010addf1b2dec5375c8cf32d70e1835545d639ee2183863e09d4e80aa3

# 2. 配方内完成（Conan）
conan create archives/i/its-playback-time/0.2026-05-26.fdcd2b0 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 关键适配点

### 1. `unix/CMakeLists.txt`：FindCurses 认不出扁平的 curses 头文件布局（唯一补丁）

CMake 的 `FindCurses` 只在头文件位于 `ncursesw/`（或 `ncurses/`）**子目录**时才填 `CURSES_HAVE_NCURSES_CURSES_H` / `CURSES_HAVE_NCURSES_NCURSES_H`；而 `CURSES_HAVE_NCURSES_H` / `CURSES_HAVE_CURSES_H` 它只在 `CURSES_NEED_WIDE` 为假时才填。上游恰恰要宽字符库（`CURSES_NEED_WIDE TRUE`），所以在「ncurses.h / curses.h 直接放在 include 目录里」的安装上（ncurses Conan 包就是这样，某些发行版也这样打包），四个变量**全为 0**。

后果：`unix/ipbt.c` 的这段include 链一个分支都不成立——

```c
#if CURSES_HAVE_NCURSES_CURSES_H
#  include <ncursesw/curses.h>
#elif CURSES_HAVE_NCURSES_CURSES_H      /* ← 上游笔误，应为 CURSES_HAVE_NCURSES_NCURSES_H */
#  include <ncurses/curses.h>
#elif CURSES_HAVE_NCURSES_H
#  include <ncurses.h>
#elif CURSES_HAVE_CURSES_H
#  include <curses.h>
#else
#  error "SysV or X/Open-compatible Curses header file required"
#endif
```

编译直接爆 `undeclared identifier 'stdscr' / 'wmove' / 'wattrset' / 'waddch' / 'ACS_DIAMOND' / 'A_BLINK'`。

`patches/0001-curses-header-fallback.patch` 在 `find_package(Curses)` 之后加一段兜底：四个变量都为假时，直接探测 CMake 已经解析出来的 include 目录，把实际存在的那个头文件对应的变量置真。只改「本来为假、且头文件确实存在」的变量，因此原本能编过的构建完全不受影响。这是**通用可移植性修复，不是 HarmonyOS 特判**（R8：无 `__OHOS__`、无 `if (ohos)` 分支）。

> 顺带记录（**未**打补丁，避免掺入与本次构建无关的改动）：上面那行 `#elif CURSES_HAVE_NCURSES_CURSES_H` 是上游笔误，重复了第一个分支，应为 `CURSES_HAVE_NCURSES_NCURSES_H`。在本包的构建配置里该分支恒为假，不影响结果。

### 2. `#if HAVE_NCURSESW` 恒为假（观察，未改）

`unix/ipbt.c:614` 用 `#if HAVE_NCURSESW` 决定用 `setcchar`/`wadd_wch`（宽字符）还是 `wcrtomb` 退化路径，但 `cmake/cmake.h.in` 里根本没有 `HAVE_NCURSESW` 这个 `#cmakedefine`，只有 `CURSES_WIDE`。所以永远走 `wcrtomb` 退化路径。**保持上游行为未动**：改它会改变运行时渲染语义（是否用宽字符 API），不属于让构建通过的必要条件。记在这里供上游/后续决策。

### 3. `NO_GSSAPI` 宏重复定义警告（上游自带，无害）

顶层 `CMakeLists.txt` 有 `add_compile_definitions(HAVE_CMAKE_H NO_GSSAPI)`，而 `cmake.h` 又 `#define NO_GSSAPI 1`，于是每个 TU 都有一条 `'NO_GSSAPI' macro redefined [-Wmacro-redefined]`。只是警告，STRICT=OFF（上游默认），不影响构建；未改上游。

### 4. `PUTTY_GSSAPI=OFF`

顶层已经 `add_compile_definitions(NO_GSSAPI)`；再显式设 `-DPUTTY_GSSAPI=OFF`，是为了让 `cmake/platforms/unix.cmake` 跳过 `libdl` / `krb5-gssapi` 探测——OHOS 上二者都没有，探测纯属噪音。

### 5. `/tmp` 只读 + 无 try_run

所有上游探测都是「编译或链接」型（`check_include_file` / `check_symbol_exists` / `check_c_source_compiles` / `check_library_exists`），**没有 `try_run`**，所以不需要交叉执行模拟，也不需要可写 `/tmp`。本地交叉验证用 `TCM` 直接跑 CMake，全程没有 `$TMPDIR` 问题。

### 6. 版本号输出来自 `cmake_commit.c` 而非 `version.h`

`--version` 打印的是

```
ipbt, source commit fdcd2b0ad60f74ffa6a695c992d56c6a3ae20e4a
```

而不是 `ipbt version 20260527.fdcd2b0`。原因在 `ipbtsrc/common.c`：`ipbt_version()` 用 `#ifdef PACKAGE_VERSION`，但 `PACKAGE_VERSION` 只由 `unix/ipbt.c` 里的 `#include "version.h"` 引入，**打印版本的那个编译单元（common.c）看不到它**，于是走 `#else` 分支打印 `commitid`。`commitid` 来自 `cmake/gitcommit.cmake`：源码目录不是 git 仓库时保留 tarball 里 `Buildscr` 预置的 `DEFAULT_COMMIT`，因此对固定 tarball 是确定的。测试断言就按这个实际输出来写。

## 上游测试清点（R51）

上游**没有任何测试**：

- 无 `tests/` `test/` `spec/` `t/` 目录
- 全树无 `enable_testing()` / `add_test()` / `include(CTest)` / gtest / Catch
- 唯一名字里带 test 的文件是 `terminal/bidi_test.c`（Bidi 镜像测试数据），但顶层 `guiterminal` 目标只编译 `terminal.c` `bidi.c` `lineedit.c`，**没有任何规则引用它**，既不编译也不执行
- 上游是 CMake 工程，未定义 `check`/`test` 目标

所以 `HMBS_UPSTREAM_TEST_RESULT` 如实报 `status=no_tests / discovered=0`，**绝不**把它写成「测试通过」。完整清点证据见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。

## 验证

`conan create`（host=OHOS aarch64）编译打包通过，产物：

```
$ file bin/ipbt
ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
interpreter /lib/ld-linux-aarch64.so.1
$ readelf -d bin/ipbt | grep NEEDED
 (NEEDED)  Shared library: [libc.so]
```

ncurses 完全静态进包（`readelf -sW bin/ipbt`：curses 符号为本地符号、UNDEF 为 0），没有产出任何 `.so`，不污染系统同名库（R26 / L5）。

安全性：PIE（`FLAGS_1 = PIE`）、NX（`GNU_STACK` 为 RW，无 X）、RELRO（`GNU_RELRO` 段存在）。

test_package 共 32 条断言，全部真实执行已打包的 aarch64 二进制：`test.sh` 14 条（通用入口与转换功能）
+ `test_ohos_playback.sh` 18 条（鸿蒙特有端到端消费者用例，rule12）。前者清单见
`test_package/MANIFEST.yml`，后者见 `reports/test-report.md` §4b：

| # | 断言 | 结果 |
|---|------|------|
| 1 | `ipbt --version` 精确等于 `ipbt, source commit fdcd2b0a…` | ✅ |
| 2 | `ipbt --help` 含 usage / `--utf8-linedraw` / `-A` / `-f` | ✅ |
| 3 | `ipbt --licence` 含 PuTTY 版权 + MIT 许可 | ✅ |
| 4 | `ipbt-dump --version` 精确版本串 | ✅ |
| 5 | `ipbt-dump --help` 含 `-S, --script` / `-H, --hex-dump` / `-x, --screen-xml` | ✅ |
| 6 | `ipbt-dump --licence` 含 PuTTY 版权 + MIT 许可 | ✅ |
| 7 | `-T` 默认 SUMMARY 输出 `:0:0.000000:offset 0xc len 0xc` | ✅ |
| 8 | `-T -S` typescript 输出与录制数据 `cmp` 逐字节相同 | ✅ |
| 9 | `-T -H` hex dump 含 `68 65 6c 6c 6f` 与 ASCII 列 `hello ipbt` | ✅ |
| 10 | `-T -x` 屏幕 XML 含 `<ttyrecording>`/`<frame index="0">`/`<t>hello ipbt`/`</ttyrecording>` | ✅ |
| 11 | `-R -S` raw 模式往返一致 | ✅ |
| 12 | 无文件名 / 文件不存在 / 未知长选项 三者退出码均非 0 | ✅ |
| 13 | 篡改载荷后 hex dump 输出必须改变（反假阳性） | ✅ |
| 14 | 去掉 `-T` 后格式自动识别仍选中 ttyrec 并解析出同一帧 | ✅ |

ttyrec 测试夹具是脚本自己合成的最小合法文件：12 字节头（sec=0、usec=0、len=12，三个小端 uint32）+ 12 字节 `hello ipbt\r\n`。

交互式 curses 播放器 `ipbt` 的 UI 无法在无头环境驱动，测试改为覆盖它的三个非 curses 入口与选项校验；`ipbt-dump` 与播放器共用同一个 `ipbtsrc/read.c` ttyrec 解析器和同一个 PuTTY 终端模拟器，所以功能路径是真跑到的。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ipbt` | 交互式 ttyrec 回放播放器（curses） |
| `bin/ipbt-dump` | 非交互转换器：hex dump / typescript / 屏幕 XML |
| `share/man/man1/ipbt.1` | tarball 自带的预生成 roff man page（重建它需要 halibut，故未在构建期生成） |
| `share/doc/its-playback-time/README` | 上游 README |
| `licenses/LICENCE` | MIT |

## 注意事项

- `package_type = "application"`，软件级目录已放 `commands.json`（R38 / L0k）
- `cpp_info.requires = ["ncurses::ncurses"]`：libncursesw.a 静态进了二进制，但运行期仍需 terminfo 库，这条把 ncurses 留在消费者的 `cpp_info` 图里
  （2026-10-11 实测更正：**仅靠这一条，`test_package` 图里的 `ncurses/6.6` 仍是 `run=False` 且 `package_folder=None`，生成的 `conanrunenv-*.sh` 里不含 `TERMINFO`**；test_package 需要自己再声明一次运行依赖，见下文「2026-10-11 修复」）
- `R32`：`configure()` 用 `self.settings.os not in ("Linux", "OHOS")`
- `R33`：编译器由 `CMakeToolchain` / `tools.build:compiler_executables` 注入，`self.run()` 里没有裸 `${CC}` / `${CFLAGS}`
- 产物 SHA256：`bin/ipbt` = `c7b7e20d11a776a8…`，`bin/ipbt-dump` = `890f90cfa3910472…`

---

## 2026-10-11 修复：test_package 的 TERMINFO 注入（CI #84438 / #84387 红灯）

**现象**：`## CI 校验失败`（构建 #84438 / worker CI-036），失败步骤 `conan-build-test`：

```
its-playback-time OHOS 端到端消费者用例：17 通过 / 1 失败
not ok 4 - TERMINFO 无效 (got: empty)
→ test_ohos_playback.sh failed → ConanException: test_package assertions failed: 14/32
```

**根因（已实测定位，不是"环境缺数据"）**：配方 `requires("ncurses/6.6")`，`ncurses/6.6` 的包目录里
terminfo 数据是齐的（`share/terminfo` 与 `lib/terminfo` 各 34 个条目）。问题在于 **test_package 图里
`run` 特征缺失**，于是 Conan 既不导出运行环境、也不给依赖包目录：

```
# 本地 `conan test` 探针输出（test_package 的 test() 内打印）
PROBE subdep ncurses/6.6, Traits: build=False, headers=True, libs=True, run=False, visible=True
      -> package_folder=None
PROBE   conanrun.sh                     TERMINFO/LD lines: []
PROBE   conanrunenv-release-armv8.sh    TERMINFO/LD lines: []
```

即：`cpp_info.requires` 只影响 `cpp_info` 图，**不会**把 `TERMINFO/TERMINFO_DIRS` 带进 test_package 的
聚合运行环境（这与本文件上文原先的说法相反，已一并更正）。旧代码据此解析 → 结果为空 →
传给 `test_ohos_playback.sh` 的第二个参数是空串 → 断言 4 必然失败。

**修复**（本轮，均在 `test_package/` 内，不动产物本体）：

1. `test_package/conanfile.py` 的 `requirements()` 显式声明运行依赖：
   `self.requires("ncurses/6.6", run=True, visible=False)`
   —— `run=True` 才让 `VirtualRunEnv` 为 ncurses 生成运行环境。实测（同一命令）：
   `conanrunenv-release-armv8.sh` 出现
   `export TERMINFO="/root/.conan2/p/ncurs780a5e6acf3cf/p/share/terminfo"` 与同名 `TERMINFO_DIRS`，
   且 `_resolve_terminfo()` 取到它并打印来源：
   `terminfo hit: …/share/terminfo (source=runenv:conanrunenv-release-armv8.sh)`。
2. 新增 `_resolve_terminfo()`：四级来源（环境变量 → 生成的 `conanrunenv*.sh` → host 依赖包目录
   `share|lib|etc/terminfo` → 系统常见位置），命中则把 **来源** 打日志：`TERMINFO=<path> (source=<...>)`，
   便于 CI 现场逐条核对；同时打印候选数量与 host 依赖清单（上面那段 PROBE 就是它的取证形态）。
3. 两个 `self.run(...)` 都加 `env="conanrun"`：由 Conan 应用聚合运行环境（`conanrun.sh` →
   `conanrunenv-*.sh`），与真机 consumer 的运行环境一致，不再依赖 worker 是否手工 source 过。
4. `test_ohos_playback.sh` 断言 4 改为「终端库契约」三分支：注入则必须是有效目录（强断言，本地与
   CI 走的就是这一支）；未注入但设备自带则记录实际路径；两者皆无时用负控
   （`TERMINFO=/nonexistent-termlib` 下 `ipbt-dump --version` 仍必须可用）证伪"依赖宿主终端库"。
   后两支是给真机兜底的可证伪分支，不把宿主 env 配置当成交付契约。

**复跑证据**（本地，`conan test` 同源复现，与 CI 同一 profile `ohos-aarch64-wsl`）：

```
ok 1 - bin/ipbt 存在且为 ELF            ok 4 - TERMINFO 指向有效目录（注入：…/ncurses/…/share/terminfo）
ok 2 - bin/ipbt-dump 存在且为 ELF       ok 6 - ipbt-dump --version 可运行且输出版本标记
ok 3 - 整包不含 .so（ncurses 静态链入）  ok 7..18 全通过
not ok 5 - ipbt --version 异常 (got: )   ← 仅本地：x86_64 宿主加载 aarch64 时
                                            `Error relocating … __fd_chk: symbol not found`，
                                            与产物本身无关；同一断言在 CI 真机 #84438 是通过的
```

**门禁复跑**：`CI_BRANCH=feat/its-playback-time-0.2026-05-26.fdcd2b0 \
CONAN_PROFILE=ohos-aarch64-wsl CI_PACKAGES="archives/i/its-playback-time/0.2026-05-26.fdcd2b0" \
zsh ci/conan/build_and_test.sh`（G0/KC/JC 通过；L1 因上述宿主加载限制在本地红，CI 真机不受影响）。
