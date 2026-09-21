# libetonyek-tools 0.1.12 — 适配说明

## 这个包是什么

libetonyek 是 Apple iWork（Keynote / Pages / Numbers）文档解析器，通过 librevenge
的文档模型对外输出。它的**源码树里除了库，还带一组命令行转换器**（`src/conv/`），
`configure.ac` 的 `AC_ARG_WITH([tools])` 没有默认值，而判定是
`AS_IF([test "x$with_tools" != "xno"])` → **不显式关掉就会构建**。本包只装这 9 个
可执行文件（+ licenses），库本身仍属 `libetonyek/<版本>`——与 Debian 把
`libetonyek-tools` 单独成包的做法一致：

| 目录 | bin_PROGRAMS |
|---|---|
| `src/conv/raw` | `key2raw` `numbers2raw` `pages2raw` |
| `src/conv/text` | `key2text` `numbers2text` `pages2text` |
| `src/conv/csv` | `numbers2csv` |
| `src/conv/html` | `pages2html` |
| `src/conv/svg` | `key2xhtml` |

## 取源

`https://dev-www.libreoffice.org/src/libetonyek/libetonyek-0.1.12.tar.xz`
sha256 `b9fa82fbeb8cb7a701101060e4f3e1e4ef7c38f574b2859d3ecbe43604c21f83`（1513688 B，
本机 curl + sha256sum 实测；真机 `source()` 同一 URL 亦 HTTP 200 / 1513688 B）。
必须用官方 dist 包：它自带生成好的 `configure`（设备上没有 automake/autoconf/
libtoolize，GitHub tag 归档无法 autoreconf）。任务版本 `0.1.12` 与上游 tag 逐字对应，
未用 main/master 顶替。

## 依赖

requires：`librevenge/0.0.5`、`libxml2/2.15.3.1`、`zlib/1.3.1`（三者都在链接行上，
运行期也需要共享的 libxml2）。
tool_requires：`boost/1.90.0.3`（私有头）、`glm/1.0.3`（`AC_CHECK_HEADERS(glm/glm.hpp)`
是硬检查）、`mdds/3.2.1`（制品是 API 3.0，故 `--with-mdds=3.0`）、`cppunit/1.15.1`（上游套件）。

`src/conv/*/Makefile.am` 里出现的 `$(BOOST_FILESYSTEM_LIB)` / `$(BOOST_SYSTEM_LIB)`
**不需要 boost 库**：本 dist 的 `configure.ac` 只用 boost 宏探测头文件，没有
`AC_SUBST` 这两个变量（`grep -c BOOST_FILESYSTEM_LIB configure` = 0），占位符在
Makefile.in 里被替换为空。tools 源码本身也一次都没用到 `boost::filesystem`
（`grep -rn filesystem src/conv/` 无命中）。

## 上游测试

`--enable-tests`（默认即 yes）构建 `src/test/`，其 `Makefile.am` 同时写
`check_PROGRAMS = core detection streams` 与 `TESTS = $(tests)` → `make -j1 check`
真跑三套 cppunit 程序，失败即整包失败。

用例口径（在解包后的 `src/test/` 里执行，取最大口径）：

```sh
grep -rhoE '\bCPPUNIT_TEST(_CASE|_TEMPLATE|_TEMPLATE_ADVANCED)?[[:space:]]*\(' src/test | wc -l
# → 60
```

60 个声明分布在 17 个 `CPPUNIT_TEST_SUITE` 里；`--without-liblangtag` 会把
`IWORKLanguageManagerTest.cpp`（含 2 个 `CPPUNIT_TEST`）整文件排除在 `core` 之外
（`src/test/Makefile.am` 的 `if WITH_LIBLANGTAG ... core_SOURCES +=`），
因此本配置的实跑数是 58。

## 鸿蒙侧结论

- **交叉三元组下的工具名探测**：`--build=...-musl --host=...-gnu` 让 autoconf 去找
  `aarch64-unknown-linux-gnu-ar`/`-ld`，真机与 CI worker 都没有这个名字，且真机 PATH 上
  连 `ar`/`ld` 都没有（只有 harmonybrew 的 `llvm-ar`，链接器只有
  `<sdk>/native/llvm/bin/ld.lld`）。探测因此退化并硬失败，实测两条按顺序出现：
  `configure: error: could not determine false interface`（AR 退化为 `false`）、
  `configure: error: no acceptable ld found in $PATH`。配方在构建环境里按
  「PATH → 编译器同目录」显式喂 `AR/RANLIB/NM/STRIP/LD`。
  （OHOS profile 的 `[env]` 段本来就写了 `AR=llvm-ar`/`RANLIB=llvm-ranlib`，但那是
  conan 自己的 runner 才应用的；本配方沿用同族范本的裸 subprocess 形态，拿不到它。）
- **shell**：范本的候选是 `/data/service/hnp/bin/bash`，那是 CI worker 才有的路径；
  真机上退到了 `/usr/bin/zsh`。候选补上 `$HOME/.harmonybrew/bin/bash` 并排在 zsh 之前
  （toybox `/system/bin/sh` 拒绝本 configure 里的 `exec 7<&0`，zsh 的分词会弄坏
  automake 递归 make）。
- 其余 OHOS 处理与 `archives/l/libetonyek/0.1.13` 相同：`umask 077→022`（hmdfs 按组位
  判可达、`chmod` 无效 → 2700 临时目录 EACCES）、辅助脚本补 `+x`（E490）、
  `make -j1`（HMDFS jobserver fifo EPERM）、7 组 `PKG_CHECK_MODULES` 变量的
  CFLAGS/LIBS **两半都必须非空**（任一半空掉就会落到构建环境里存在的 pkg-config 并
  `as_fn_error` 硬失败）、`CXXFLAGS=-std=c++17`（mdds 3.0 头用 `std::bool_constant`，
  而 `AX_CXX_COMPILE_STDCXX_11` 在 clang 15 默认 gnu++14 时不加任何 `-std`）、
  librevenge 走「只放归档的干净 `-L` 目录」避开 `.la` 里记录的 `//lib`、
  运行期靠 `-Wl,-rpath` 而不是 `LD_LIBRARY_PATH`（后者会劫持 lld 自己的 libxml2）。
- **可退化移植**：liblangtag 按 §3.6 关闭（同 0.1.13 的记录：档案在 main 里写着
  published 但制品仓查不到，属发布流水线缺口）。影响的只是文本段的语言标签元数据，
  转换输出本身不受影响。

## 真机取证

独立 `CONAN_HOME=~/work/psj/ch-libetonyek-tools`（全新 home，只从 `~/.conan2` 拷
`profiles/settings.yml/remotes.json/global.conf/extensions/migrations`，未写共享缓存）。
启动前用 `ls -lt ~/work/psj/*.log` 确认同机无其它 `conan create` 在跑
（**Toybox 的 `pgrep -f` 在这台设备上恒为空**，`find -newermt '-15 minutes'` 也不生效，
只有 `ls -lt` + 比对字节数增长可靠）。

| 项 | 值 | 出处 |
|---|---|---|
| 配方 revision | `f6eca55199bcaf0e8be000e380622f08` | 两次 create 同一值（`conanfile.py` 字节一致，md5 `ba7d13d7…`） |
| 包 ID | `3941cc866cac021130e6d0c308116c0764fbb184` | `let-ch1.log` |
| `conan create` | `CREATE_EXIT:0` | `let-ch1.log`（完整构建）与 `let-ch2.log`（复用已构建包 + 跑最终 test_package） |
| 上游套件 | `Testsuite summary for libetonyek 0.1.12` / `# TOTAL: 3 # PASS: 3 # SKIP: 0 # XFAIL: 0 # FAIL: 0 # ERROR: 0`；`PASS: core` `PASS: detection` `PASS: streams` | `let-ch1.log` 第 726–738 行 |
| 上游逐用例 | `core` OK (48)、`detection` OK (4)、`streams` OK (6) → 实跑 58 项，全部通过 | 在 `src/test/` 目录内直接跑三个测试程序（必须在 `src/test` 里跑：程序里编的是相对 `$(top_srcdir)/src/test/data`，换 CWD 会假失败） |
| 消费者断言 | `TOTAL=67 PASS=67 FAIL=0` | `let-ch2.log`（最终版 `test_tools.sh`） |
| 包内清单 | `bin/`（9 个）+ `licenses/COPYING`，无库无头 | `find <pkg>/p -type f` |
| 产物 | 9 个各约 20.4 MB，`llvm-readelf -h` → `Type: DYN (Shared object file)`、`Machine: AArch64` | 真机 |
| 取源 | `sha256 b9fa82fbeb8cb7a701101060e4f3e1e4ef7c38f574b2859d3ecbe43604c21f83`，1513688 B；本机 curl+sha256sum 与真机 `source()`（`downloaded 1513688 bytes (HTTP 200)`）两侧一致 | 本机 / `let-ch1.log` |

**L1e / R34 破坏性反向验证（本会话自行预跑）**：移走包内 `bin/` →
`conan test` 第一条断言即失败（`[FAIL] bin 目录不存在: …/p/bin`，`NEG_EXIT=1`）；
还原后 `TOTAL=67 PASS=67 FAIL=0`。

**两份日志的分工**（避免误读）：`let-ch1.log` 含完整 `make` + `make -j1 check` +
Testsuite 汇总，其 test_package 用的是当时 54 条断言的版本；改完断言后
`let-ch2.log` 复用了同一 `3941cc86` 包（配方未变，conan 正确地跳过重建）并跑最终
67 条断言到全绿。即"构建证据"与"最终消费者测试证据"分别在两份日志里，
而提交进 PR 的 `conanfile.py` 与两次运行字节相同。

