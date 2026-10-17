# dicom3tools 1.00-20240118131615 — OHOS 适配说明

## 软件

David A. Clunie 的 DICOM 离线命令行工具集。本版本安装 **102 个 ELF 程序 + 19 个 `#!/bin/sh` 脚本 + 1 个上游自带的 0 字节脚本**，
外加 130 个 man 手册，覆盖创建、修改、转储、校验 DICOM 文件以及从各厂商私有格式
（GE、Siemens、Picker、Toshiba、Shimadzu、Imatron 等）转换。

## 构建系统：X11 imake

上游不使用 autotools/CMake，而是 **imake**（X11 的 Makefile 生成器）：

```
./Configure                      # 生成 config/generic.cf
imake -I./config <defines>       # 由 Imakefile + 模板生成 Makefile
make Makefiles                   # 递归生成 67 个子目录 Makefile
make depend                      # 生成派生表头 + 依赖
make                             # 编译 6 个内部静态库与全部程序
make install / install.man       # 安装（尊重 DESTDIR）
```

`imake`、`makedepend`、`mkdirhier` 不属于 dicom3tools，OHOS 上也没有发行包。
上游 `INSTALL` 明确给出获取位置：

> If you don't have imake, I suggest you get it from Paul DuBois's archive
> ... It is also probably at the site where you found dicom3tools.

因此配方把该归档（`https://www.dclunie.com/imake/imake.tar.gz`）作为第二个 source，
在 `build()` 内现场编译这三个工具，**只作构建工具，不进入制品**。

## 依赖

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| libx11 | 6.4.0 | dcdisp（X11 图像显示程序）与 libddply/libodply |
| libxext | 6.4.0 | 同上 |

libxext/6.4.0 依赖 libx11/6.4.0；`X11/X.h` 来自 libx11 传递依赖的 xorgproto。

## 补丁

| 补丁 | 类别 | 内容 |
| --- | --- | --- |
| 0001-configure-probe-compiler-capabilities | portability | Configure 改为编译探测 C/C++ 编译器与 C 库能力 |
| 0002-imakefile-xcomm-comment-lines | portability | 注释掉的配方行改用 XCOMM |
| 0003-support-awk-diagnostics-to-stderr | portability | awk 诊断写 stderr |
| 0004-imake-build-on-musl-and-modern-cpp | portability | imake 适配 musl 与现代 cpp |
| 0005-makedepend-build-on-modern-c | bugfix | makedepend 适配现代 C 库并修 64 位崩溃 |
| 0006-portable-userland-command-syntax | portability | sort 与 xargs 改用可移植语法 |

### 0001 Configure 改为编译探测

`Configure` 原本靠解析 `gcc -v` 的版本号决定用哪套 C++ 头文件与特性宏。
OHOS 上没有 `gcc`/`g++`（只有 clang），版本号解析全部失败，于是
`UseStandardHeadersWithoutExtension`、`EmitUsingStdNameSpace` 等保持 0，
编译随即因 `<iostream.h>` 不存在而失败。

补丁在 OS 分支之前插入一段编译探测：先确认 C/C++ 编译器真的可用
（`$CC`/`$CXX` → `clang`/`cc` → `clang++`/`c++`），再逐个探测
iostream 头文件形式、`std::streampos`、`infinity()`/`quiet_nan()`、
`gethostid()`、`tm_gmtoff`，以及编译器的默认 include 搜索路径
（供 makedepend 使用）。探测结果写进 `generic.cf`，由既有的 `#ifndef` 守卫
保证已有分支的结论优先。此外 `TMPROOT` 改为尊重 `TMPDIR`（设备 `/tmp` 只读）。

### 0002 注释掉的配方行

`Imakefile` 与 `appsrc/dconvert/signa/Imakefile` 里有以 TAB+`#` 开头、被注释掉的
配方行。现代 cpp 把它当预处理指令，报 `invalid preprocessing directive`。
imake 自己的 `CleanCppInput()` 只处理第 0 列的 `#`。改用 `XCOMM`（即 `#`）
让它穿过 cpp，生成物中的注释语义不变。

### 0003 awk 诊断写 stderr

`libsrc/support/*.awk`（12 个文件、85 处）把诊断写到 `/dev/tty`。没有控制终端时
gawk 把重定向失败当**致命错误**，在生成大表头的中途退出，留下截断的文件
（如 `ge9800hdrp.h` 缺右大括号），下游编译随即以 `missing '}' at end of definition`
一类错误成片失败。改为 `/dev/stderr`。

（该级联错误的具体条数来自探索期的一次构建，未保留对应轮次的日志，
故此处不给出数字；`85 处 / 12 个文件` 可由补丁本身复核：

```sh
grep -c '^+.*/dev/stderr' patches/0003-support-awk-diagnostics-to-stderr.patch   # → 85
grep -c '^+++' patches/0003-support-awk-diagnostics-to-stderr.patch              # → 12
```）

### 0004 imake 适配 musl 与现代 cpp

三处：

1. musl 没有 `sys_errlist[]`，改用 `strerror(errno)`；
2. `LogFatal()` 是隐式 `int` 返回类型，里面却有裸 `return;`，clang 直接报错；
3. `KludgeOutputLine()` 的 target 判据重写（见下）。

第 3 点是本次适配最关键的发现：cpp 会把多行宏调用内部的换行与制表符合并成一个
空格，imake 还原出的配方行只剩一个前导空格。imake 自带的修正逻辑（`FIXUP_CPP_WHITESPACE`，
`imakemdep.h` 只在 sun/SYSV/SVR4/hcx 下自动定义）用「行内是否含冒号」判断 target 行：

- 配方行不含冒号时补不上 tab → `*** missing separator`；
- 含冒号的对齐宏定义（`   PRIVCONFIGDIR = $(TOP)/config`）被当成 target 行、
  前导空格被剥掉 → 变量消失 → 子目录 imake 丢掉 `-I$(TOP)/config` →
  `fatal error: 'Imake.tmpl' file not found`。

补丁把判据收紧为「**首个空白分隔的词**里含冒号才算 target」，并把缩进行分成
配方行（单个前导空格 + 在规则内 → tab）与宏定义（`NAME = ` 形态 → 第 0 列）两类。

配套地，`CPP_PROGRAM` 指向读 stdin 的 `clang-cpp` 并加 `-P`：`-P` 既去掉行号标记，
也去掉 clang 为保持源码行号而插入的空行——那些空行会重置 imake 的 `InRule` 状态。

### 0005 makedepend 适配现代 C 库

1. `getline()` 与 POSIX `<stdio.h>` 的声明冲突 → 私有实现改名 `md_getline()`；
2. 若干函数有裸 `return;` 但返回类型隐式 `int` → 补显式 `void` 与原型；
3. `fatal()/warning()/warning1()` 声明了 10 个参数却只把第 1 个写成 `char *`，
   其余默认 `int`，在 64 位目标上把指针截断，**任何带 `%s` 的诊断都会段错误**
   （`makedepend: error: got signal 11`）→ 改用 `<stdarg.h>`。

### 0006 sort / xargs 改用可移植语法（CI 才暴露的问题）

上游到处使用 **POSIX.1-2001 之前的关键字语法**给 sort 指定键，并靠
`config/Imake.tmpl` 里的 `SortCmd = _POSIX2_VERSION=199209 sort` 让 GNU coreutils
接受它：

| 位置 | 原写法 | 现代写法 |
| --- | --- | --- |
| `libsrc/docs/Imakefile:5` | `$(SORT) -b +1 -2 +0 -1` | `$(SORT) -b -k2,2 -k1,1` |
| `libsrc/standard/Imakefile:39,53,105,146,152` | `$(SORT) -b -n +0 -1 +4 -5` | `$(SORT) -b -k1,1n -k5,5n` |
| `libsrc/standard/elmdict/Imakefile:35` | 同上 | 同上 |
| `libsrc/standard/Imakefile:23` | `sort -u -t , +2` | `sort -u -t , -k3` |

`_POSIX2_VERSION=199209` 只是 **GNU coreutils 的兼容开关**：其他实现不认这个变量，
也不接受 `+N -M`，会直接报

```
sort: Unknown option '2' (see "sort --help")
make[2]: *** [Makefile:192: modtype.txt] Error 2
```

同一条 `Imakefile` 还用了 `xargs -L 1`，toybox 同样不支持
（`xargs: Unknown option 'L' (see "xargs --help")`）；改用 POSIX 的 `-n 1`。
两处输入都是**不含空白的逗号连接行**（`name,iod,module,usage,,type,vm` 与
`name,ie`），因此对它们 `-L 1` 与 `-n 1` 完全等价。

**为什么设备上一直没发现**：设备 PATH 上的 `sort`/`xargs` 是 GNU coreutils，
接受这些写法；CI worker 用的是 OHOS 基础系统的 toybox。hnp 只提供
gawk / grep / clang 等，**不提供 sort、xargs、sed、cat、head、tail**，这些在 CI 上
一律落到 toybox。属 §11.1 记录的「设备全绿 ≠ CI 绿」。

**故障链**（CI 日志，全由 sort 一条引发）：

```
sort 失败 → modtype.txt 未生成 → libsrc/standard 的模板链断掉
          → elmdict.tpl 为空 → elmconst.h 只剩一行 #endif
          → 所有 TagFromName(XxxAttribute) 展开失败：
            "use of undeclared identifier 'OverlayRows_GROUP'"
```

报错最后落在 `dcdisp.cc` / `ge9800*.cc` 的**未定义标识符**上，与真正的原因
（排序命令）隔着三层，极易误判为「语法错误 / 缺链接库」。

**等价性验证**（设备实测，原始输出见 `reports/`）：

| 判据 | 结果 |
| --- | --- |
| `modtype.txt`（2591 行）busybox/toybox 新语法 vs GNU 旧语法 | 逐字节一致 |
| `elmdict/*.tpl` 全部 18 个文件 | 逐字节一致 |
| `iodandmodulerelationshipsbytag.dat`（合成样本） | 逐字节一致 |
| 全量原生构建（toybox sort + xargs + sed/cat/head/tail） | PASS，0 错误 |
| 上述构建产出的 `modtype.txt` / `elmdict.tpl` / `elmconst.h` vs Conan（GNU）产出 | 逐字节一致 |
| 修复前复现 | toybox/busybox 下 `rc=2`、0 行，报错与 CI 完全相同 |

这是**上游 Makefile 的可移植性缺陷**，不是 OHOS 特有：任何使用
busybox/toybox userland 的环境（Alpine、嵌入式、OHOS）都会命中。

## 构建参数

- `-DStripCmd=true` 且 `INSTPGMFLAGS=`：hnp clang 的产物带 `.codesign` 段，
  strip 后内核拒绝执行（退出码 126）。参见知识条目 E077。
- `-DX11IncludePath=<libx11 与 xorgproto 的 include>`：
  imake 展开成 `-I$(X11INCLUDEPATH)`，所以第二个及之后的目录自带 `-I`。
- `-DDisplayLoadFlags=<libx11 与 libxext 的 -L> -lX11 -lXext`。
- `TMPDIR` 指向构建目录：设备 `/tmp` 只读。
- `INSTALL` 用 `busybox install`：OHOS 基础系统没有 `install` 命令。
- `IMAKE`/`DEPEND`/`MKDIRHIER` 以绝对路径传给 make：make 的每条 recipe 都是新
  shell，且 `IMAKE_DEFINES` 里的值含空格，必须逐个加引号才不会被拆成多个词。

## 验证脚本的两条约定

`test_package/test.sh` 与 `reports/l2-consumer-test.sh` 都**刻意不用** code-style 要求的
`set -euo pipefail`，只用 `set -uo pipefail`：两者的多条断言要求「坏输入必须以非 0 退出」
（`dcdump` 截断数据集 rc=1、`dciodvfy` 非 DICOM rc=1），启 `-e` 会让脚本在断言判定之前
就退出，反而掩盖结果。失败状态由各自末尾的 `[ "$fail" -eq 0 ]` 兜底，因此
「有断言失败则整体非 0 退出」这一性质仍然成立。两处代码内均有同样的注释说明。

`make test` 的退出码恒为 0（顶层 recipe 是 `for` 循环，见上），不能作为通过证据；
本 PR 的通过判定一律基于测试脚本自己的 PASS/FAIL 计数与退出码。

## 上游测试

口径：**测试驱动调用点**（`support/testapp` 调用 + 独立测试脚本调用）。
候选值实测为 0（无单元测试框架）/ 21（`test::` 目标）/ 21（`test.create::` 目标）/
16（`test::` 具名子目标）/ 2（`test.create::` 具名子目标）/ 148（compare 模式 testapp）/
148（create 模式 testapp）/ 296（全部 testapp，词法口径）/ 288（仅 `test::` 可达的 testapp）/
12（脚本驱动调用点）/ **308（采纳值 = 296 + 12，取最大值）**。
取数命令与逐项归因见 `test_package/MANIFEST.yml` 的 `upstream_test_counts`。

关键点：脚本驱动数**必须用与脚本名无关的枚举**取得。按脚本名硬编码三个名字
（`binpatch.test.sh` / `test.create.ut.sh` / `testy2k.sh`）只能看到 8 处，会漏掉
`test.create.private.un.sh` ×2 与 `testy2k.antodc.sh` ×2 —— 这正是此前 N=304 的少报根因
（304 = 296 + **8** 用了不完整的脚本枚举）。正确枚举：

```sh
grep -rnE '^[[:space:]]*(@)?\./[A-Za-z0-9_.-]+\.sh' --include=Imakefile . \
  | grep -v ':[[:space:]]*#' | grep -v makedcdtchgheader | wc -l    # → 12
```

（`appsrc/dcfile/Imakefile:190` 的 `./makedcdtchgheader.sh` 是构建步骤而非测试驱动，已排除。）

```text
TOTAL = PASS + FAIL + SKIP + NOT_RUN = 0 + 0 + 0 + 308 = 308
```

**判定口径**（避免 FAIL/NOT_RUN 混用）：`FAIL` 只记「驱动真的执行了比对并给出不符结论」；
只要驱动在达到比对之前就被阻断，一律记 `NOT_RUN`——因为此时没有任何比对结论可言，
把环境阻断记成 FAIL 会把「平台限制」说成「测试失败」。

- **PASS 0 / FAIL 0 / NOT_RUN 308**：全部 308 个驱动点都在**比对执行之前**被阻断，具体两类：
  1. **夹具目录不存在**（296 个 testapp 调用）：上游把夹具 `images/` 与 `test/` 作为独立归档
     分发，该归档在官方站点上不存在（任何日期均 HTTP 404，索引中 0 条匹配），
     第三方镜像与 Debian 打包同样没有；日志中出现 19 次 `no such image directory`，涉及 19 个目录。
  2. **脚本驱动硬编码 `/tmp`**（12 个脚本驱动点中的 2 类）：`appsrc/misc/binpatch.test.sh`
     把临时目录写成 `/tmp/binpatch.test.sh.$$`，设备 `/tmp` 只读 → 被测程序 `binpatch`
     abort（`File open for write failed`），脚本随后报 `nothing stored to compare binary/od`；
     `appsrc/acrnema/test.create.ut.sh` 与 `test.create.private.un.sh` 的 `mkdir //tmp/<script>.$$`
     失败 → 每条 `cmp`/`diff` 都指向不存在的文件。**两者都从未产出比对结论**，
     故同为 NOT_RUN（`binpatch.test.sh` 的被测二进制确实被调用并 abort，这条原始输出保留在
     逐字日志里，可佐证「不是静默跳过」）。

  另 148 个 create 模式调用是**生成比对基准**而非比对本身，按最大口径仍计入 N。

**`make test` 的退出码恒为 0，不能作为通过证据**——原因已实测定位（见
`reports/make-test-exit-code-probe.md`）：顶层 `test::` 的 recipe 是
`for i in $(SUBDIRS); do (cd $$i; $(MAKE) ... test); done`，
**shell 循环的退出状态等于最后一次迭代的状态**，子目录失败不会向上传递；
实测同一次运行中 **22 条 `*** Error` 与 `rc=0` 并存**。本 PR 未把该退出码记为 PASS。

取证见 `reports/upstream-test-evidence.md`（分析）、`reports/upstream-test-probe.md`
（404 探测原始响应）、`reports/upstream-make-test-evidence.md`（日志逐字留档）。

本 PR 用 `test_package/test.sh` 对同一批已安装产物做端到端验证（22 项断言全部通过），
另用 `reports/l2-consumer-test.sh` 覆盖像素导出/导入回环等更深链路（36 项全部通过），
合计 58 项即「鸿蒙特有测试」行的取数。

## 上游工具的两处设计行为（写测试时必须知道）

1. `dcstats` 输出的是**像素值统计**（min/max/mean/Bits Stored），不是模块属性列表；
   断言 `Rows`/`Columns` 会失败，那是 `dcdump` 的职责。
2. `dcdump` 对**任意字节流都返回 0**：它按设计支持没有 Part 10 头的旧格式，会做字节序
   与 VR 自动识别。实测把 `this is not a dicom file at all\n` 解析成
   `(0x6874,0x7369) VR=<UN>`（"th"/"is" 的小端读法）。因此"拒绝坏输入"的判据只能用
   结构校验器 `dciodvfy`。同理，`dcsmpte -rows 32 -columns 32` 会触发上游断言
   `right_col >= bitmap_cols` 而 abort，测试图尺寸需 ≥ 256。

## 验证结果

| 项目 | 结果 |
| --- | --- |
| `conan create`（清缓存干净轮） | PASS（`linked 102 programs`；6 条 `Apply patch`、5 条 `RUN: make`、1 条 `Calling build()`） |
| `test_package` | PASS 22/22 |
| 上游测试 | TOTAL 308 / PASS 0 / FAIL 0 / SKIP 0 / NOT_RUN 308（夹具未分发 + 脚本硬编码 /tmp，见上述取证与判定口径） |
| W3 本地 CI 模拟 | L0/L1/L2/L5 pass，L4 warn（warn 对象是补丁文本里的危险函数，非产物） |
| L2 消费者实测（人工补测） | PASS 36/36 |
| L4 静态安全属性（人工补测） | PASS 102/102 ELF |
| G4 产物与 package_info 互证 | PASS（bin 122 = 102 ELF + 19 shebang 脚本 + 1 个上游 0 字节脚本 `himrunid`；man1 130） |
| L5 产物基线 | 七轮清缓存构建两条稳定聚合逐字节一致，122 项逐产物基线与采集基线 diff 无输出，见 `reports/conan-verify-supplement.md` |

`conan-verify` 的报告里 G4 报 `⚠️ 无法找到程序包 ID`、L2/L4/L5 报
`⏭️ 跳过（无 cache 路径）`（工具缺陷，第 17 节已登记），因此上述四项均为人工补测，
证据在 `reports/conan-verify-supplement.md`、`reports/l2-consumer-test.sh` 与
`reports/l2-consumer-test-evidence.md`。

实跑命令与日志见 `manifest.yaml` 的 `validation` 段与 `reports/`（全部证据为 `.md`/`.sh`/`.sha256`，原始 `.log` 不入库，见 `.gitcode/review-memory.md` §19）。
