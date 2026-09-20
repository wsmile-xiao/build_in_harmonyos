# 测试报告 — rlog 1.4

> **项目**: rlog 1.4
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS HongMeng Kernel（aarch64-linux-ohos，OHOS SDK 26.0.0.18，clang 15.0.4）
> **测试类型**: 上游 noinst 程序（设备实跑）+ 消费者测试（conan test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游注册测试（`make check`） | 0 | - |
| 上游可运行程序（noinst） | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 消费者测试断言 | 11 | 100% |

**核心功能通过率**: ✅ **2/2 上游程序 + 11/11 消费者断言（100%）**

> 分母说明：上游 `make check` 不注册任何测试（`rlog/Makefile.am` 只有
> `noinst_PROGRAMS = test testlog`，无 `TESTS` 变量），因此上游分母为 0/0；
> 上表的 2 是「上游随源码提供、可实际运行的程序数」，两者不混算。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 上游两个程序与消费者测试全部通过；库产物（共享库、头文件、pkg-config、文档）齐全。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 2007 版 config.guess 不认识 HarmonyOS（裸 configure 无 build type） | configure 阶段，已用补丁 0001 解决 | 🟢 |
| 2006 版 autoconf 的 C++ 候选表不含 clang（设备无 g++/c++） | configure 阶段，已用补丁 0002 解决 | 🟢 |
| HMDFS 权限/工具限制（config.status 临时目录、make jobserver fifo、libtool wrapper 相对路径） | 构建/运行阶段，已用补丁与 -j1、直跑 .libs 二进制解决 | 🟢 |

### 2.3 可用功能清单

```
✅ 通道体系（GetGlobalChannel/RLOG_CHANNEL、层级与过滤）
✅ 订阅-发布链路（RLogNode::addPublisher/isInterested/publish）
✅ 日志级别宏（rDebug/rWarning/rError/rLog）与格式化
✅ 断言机制（rAssert/rAssertSilent → rlog::Error，含 file/line/function/component）
✅ 计时 API（rlog_get_time/rlog_time_diff/rlog_time_unit）
✅ 共享库链接与消费者编译（CMakeDeps + rlog::rlog）
```

### 2.4 已知限制

1. 上游未注册 `make check` 测试套件；本仓库通过 build() 运行两个 noinst 程序补齐运行证据。
2. `test` 程序内含一次**故意**的断言失败（验证断言机制），stderr 会出现预期内的
   "Assert failed"，退出码为 0。
3. W3 的 L4 静态安全扫描对补丁文件给出 `gets` 命中警告，经核对是**误报**：
   config.guess 补丁的上下文注释中出现单词 "targets"，被 `gets\b` 规则命中；
   本包未引入任何 `gets()` 调用（纯 C++ 库，上游源码亦无 gets）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| rlog/test（上游 noinst，build() 内实跑） | 订阅-发布、rDebug/rWarning/rError、rAssert→Error 位置信息、计时 API（4×sleep(1) 实测 ≈1003 ms/次） | ✅ PASS (exit 0) |
| rlog/testlog（上游 noinst，build() 内实跑） | 200 条 warning 的调用开销基准（dormant 与 active 两条路径） | ✅ PASS (exit 0) |
| test_package/test.cpp（消费者，11 项断言） | 版本符号、通道注册/命名、订阅-发布、通道层级与过滤、rAssert→Error、计时 API | ✅ PASS (11/11) |

消费者测试逐项结果：

```
[PASS] RLogVersion() matches CURRENT_RLOG_VERSION
[PASS] GetGlobalChannel returns the requested channel name
[PASS] channel lookup returns the same instance
[PASS] subscribed node receives messages published to the channel
[PASS] message formatting (%d) is applied
[PASS] sub-channel messages reach the parent channel subscriber
[PASS] messages from an unrelated channel are filtered out
[PASS] rAssert error reports the consumer source file
[PASS] rAssert(false) throws rlog::Error
[PASS] rlog_get_time/rlog_time_diff are usable
[PASS] rlog_time_unit reports a unit
rlog consumer test: checks=11 failures=0
```

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（上游文档构建需要 doxygen/latex，环境无该工具链时 docs 的 doxygen 规则不注册，
但预生成的 html/refman.pdf 仍按上游 Makefile.am 正常安装）。

---

## 四、关键问题分析

### 问题1: 裸 `./configure` 无法确定平台与 C++ 编译器

**现象**（G0 干净构建验证，两次实测）：

```
config/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
# 加补丁 0001 后继续，又出现：
configure:2846: g++    conftest.cpp  >&5
./configure: g++: inaccessible or not found
configure: error: C++ compiler cannot create executables
```

**根因分析**：上游 tarball 的 `config/config.guess` 为 2007 版（早于 aarch64 与
HarmonyOS），设备实测直接运行返回 exit 1（`unable to guess system type`）；即使补上
平台识别，2006 版 autoconf 生成的 configure 的 C++ 编译器候选表为
`g++ c++ gpp aCC CC cxx cc++ cl.exe FCC KCC RCC xlC_r xlC`，**不含 clang**，设备上也
没有 g++/c++，于是 configure 退化为不存在的 g++。配方经 `AutotoolsToolchain` 显式给
CXX 时不受影响（所以 conan create 一直能构建）。

> 附核（W4 审计 P1 修正后）：自带 `config/config.sub` 经设备实测**接受**本配方使用的
> `aarch64-unknown-linux-gnu`（exit 0；仅 `*-ohos` 形式被拒），因此无 config.sub 补丁。

**解决方案**：补丁 0001 让 config.guess 在 `HarmonyOS:aarch64` 上直接给出
`aarch64-unknown-linux-gnu`；补丁 0002 在 configure 的两处候选表前加入 `clang++`。
两者都只影响裸 `./configure` 路径，与配方的显式三元组/CXX 设置一致。

### 问题2: config.status 临时目录在 HMDFS 上不可写

**现象**：
```
./config.status: line 908: ./confDGDhIE/out1: Permission denied
./config.status: line 911: ./confDGDhIE/config.h: Permission denied
make: *** No targets specified and no makefile found.  Stop.
```

**根因分析**：configure 生成的 config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")`
创建 0700 临时目录，HMDFS 上该目录内写入被拒绝，导致 config.h 与各 Makefile 生成失败，
随后 make 找不到 Makefile。

**解决方案**：补丁 0002 将该分支改为 `(umask 022 && mkdir "$tmp")`（归档先例：a52dec
0002-configure-umask-022.patch、libagg 同类内联改写）。

### 问题3: 并行 make 的 jobserver fifo 不可创建

**现象**：
```
make: jobserver mkfifo: /storage/Users/currentUser/ws/tmp/rlog-1.4/tmp/GMfifo20103: Operation not permitted
```

**根因分析**：GNU make 在多作业模式（-jN）下需要 mkfifo 创建 jobserver fifo，
HMDFS 不允许 mkfifo。

**解决方案**：配方使用 `autotools.make(args=["-j1"])` 串行构建（12 个源文件，代价可忽略）。

### 问题4: VPATH 构建下 docs 安装路径失效

**现象**：
```
installing to .../share/doc/rlog/html
/bin/sh: ../mkinstalldirs: No such file or directory
make[2]: *** [Makefile:399: install-data-local] Error 127
```

**根因分析**：docs/Makefile.am 的 install-data-local 使用相对路径 `../mkinstalldirs`
与 `html/*`，假设在源码树内构建；Conan 的 autotools 构建为 VPATH 构建（build 目录 ≠
源码目录），这两个相对路径都不存在。

**解决方案**：补丁 0003 改用 `$(top_srcdir)/mkinstalldirs` 与
`$(INSTALL_DATA) $(srcdir)/html/*`，保留上游文档安装行为。

### 问题5: libtool wrapper 运行上游程序时 relink 失败

**现象**：
```
rlog/1.4@ohpcd/stable: RUN: ./rlog/test
shell-init: error retrieving current directory: getcwd: cannot access parent directories
clang-15: error: no such file or directory: 'test.o'
clang-15: error: no such file or directory: './.libs/librlog.so'
```

**根因分析**：libtool wrapper 记录的 relink 命令形如
`(cd ; ... -o $progdir/$file test.o ./.libs/librlog.so)`（**cd 无参数**），
在 HMDFS 上 getcwd 失效时 wrapper 走 relink 分支、相对路径无法解析，clang 报错退出。

**解决方案**：配方直接执行 `.libs/test`、`.libs/testlog` 真实二进制，并显式
`LD_LIBRARY_PATH=<build>/rlog/.libs`（设备复测两者 exit 0）。

---

## 五、测试环境

```
软件: rlog 1.4（LGPL-2.1-or-later，上游 tarball sha256 a938eeed…）
构建系统: autotools（上游自带 configure）
工具链: OHOS SDK 26.0.0.18 / clang 15.0.4 / GNU make 4.4.1
conan: 2.29.1（OHOS 适配版）, profile ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, arch=armv8）
验证命令: conan create archives/r/rlog/1.4 -pr:h=<profile> -pr:b=<profile> --build=missing
```

---

*报告生成时间: 2026-09-18*
