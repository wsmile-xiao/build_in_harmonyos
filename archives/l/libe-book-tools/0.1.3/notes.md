# libe-book-tools 0.1.3 OHOS 移植笔记

适配对象：libe-book-tools 0.1.3 —— Document Liberation Project 的电子书
**转换器命令行交付物**（ebook2raw / ebook2text / ebook2html），源码为
libe-book 0.1.3 官方 dist tarball。

上游首页 `https://sourceforge.net/p/libebook/`，发布物由 Document Foundation
统一托管：`https://dev-www.libreoffice.org/src/libe-book-0.1.3.tar.xz`
（416268 字节，sha256 `7e8d8ff34f27831aca3bc6f9cc532c2f90d2057c778963b884ff3d1e34dfe1f9`，
本机与设备两侧各测一次一致）。必须用 dist tarball 而非源码归档：设备无
autoconf/automake/libtoolize，只有该 tarball 预生成的 `configure`
（GNU Autoconf 2.72）能驱动构建。

## 与 libe-book 0.1.4 的关系（W2 拆分，不是重复适配）

平台把库与转换器拆成两条任务，父配方在
`archives/l/libe-book/0.1.4/conanfile.py` 的模块 docstring 里从另一侧记录了
同一决定（`--without-tools`、"W2 atomicity keeps this recipe a pure library
(no commands.json, no generators requirement)"），并与归档内既有的
libmspub / libmspub-tools 拆分一致。本包因此**只交付 bin/ 与 licenses/**，
`package_type = "application"`，并配软件级 `commands.json`（L0k/R38：产物含
bin/ 必须有）。

版本键取 0.1.3 而不是与库对齐的 0.1.4：任务卡与分支门禁（L0n/R40 按目录名推
期望分支）都以 0.1.3 为准，且 0.1.3 有自己的官方 dist 制品，坐标可精确还原。

包内不重复交付 `libe-book-0.1.a` 与头文件：同一份静态库以两个制品名交付，会
让同时依赖两者的消费者拿到重复符号定义。`make install` 装出来的 lib/、
include/、share/（CSS 只在 --enable-experimental 下安装，本包未启用）在
`package()` 里按白名单裁掉，且裁完立刻断言三个转换器都在，缺一个就硬失败。

## 上游测试三步法（R51）

1. **清点（适配前，全部在 dist 包上取数）**
   - `src/test/Makefile.am`：`check_PROGRAMS = $(target_test)` 且
     `TESTS = $(target_test)`，`target_test = test` —— 一个 cppunit 聚合程序，
     `make check` 直接跑；由 `--enable-tests` 构建（上游默认 yes）。
   - 用例宏总数（最大口径，含未参与编译的 TU）= **22**：
     ```sh
     for f in libe-book-0.1.3/src/test/*Test.cpp; do
       printf '%s %s\n' "$(basename $f)" "$(grep -cE '^[[:space:]]*CPPUNIT_TEST[[:space:]]*\(' $f)"
     done
     # EBOOKBitStreamTest 9, EBOOKMemoryStreamTest 2, PDBLZ77StreamTest 1,
     # SoftBookLZSSStreamTest 2, XMLCollectorTest 4, XMLTreeWalkerTest 2,
     # EBOOKLanguageManagerTest 2 ; test.cpp 是运行器（0）
     ```
   - 本次配置真正编译的是 **14** 个（4 个 TU）：EBOOKLanguageManagerTest(2)
     受 `if WITH_LIBLANGTAG` 门控、XMLCollectorTest(4) 与 XMLTreeWalkerTest(2)
     受 `if ENABLE_EXPERIMENTAL` 门控，两组开关都关（见下）。
   - `src/fuzz/Makefile.am` 只有 `noinst_PROGRAMS = lrffuzzer pdbfuzzer`，是
     fuzzing 目标而非测试用例，且 `--enable-fuzzers` 默认 no → 不计入 N。
2. **运行（W3）**：配方 `build()` 内 `make -j1 check` 作硬门禁，失败即出不了包。
3. **回填**：PR 表格用实测数（cppunit 自报 `OK (N tests)` 与脚本打印的
   TOTAL/PASS/FAIL），见下方「真机取证」。

## 依赖决策（W0 证据 = `conan graph info` 在隔离缓存的实测输出）

与库本体同一组引脚，本包多出 generators 一组的**探测变量**：

| 依赖 | 版本 | 角色 | 依据 |
| --- | --- | --- | --- |
| librevenge | 0.0.5 | requires | PKG_CHECK_MODULES(REVENGE/REVENGE_STREAM/REVENGE_GENERATORS)；包内捆绑三库（`cpp_info.libs` 含 revenge/revenge-stream/revenge-generators） |
| libxml2 | 2.15.3.1 | requires | PKG_CHECK_MODULES(XML)；共享库，靠 bake 的 -Wl,-rpath 运行期解析 |
| zlib | 1.3.1 | requires | PKG_CHECK_MODULES(ZLIB) |
| icu4c | 77 | requires | PKG_CHECK_MODULES(ICU, icu-i18n) 硬检查 |
| boost | 1.90.0.3 | tool_requires | AC_CHECK_HEADERS(boost/...) 与 BOOST_CFLAGS，仅头文件 |
| cppunit | 1.15.1 | tool_requires | --enable-tests 的上游测试框架 |
| gperf | 3.3 | tool_requires | AC_PATH_PROG(GPERF) 硬检查 + BUILT_SOURCES 六张 .gperf token 表 |

`conan graph info`（隔离 CONAN_HOME，`--build=missing`）显示上述 7 个依赖的
二进制全部为 `- Download (ohpcd)`，无一项需要在本机从源码构建 —— 这是先做
预检而不是直接 create 的原因（boost/icu 源码编译在设备上是小时级）。

## 可退化移植与开关边界（§3.6）

- **liblangtag 关闭**（`--without-liblangtag`，上游开关）：与库本体保持一致的
  判断 —— archives/l/liblangtag/0.6.4 标 published 而制品仓无该发布（发布流水
  线缺口，非缺任务）。影响面是解析结果里文本段的语言标注字段，不影响转换器
  输出内容；上游侧连带排除 EBOOKLanguageManagerTest 的 2 个用例。
- **experimental 关闭**（上游默认）：libcss/libhubbub/libmspack 路径未启用且
  都不在制品仓，连带 XMLCollectorTest(4) + XMLTreeWalkerTest(2) 不参与编译。
- 因此「上游 22 用例」中 8 个未运行，两处原因都是**具体依赖在制品仓不可得**，
  不是「平台限制」这类含糊说法，也未修改任何上游测试文件（patches_applied: []）。

## 平台适配要点（继承归档既有 DLP 系移植，并按本 tarball 复核）

### 三条必须按本 tarball / 本设备重测、不能从 libe-book 0.1.4 照抄的结论

1. **`config.sub` 的版本随 dist 而异，三元组可用性要逐个 tarball 实测。** 0.1.4
   的结论是「本 dist 的 config.sub/config.guess 为 2024 版，aarch64 与 musl 都
   认」，于是它用 `--build=aarch64-unknown-linux-musl`。**这条在 0.1.3 不成立**：
   本 dist 带的是 2013 版（包内时间戳 2013-06-16），实测
   ```sh
   sh config.sub aarch64-unknown-linux-musl  # rc=1 Invalid configuration: machine `aarch64-unknown-linux' not recognized
   sh config.sub aarch64-unknown-linux-ohos  # rc=1 同上
   sh config.sub aarch64-unknown-linux-gnu   # rc=0 aarch64-unknown-linux-gnu
   sh config.sub aarch64-linux-gnu           # rc=0 归一化成 aarch64-unknown-linux-gnu
   ```
   而 0.1.4 的同一份脚本对 musl 与 ohos 都返回 rc=0。本包因此改用
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，与已合入的
   `archives/l/libmspub-tools/0.1.4` 同一个选择。照抄 musl 三元组的症状是
   `configure: error: /usr/bin/zsh ./config.sub aarch64-unknown-linux-musl failed`
   —— 措辞把矛头指向 shell，实际是三元组不被识别（本地用 sh 复跑同样 rc=1）。
2. **原生模式（build == host）会激活一批 cross 模式下不跑的探测**，于是暴露出
   真机上 `ld`/`ar`/`nm` 全都不存在：实测 `command -v ld`、`ar`、`nm` 均为 NONE，
   只有 `<sdk>/native/llvm/bin/` 下的 `ld.lld`/`llvm-ar`/`llvm-nm`/`llvm-ranlib`/
   `llvm-strip`（profile 的 `[buildenv]` 正是这么映射的）。而 `[buildenv]` 只由
   conan 自己的 `Autotools()` 帮手经 conanbuild 脚本应用，本配方用裸 subprocess
   跑 configure，所以这些映射必须自己导出：否则 libtool 找不到 archiver 会把
   `AR` 退化成 `false`，报 `configure: error: could not determine false
   interface`（E012 记因、E528 记该签名与完整闭包）；补上 AR 后下一个撞出来的
   是 `configure: error: no acceptable ld found in $PATH`。修法是**从 profile 给的
   编译器绝对路径同目录**解析 `llvm-ar`/`llvm-ranlib`/`llvm-nm`/`llvm-strip`/
   `ld.lld` 导出成 `AR/RANLIB/NM/STRIP/LD`，并把该目录前置进 PATH —— 不硬编码任何
   一侧机器的路径：CI worker 上没有 `llvm-*` 时这些变量就不设，退回它自带的
   binutils，两种环境都不破。
3. **`LD_LIBRARY_PATH` 要置空而不是追加。** 真机 profile 把它指向
   `<sdk>/native/llvm/lib`，而该目录实测**自带 `libxml2.so.16`（2.14.0）**，与本包
   依赖的 libxml2/2.15.3.1 不是同一份；musl loader 先查 `LD_LIBRARY_PATH` 再查
   rpath，等于随时可能装错版本（CI-021 #48068 中 lld 被外部 libxml2 撞坏是同一
   形态）。置空是安全的：实测本 SDK clang++ 编的最小 C++ 程序（NEEDED 为
   `libc++_shared.so` + `libc.so`）在 `LD_LIBRARY_PATH` 为空时 `rc=0` 正常跑起来，
   而上游 `make check` 的程序靠 bake 的 `-Wl,-rpath` 解析 libxml2。

### 其余沿用既有结论

- configure 恰 2 处 `umask 077` → 构建前改写 022（E011：HMDFS 组位遍历，chmod
  在该文件系统上无效）。配方对「2 处」这个数量做断言，上游改动会立刻暴露。
- 7 组 PKG_CHECK_MODULES 变量对逐个导出（比库本体多 REVENGE_GENERATORS 一组），
  每组 CFLAGS 与 LIBS 两半都必须非空 —— pkg.m4 对两半**分别**判空，任一半为空
  就会落回 `$PKG_CONFIG`；E468 记录了 conan 不把生成 .pc 的目录加入
  PKG_CONFIG_PATH，而已发布 .pc 的 libdir 是 `//lib`（E236 同源病灶）。
- 一处**被实测推翻**的猜测，因此没有留下对应的防御代码：最初以为
  `--with-tools` 探测失败会把 `with_tools` 静默降级成 no（表现为"构建成功但包里
  没有 bin/"），并为此写了 configure 之后读 `config.status` 的断言。核对本 dist
  的 configure 生成码后确认：`PKG_CHECK_MODULES([REVENGE_GENERATORS],[librevenge-
  generators-0.0])` 不满足时走 `as_fn_error "Package requirements
  (librevenge-generators-0.0) were not met"`，构建直接停在手 configure，故删掉
  那条断言。
- librevenge 经「只含 .a 的干净 -L 目录」链接（E236：.la 记录 //lib → libtool
  `library ... was moved` 硬错误）；icu4c 静态 .a 是 C++ 库，链接行必须带
  `-lc++`。
- SHELL/CONFIG_SHELL 候选顺序为 hnp bash → **PATH 上的 bash** → /usr/bin/zsh。
  照抄父配方的 `hnp bash → zsh → bash` 在真机会选中 zsh（真机没有
  `/data/service/hnp/bin/bash`），而父配方自己的注释就写着「automake 树绝不能
  用 zsh 当配方 shell」。toybox /system/bin/sh 也跑不了 autoconf 2.72 的
  `exec 7<&0`。
- CC/CXX 从 profile conf 显式导出（R33）；辅助脚本补 exec 位（E490）；TMPDIR
  指向构建目录内 `.tmp`（真机 /tmp 只读）。

## test_package（鸿蒙特有测试，消费者视角）

不链任何库（本包无 lib/），直接驱动交付的三个可执行文件，全部断言由
`test_libe_book_tools.sh` 自己计数并打印 `TOTAL=/PASS=/FAIL=`，任一条失败即
非零退出。覆盖面：

1. 交付结构：bin/ 存在、三个转换器都有可执行位、许可证随包交付，以及
   **本包不含 lib/ 与 include/**（把 W2 拆分本身变成可断言的事实）。
2. ELF 身份：用 `od` 读 magic 与偏移 18 的 `e_machine`（b700 = EM_AARCH64），
   不依赖设备上是否装有 readelf。
3. 真能跑：`--version` 退出码 0 且自报程序名（这一步同时证明 OHOS 内核放行
   exec，签名/RUNPATH 这一类问题会在这里暴露）。
4. 正向解析：就地生成两份真实语料 —— FictionBook 2（`FictionBook` 根元素 +
   `http://www.gribuser.ru/xml/fictionbook/2.0` 命名空间，命中 detectXML 的
   TYPE_FICTIONBOOK2）与 XHTML（同一函数另一条 TYPE_XHTML 分支），跑满三个
   工具的导出链路，并断言 `--info` 元数据通道。
5. 反向对照：一段非文档字节必须让三个工具都退出码 1 且报
   `has not been recognized`（上游 src/conv/text/ebook2text.cpp 的原文案）；
   text 输出里不得出现源文件的 `<FictionBook` / `<html` 标签，排除「把字节
   回显」这一类假绿；未知选项与无参数都必须按上游 `printUsage()` 的
   `return -1`（exit 255）非零退出。

CI L1e（把 bin/ 整个 mv 走后重跑 conan test）依赖第 1、3 类断言失败才成立。

## 真机取证

完整原件见同目录 `reports/test-report.md`。摘要（全部为 2026-09-20 真机本轮输出）：

- 隔离 `CONAN_HOME=~/work/psj/ch-lbk13140`（只读拷贝 `~/.conan2` 的
  profiles/settings.yml/remotes.json/global.conf，未写共享缓存）
- `CREATE_EXIT:0`；配方 rev `fb15f2f70e5ea83bca18e22aa23a8235`，包 ID
  `6083f91ceb24a67315a8f7fa27298fa9f983f224`
- 上游 `make -j1 check`：`PASS: test` + `# TOTAL: 1 / # PASS: 1 / # FAIL: 0 /
  # ERROR: 0`；`src/test/test.log` 逐用例 14 行 ` : OK` 末行 `OK (14)`
  → 与「dist 内 22 个 CPPUNIT_TEST 宏、本配置实编 14 个」的推断一致
- 消费者 `test_libe_book_tools.sh`：`TOTAL=46 PASS=46 FAIL=0`
- L1e 破坏性反向验证：`POS_EXIT:0` → 移走 `bin/` → `NEG_EXIT:1`（首条失败即
  `包内 bin/ 目录存在`，随后三个可执行位与 ELF 断言）→ 还原 `RESTORED_EXIT:0`
- 交付物：包内顶层只有 `bin`、`licenses`（+conan 自带的 conaninfo/conanmanifest），
  三个二进制 `e_machine=b700`，`NEEDED` = `libc++_shared.so` + `libxml2.so.16` +
  `libc.so`，`RUNPATH` 指向 libxml2 包目录
- 已知边界（实测）：最小 XHTML 语料被 `detectXML` 识别（stderr 无
  `has not been recognized`）但 `EBOOKDocument::parse` 返回非 OK → rc=1；
  上游 0.1.4 重写了这条链路。本包不改上游实现，只把该行为写成断言。

---
