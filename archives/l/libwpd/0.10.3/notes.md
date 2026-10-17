# libwpd 0.10.3 适配笔记

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU Autoconf 2.69；单一 configure）
- 平台任务: contrib-8442（libwpd 0.10.3），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 编译器: clang/clang++ 15.0.4
- 依赖: `librevenge/0.0.5`、`zlib/1.3.1`；`boost/1.90.0.3` 为 **tool_requires**（构建期头文件）
- 上游: 项目主页即 SourceForge（https://libwpd.sourceforge.net/）
- 源码 sha256: `2465b0b662fdc5d4e3bebcdc9a79027713fb629ca2bff04a3c9251fdec42dd09`
- 状态: built（G0/G1/G2/G3 全过，库级 9/9 + CLI 级 5/5）

## 源码面貌（摸底结论）

- 主体 **C++**：`src/lib/` 174 个 `.cpp`、173 个头；`src/conv/` 是转换工具（wpd2text/wpd2html/wpd2raw），`src/fuzz/` 是 fuzzer（默认关）
- 交付形态：静态库 `libwpd-0.10.a` + 头 `include/libwpd-0.10/libwpd/{libwpd.h,WPDocument.h}` + 三个 CLI 工具 + `.pc`
- 依赖探测：
  - `PKG_CHECK_MODULES([REVENGE],[librevenge-0.0 >= 0.0.1])`（必需）
  - `--enable-tools` **默认 yes** → 额外需要 `librevenge-generators-0.0` 与 `librevenge-stream-0.0`
  - boost 头检查：`CPPFLAGS="${BOOST_CFLAGS} ${CPPFLAGS}"` + `AC_CHECK_HEADERS([boost/spirit/include/qi.hpp])`，缺失即 `AC_MSG_ERROR`
- 上游**无测试套件**：无 `TESTS`/`check_PROGRAMS`、无 `src/test/`、无 `*test*` 源文件，也不分发 WordPerfect 样例文档

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify libwpd 0.10.3 --project-dir "$PWD"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `checking for C compiler default output file name... configure: error: C compiler cannot create executables`（CI 上，设备通过） | conan 的 `AutotoolsToolchain` 把 `CC=/data/service/hnp/bin/clang` 写进 `conanautotoolstoolchain.sh`，但该脚本只被 conan 自己的 `Autotools()` 助手 source；裸 subprocess 里 CC 未设 → autoconf 退到 PATH 里的裸 `clang`。设备 PATH 含 hnp 目录故恰好正确，CI worker 不含则命中无法链接 OHOS 可执行文件的 clang | `_compiler_environment_items()`：从 profile 的 `tools.build:compiler_executables` 显式导出 `CC`/`CXX`（R33） |
| 2 | 编译期 `fatal error: 'boost/spirit/include/qi.hpp' file not found` → configure 阶段则报 `Required boost headers not found.` | libwpd 自身 `src/lib/libwpd_internal.cpp` 使用 boost/spirit，属**私有头文件依赖**（公共头与链接接口都不含 boost） | 用 `tool_requires("boost/1.90.0.3")`（构建期上下文，版本与 librevenge 依赖的 boost 对齐），并在 `_revenge_environment_items()` 里导出 `BOOST_CFLAGS` 与 `CPPFLAGS` |
| 3 | `The direct dependency 'boost' is not used by any '(cpp_info/components).requires'` | 我先写成 `requires`，又不该把 boost 放进 `cpp_info.requires`（消费者不需要它） | 改为 `tool_requires`（见 #2），两者同时解决 |
| 4 | 链接工具时报 `libtool: warning: library '.../librevenge-0.0.la' was moved` + `libtool: error: cannot find the library '//lib/librevenge-0.0.la'` | librevenge 用 `--prefix=/` + DESTDIR 打包，其 `.la` 里记录的 `libdir` 是 `//lib`；libtool 在 `-L` 目录里优先找 `.la` 并按其中路径解析 | 把 `-L` 指向构建目录内一个**只放三个 `.a`、不放 `.la`** 的目录（`_clean_link_dir()`），libtool 于是走普通 `-L/-l` 路径 |
| 5 | 若改为直接给 `.a` 绝对路径：`ld.lld: warning: archive member 'librevenge-0.0.a' is neither ET_REL nor LLVM bitcode` | libtool 把命令行上的 `.a` 当作输入**成员**归档进 `libwpd-0.10.a` | 同上，用干净的 `-L` 目录而不是绝对路径（否则消费者再链 librevenge 会出现重复符号） |
| 6 | 设备无 pkg-config，三处 `PKG_CHECK_MODULES` 无法通过 | `PKG_CHECK_MODULES` 在对应 `<PREFIX>_CFLAGS` 非空时短路，不调用 pkg-config | 分别导出 `REVENGE_*`、`REVENGE_GENERATORS_*`、`REVENGE_STREAM_*` 三组变量（`*_LIBS` 里带上 librevenge 自身所需的 `-lz`，静态库场景必须） |
| 7 | 消费者测试编译失败（18 个错误）：`use of undeclared identifier 'WPDocument'` | libwpd 的公开符号都在 `libwpd::` 命名空间内 | 测试里全部加限定名（`libwpd::WPDocument`、`libwpd::WPD_CONFIDENCE_EXCELLENT` 等） |
| 8 | 断言 `header.wpd 必须被拒绝` 失败（实际 exit 0） | 我构造的是**合法** WPX 头（就是为了做正向识别断言），工具接受它并输出 1 字节文本是合理行为；上游对「合法头 + 零字节体」未作规定 | CLI 测试对该输入只断言「不得以信号终止」并把实测退出码与输出字节数记入日志，不对未规定行为写死期望 |
| 9 | 设备 job 报「另一个任务在跑，退出」 | 两个 `agent_worker.sh` 并发取走同一 job，互斥锁把第二个挡住（这是期望行为）；但我在上一轮验证未结束时投了下一轮 | 等上一轮验证结束（确认无 conan/make 进程、verify 日志已生成）再投递 |

## 源码修改

无补丁，未改动上游任何源码。

## 依赖版本

- `librevenge/0.0.5`（文档模型基础库；静态库，其 stream 层需要 `-lz`，已随 `REVENGE*_LIBS` 传递）
- `zlib/1.3.1`
- `boost/1.90.0.3`（tool_requires，仅构建期头文件；与 librevenge 依赖的 boost 同版本，避免图中出现两个 boost）

## 验证结果（设备实机实测，2026-09-14）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: libwpd 0.10.3
```

库级消费者测试（test_package，ctest + 直接执行）：

```text
ok 1 - isFileFormatSupported(nullptr) reports no confidence
ok 2 - an empty stream reports no confidence
ok 3 - a text file reports no confidence
ok 4 - WPC magic with an unknown file type reports no confidence
ok 5 - a WordPerfect file type with an unhandled version reports no confidence
ok 6 - a WP6+ header (file type 0x0a, major version 0x02) is detected as excellent
ok 7 - a WP5 header (major version 0x00) is detected as excellent
ok 8 - parse() on a non-WordPerfect stream reports failure
ok 9 - verifyPassword() on a non-WordPerfect stream never reports a match
1..9
# 9 checks, 0 failures
```

CLI 级消费者测试（对已安装的 `bin/wpd2text`）：

```text
ok 1 - installed wpd2text exists and is executable: .../p/bin/wpd2text
ok 2 - a missing input file fails with a non-zero exit code
ok 3 - plain text is rejected cleanly (exit 1)
ok 4 - header-only input is handled without a crash (exit 0, 1 bytes of text)
ok 5 - every input is handled without a crash, with the expected outcome
```

## 可复用要点（对 libabw 直接适用）

libwpd 与 libabw 同族（libwpd/libwps/libabw 都基于 librevenge、都用 libtool + PKG_CHECK_MODULES），
本包踩过的坑 libabw 会原样遇到：

1. **`.la` 不能跨包复用** → 依赖库统一走「只含 `.a` 的干净 `-L` 目录」；
2. **私有头文件依赖用 `tool_requires`**（boost 这类）而不是 `requires`；
3. **`REVENGE*_CFLAGS/_LIBS` 三组变量都要导出**（含 `-lz`）；
4. **CC/CXX 从 profile conf 显式导出**；构建 shell 用 hnp bash；
5. 消费者测试注意 `libwpd::` / `libabw::` 命名空间限定。
