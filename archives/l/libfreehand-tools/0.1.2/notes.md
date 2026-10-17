# libfreehand-tools 0.1.2 适配笔记

## 编译环境

- 构建系统: autotools（上游 dist tarball 自带 configure，免 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 交叉工具链，`Target: aarch64-unknown-linux-ohos`）
- 状态: built
- 上游源码: LibreOffice/DLP libfreehand tag `libfreehand-0.1.2`（2017-09-16 发布）
  - URL `https://dev-www.libreoffice.org/src/libfreehand/libfreehand-0.1.2.tar.xz`
  - sha256 `0e422d1564a6dbf22a9af598535425271e583514c0f7ba7d9091676420de34ac`（本任务自行下载复算，
    不沿用 `libfreehand/0.1.1` 归档的 URL/sha256）

## 包形态（-tools 子包口径）

`libfreehand-tools` = **同一上游 tarball 的源码树整体编译**：`src/lib/`（`libfreehand-0.1` 库本体，
含 `libfreehand-internal` 内部便利库）+ `src/conv/{raw,svg,text}/`（`fh2raw` / `fh2svg` / `fh2text`
三个转换工具，LDADD 指向本树 libtool 产出的 `libfreehand-0.1.la`）。与 Alpine libfreehand 拆包口径一致，
也与本仓已合并的同族包 `libmspub-tools/0.1.4`、`libmwaw-tools/0.3.22` 同形。
库本体不在制品仓（`archives/l/libfreehand/0.1.1` 是手工编译时代的归档，无 conan 配方），故在本包内一并编译。

## 编译步骤

1. `conan create archives/l/libfreehand-tools/0.1.2 -pr:h=<repo>/ci/conan/profiles/ohos-aarch64
   -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -c tools.build:jobs=1`
2. configure 用 GNU triplet 强制交叉编译模式（`--build/--host=aarch64-unknown-linux-gnu`），因上游
   `config.sub`(2012) 不识别 `aarch64-linux-ohos`；OHOS 目标由工具链 CFLAGS/LDFLAGS/sysroot 达成。
3. PKG_CHECK_MODULES 模块（librevenge / revenge-stream / revenge-generators / zlib / icu-uc /
   lcms2 / cppunit）用「预置 `<MODULE>_CFLAGS`/`<MODULE>_LIBS` 环境变量 + la-free shadow 目录
   `-L<shadow> -l<name>`」绕过 pkg-config 探测与 libtool `.la` 查找。
4. `make`（`-j1`）→ `make check`（上游 CPPUnit 套件）→ `make install` → `conan create` 的
   `test_package`（鸿蒙消费者用例 + 三个工具 `--version` 冒烟）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: definition of implicit copy assignment operator for 'FHTransform' is deprecated ... [-Werror,-Wdeprecated-copy-with-user-provided-copy]`，构建直接失败 | 上游 `configure.ac` 的 `--enable-werror` **默认 yes**（`[enable_werror=yes]`，开发默认）；2017 年代码 + clang 15 触发新告警即错误 | 传 `--disable-werror`（上游自带开关、发行版打包惯例）；**不改源码、不加平台宏**（对照：0.1.1 归档用 `#ifdef __OHOS__` 加 `operator=` 的补丁，本包不采用——PF5 禁补丁新增 `__OHOS__` 行） |
| 2 | `error: use of undeclared identifier 'outbuf'`（18 errors，`libfreehand_utils.cpp`） | `U16_NEXT(s,j,length,c)` 在 ICU 78 展开为 `do{...}while(0)` 块，源码缺分号 → 紧随的 `unsigned char outbuf[...]` 落入 while 体，出作用域 | `patches/0001-src-lib-libfreehand_utils.cpp.patch`（仅补 1 个分号，平台无关，`patch -p1 --dry-run` 实测可应用） |
| 3 | `archive member 'libz.a' is neither ET_REL nor LLVM bitcode` / `undefined symbol: inflate*` | libtool `_LIBADD` 里绝对路径 `.a` 被当 convenience 库嵌入产物 | la-free shadow 目录 + `-L<shadow> -l<name>`（libmspub-tools 同款手法） |
| 4 | `libtool: error: cannot find the library '//lib/librevenge-0.0.la'`（潜在） | librevenge 的 `.la` 带 `libdir='//lib'` 病灶（E236） | shadow 目录只放 `.a`、不放 `.la`，`-lrevenge-0.0` 无法命中 `.la`；package() 再清掉包内 `.la` |
| 5 | 三个工具与消费者二进制无法启动（`liblcms2.so.2` 找不到） | `archives/l/lcms2/2.19` 制品仓**只有动态 binary**（`default_options shared=True`，无 `.a`；`-o lcms2/*:shared=False --build=never` 实测 `Missing prebuilt package`）；OHOS 系统只有 `liblcms_shared.z.so`（soname 不同） | 保持 lcms2 动态链接 + `-Wl,-rpath,<lcms2 libdir>`（主配方与 test_package 同款），包内 `bin/` 与 test_package 二进制都可直接执行，L2 冒烟无需手工设 `LD_LIBRARY_PATH`。实测 `readelf -d bin/fh2raw`：`RUNPATH=[…/lcms2…/p/lib]`、`NEEDED=liblcms2.so.2` |
| 6 | 构建期需要 `gperf`（生成 `tokenhash.h`）与 `perl`（`gentoken.pl` 生成 `tokens.gperf`） | `src/lib/Makefile.am` 的 `BUILT_SOURCES = tokens.h tokenhash.h`：tarball 虽随包发布 `tokenhash.h`，但 `tokens.gperf` 不在包内 → make 必然重新生成两者；`AM_MISSING_PROG([GPERF],[gperf])` | perl 用 `tool_requires("perl/5.42.2.3")`（制品仓已发布，实测 `conan install --build=never` rc=0）；**gperf 无已发布 conan 包**（`archives/g/gperf/3.1` 只有配方，`conan install --build=never` rc=1）→ 依赖 HNP 提供的 `/data/service/hnp/bin/gperf`，automake 的 `missing` 包装器在构建期从 PATH 解析并**真实执行**（构建日志：`missing gperf --compare-strncmp -C -m 20 tokens.gperf` → 产物 `tokenhash.h` 13 258 B，头部 `/* C++ code produced by gperf version 3.1 */`）。先例：`archives/l/libhubbub/0.3.8`。**若 CI PATH 无 gperf，`missing` 退出码被管道吞掉会让 `tokenhash.h` 变空 → `FHParser.cpp` 立刻编译失败（响亮失败，不是假绿）** |
| 7 | `Your 'rm' program is bad` / `bad interpreter: /bin/bash` | codebuddy safe-bin 的 `rm` shim（shebang `#!/bin/bash`，OHOS 无 `/bin/bash`）三重注入：PATH 首项目录、`BASH_FUNC_rm%%` 等函数导出、`BASH_ENV` 指向的脚本会**复活** `rm` 函数 | `_sanitize_path()` 一次清三者 + PATH；保留 `ACCEPT_INFERIOR_RM_PROGRAM=yes` 双保险（libmspub-tools 同款） |
| 8 | `configure`/`config.status` 在 HMDFS 上 `Permission denied`（潜在，E011） | `umask 077 && mktemp -d` 在 HMDFS 生成不可写临时目录 | `_patch_configure_umask()` 运行时把 `configure` 的 `umask 077` 放宽为 `022`（libmspub-tools 同款） |
| 9 | 采信轮 G2 FAIL：`Package 'libfreehand-tools/0.1.2' not resolved: Unable to find ... in remotes`（而 `conan create` 本体已 `Package '…' created`） | `conan-verify` 以 `conan create … --user=ohpcd --channel=stable` 运行，包 ref 是 `libfreehand-tools/0.1.2@ohpcd/stable`；test_package 里写死 `self.requires("libfreehand-tools/0.1.2")`（无 user/channel）解析到**另一个 ref** | test_package 改用 `self.requires(self.tested_reference_str)`（整仓 5908 个 test_package 中 5896 个的标准写法；`libmspub-tools/0.1.4` 属少数写死字面量的例外，不照抄） |

## 源码修改

- `patches/0001-src-lib-libfreehand_utils.cpp.patch`：`src/lib/libfreehand_utils.cpp:165` 的
  `U16_NEXT(s, j, length, c)` 补分号。**平台无关**（对任何 ICU 版本都是正确的），无 `__OHOS__` 宏。
- 本包**未打**配置类补丁：`config.guess`/`config.sub` 的 HarmonyOS 识别由 GNU triplet
  （`--build/--host=aarch64-unknown-linux-gnu`）绕过，不需要改生成文件。

## 依赖版本

- librevenge/0.0.5（单包提供 revenge-0.0 / revenge-stream-0.0 / revenge-generators-0.0 三库）
- icu4c/78（icu-uc：`unicode/utf8.h`、`unicode/utf16.h`）
- zlib/1.3.1（`FHInternalStream.cpp` 的 `inflate*`）
- lcms2/2.19（**动态**：`FHParser.cpp` 的 `cmsOpenProfileFromMem`）
- boost/1.90.0.3（仅头文件：`boost/cstdint.hpp`）
- cppunit/1.15.1（`--enable-tests` 上游默认 yes → 默认构建期依赖；上游用例的运行框架）
- pkgconf/3.0.5、perl/5.42.2.3（tool_requires）

W0 实测：以上 8 条 `conan install --requires=<ref> -pr:h/-pr:b=<repo profile> --build=never` 全部 rc=0
（`$TASK_DIR/w0-deps.txt`、`$TASK_DIR/pipeline-logs/s1-08-w0-deps.log`）。

## 上游测试清点与结果（父 tarball 全量注册面）

清点命令（在 `$TASK_DIR/upstream-n/libfreehand-0.1.2` 下执行）：

```bash
grep -rn "^check_PROGRAMS\|^TESTS\|^noinst_PROGRAMS\|_SOURCES" --include=Makefile.am .
grep -rn "CPPUNIT_TEST(\|CPPUNIT_TEST_SUITE_REGISTRATION" src/test/*.cpp
grep -c "CPPUNIT_ASSERT" src/test/FHInternalStreamTest.cpp
```

| 候选口径 | 读数 | 取数位置 |
|---|---|---|
| `check_PROGRAMS` | **1**（`test`） | `src/test/Makefile.am:5` |
| `TESTS` | **1**（`$(target_test)`） | `src/test/Makefile.am:25` |
| CPPUnit 注册用例（`CPPUNIT_TEST`） | **2**（`testRead`、`testSeek`） | `src/test/FHInternalStreamTest.cpp:32-33` |
| CPPUnit suite 注册 | **1** | `src/test/FHInternalStreamTest.cpp:104` |
| 测试/模糊测试源文件数 | **3**（`src/test` 2 个 + `src/fuzz` 1 个） | `test_SOURCES` / `noinst_PROGRAMS` |
| assertion 数（**另一单位，只披露不并入 N**） | **20**（testRead 7 + testSeek 13） | `CPPUNIT_ASSERT*` 计数 |

**主 N = 3**（用例/注册类候选口径的最大值 = 测试/模糊测试源文件数），逐项归因：

| 项 | 在本包构建/运行 | 结果 | 依据 |
|---|---|---|---|
| `src/test/FHInternalStreamTest.cpp`（testRead、testSeek 2 用例，20 断言） | 是 | **PASS** | `make check` 日志 `test::FHInternalStreamTest::testRead : OK` / `::testSeek : OK` / `OK (2)` |
| `src/test/test.cpp`（CPPUnit 运行器 main） | 是（随 `check_PROGRAM test` 编译运行） | **PASS** | `PASS test (exit status: 0)`；automake 驱动汇总 `# TOTAL: 1 # PASS: 1 # FAIL: 0` |
| `src/fuzz/fhfuzzer.cpp`（`noinst_PROGRAMS = fhfuzzer`） | 否 | **NOT_RUN** | 链接需 `-lFuzzingEngine`（libFuzzer 引擎库），制品仓与工具链均无；上游 `--enable-fuzzers` 默认 `no`，不放开该开关引入不可得依赖 |

台账（同单位、自洽）：`上游 TOTAL = 3 = PASS 2 + FAIL 0 + SKIP 0 + NOT_RUN 1`。
（automake 驱动层同一次运行的汇总为 `TOTAL 1 / PASS 1 / FAIL 0`，口径是「测试程序数」；
本表口径是「用例/源文件数」，两者不可相加，分别列示。）

## 验证结果

```bash
# conan create 全流程（含 make check 与 test_package）
conan create archives/l/libfreehand-tools/0.1.2 \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=1
# → libfreehand-tools/0.1.2: Package 'b596456020758db0c94e98e58554d6db2f2c0041' created

# 上游 CPPUnit 用例（在 build() 内以 HOME=<build>/.test-home 沙箱运行）
#   test::FHInternalStreamTest::testRead : OK
#   test::FHInternalStreamTest::testSeek : OK
#   OK (2)  /  PASS test (exit status: 0)  /  # TOTAL: 1 # PASS: 1 # FAIL: 0

# 鸿蒙消费者用例（test_package/harmonyos_specific_test.cpp）6/6
PASS: isSupported(nullptr) is safely rejected
PASS: parse(nullptr, nullptr) is safely rejected
PASS: plain text stream is not a FreeHand document
PASS: parse() rejects a plain text stream
PASS: AGD magic header is recognized as FreeHand (positive detection)
PASS: FH3 magic header is recognized as FreeHand (positive detection)

# 三个工具冒烟（退出码 0）
fh2raw --version   -> fh2raw 0.1.2
fh2svg --version   -> fh2svg 0.1.2
fh2text --version  -> fh2text 0.1.2
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/fh2raw` | FreeHand → raw 调试输出（`--callgraph` 显示调用图嵌套层级） |
| `bin/fh2svg` | FreeHand → SVG |
| `bin/fh2text` | FreeHand → 纯文本 |
| `lib/libfreehand-0.1.a` | 静态库本体（R26：系统同名库不动态链接） |
| `include/libfreehand-0.1/libfreehand/` | 公共头（`libfreehand.h`、`FreeHandDocument.h`） |
| `lib/pkgconfig/libfreehand-0.1.pc` | pkg-config 元数据 |
| `licenses/COPYING` | MPL-2.0 |

## 注意事项

- **交付面不含 `libfreehand-internal.la`**：`src/lib` 的 `noinst_LTLIBRARIES` 便利库只用于本树内链接；
  `autotools.install()` 不会安装它。
- **包内无 `.la`**：`package()` 主动删除 libtool 归档，避免下游 libtool 重读陈旧 `dependency_libs`
  路径（E236 收尾）。
- **lcms2 是运行时依赖**：`bin/fh2*` 带 `DT_NEEDED=liblcms2.so.2` + RUNPATH 指向构建时 conan cache；
  换机器运行时由消费侧 conan runtime env（`conanrun.sh`）提供 `LD_LIBRARY_PATH`。
- **上游 `--enable-tests` 默认 yes**：不传 `--disable-tests` 是**沿用上游默认**，不是为凑数字放开开关；
  上游 CPPUnit 套件因此默认进构建，本配方在 `build()` 内真实 `make check`。`--enable-fuzzers`
  保持上游默认 `no`（需不可得的 `-lFuzzingEngine`），对应 fuzz 项按 NOT_RUN 申报。
- `--help` 在上游一律走 `printUsage()` `return -1`（退出码 255），冒烟统一用 `--version`。
- 上游 `src/test/test.cpp` 的版权头写成 "part of the libcdr project"（复制粘贴笔误），与本包无关，未修。

---

**编译结束**: 2026-09-20
**最终状态**: built（本地 conan create + 上游测试 + test_package 全通过，未 conan upload 到 ohpcd）
