# rio 1.07 适配笔记

## 软件概况

- 上游：rio 1.07 — The Snowblind Alliance (c) 1999（Ashpool Systems）
- 用途：Diamond Rio PMP300 便携 MP3 播放器的命令行管理工具。通过**并口**（默认 0x378）
  与播放器通信，实现目录显示、上传/下载、删除、初始化、播放列表排序。
- 许可证：GPL-2.0-only（源码包内 gpl.txt 为 GPL v2 原文）
- 源码：`https://deb.debian.org/debian/pool/main/r/rio/rio_1.07.orig.tar.gz`
  （sha256 `e0426cd1dc90acb1aae6a647f5e65168c345fc262456a47dba5ff1a2cae1ab6b`，
  原作者站点早已失效，Debian pool 保存的是未修改的 pristine orig 包）
- 构建系统：纯 makefile（无 configure），源码 20 个文件、约 3.7k 行
- 编译环境：clang 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK 26.0.0.18 + musl）
- 状态：built（conan create + conan-verify + W3 本地 CI 全绿，未 upload）

## 上游测试入口核验（R51 第一步）

rio 1.07 **没有自动化测试**，证据：

```bash
$ make -n check
make: *** No rule to make target 'check'.  Stop.
$ make -n test
make: *** No rule to make target 'test'.  Stop.
$ grep -n '^[a-zA-Z].*:' makefile
9:all: 		rio
11:rio:		app.cpp rio.cpp
15:clean:
$ find . -type d
.
```

- 源码包内唯一目录就是源码根目录，无 `tests/`、`test/`、`t/`；
- 无 configure / CMakeLists.txt / ctest / pytest 注册；
- README 的 "Building and running" 仅给出 DOS / OS2 / Win9x / WinNT / Linux 五个平台的
  编译方法，不含任何测试命令；
- 该工具全部功能依赖真实并口连接的 Diamond Rio PMP300 硬件，上游从未提供软件侧的
  模拟器或测试桩。

因此"上游测试统计"为 0/0，如实上报，不用 test_package 冒充上游覆盖（R51 第三步）。
上游真实可执行的"入口"只有无参数运行打印的用法/默认值，以及各参数解析路径，
本次已在 `test_package/test.sh`（6 条）中实跑。

## 编译步骤

```bash
# 1. 打补丁（6 个，见 patches/）
cd $BUILD_SRC_DIR
for p in patches/*.patch; do patch -p1 < $p; done   # 由 apply_conandata_patches() 自动完成

# 2. 编译
make -j1 CXX=/data/service/hnp/bin/clang++
#   -> rio: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# 3. 干净构建验证（G0，等价于 gcc/autotools 项目的 configure && make && make install）
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=<staging>
#   -> <staging>/$DEFAULT_PREFIX/bin/rio

# 4. 验证
./rio                       # 打印版本横幅 + 用法表（默认端口 0x378，延时 20000/100/2）
./rio -d                    # open( /dev/port ) failed, reason 'No such file or directory'
RIO_PORT_DEVICE=<file> ./rio -d   # device not found（端口后端正向路径）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `rio.cpp:69: fatal error: 'sys/perm.h' file not found` | `<sys/perm.h>` 是 x86 Linux 专有头文件，OHOS（musl）没有；同时 `<asm/io.h>` 亦不存在，且 OHOS 的 `<sys/io.h>` 只是空壳（`bits/io.h` 为空），`ioperm()/inb()/outb()` 全部未声明 | 0003 补丁：把 `__linux__` 分支按架构拆分——`__i386__/__x86_64__` 保留 ioperm/outb/inb；其余架构改用 `/dev/port` 字节流后端（`pread/pwrite`，偏移=端口号）。**注意不能用 `__has_include(<sys/io.h>)` 探测端口能力**，因为该头在 aarch64 上存在但为空 |
| 2 | 序列化目录结构在 aarch64 上尺寸错误（`CDirHeader` 516 字节而非 512） | `SIGNED32/UNSIGNED32` typedef 成 `long/unsigned long`，ILP32 上恰好 32 位、LP64（aarch64）上是 64 位 → 目录头/目录项/512 字节块尾结构全部错位，校验和与并口写入数据全错 | 0004 补丁：改为 `int/unsigned int`，并用 `static_assert` 在编译期锁定 512/128/16 字节 |
| 3 | `undefined symbol: sys_errlist` / 编译告警 | `sys_errlist[]` 已被 glibc(>=2.32) 与 musl 移除 | 0005 补丁：`SZERROR` 改为 `strerror(errno)` |
| 4 | app.cpp 6 处 printf 格式串与实参类型不匹配 | `%08lx`/`%ld` 配 `int` 实参，在 LP64 下可变参数读取 8 字节（未定义行为）；`%-5hd` 配 `int` | 0001 补丁：修正格式串与显式 `(long)` 转换 |
| 5 | 使用已被移除的 `<values.h>` 与内核内部头 `<linux/limits.h>` | glibc 2.30 起移除 `values.h`；`linux/limits.h` 属内核内部头（OHOS musl 恰好还留着，但不该依赖）；且源码其实不需要 values.h 里的任何宏 | 0001 补丁：改为 `<limits.h>`（PATH_MAX） |
| 6 | 上游 makefile 硬编码 `g++` 且 `chmod +s rio` 设置 setuid root | 1999 年为以非 root 身份调用 `ioperm()` 而提权 | 0002 补丁：使用 `$(CXX)/$(CXXFLAGS)`；去掉 `chmod +s`（HarmonyOS 拒绝 setuid 可执行文件；新后端也不需要 root） |
| 7 | `rio.cpp` 3 处 `-Wsign-compare` 告警 | 上游原有代码风格（`int` 与 `sizeof()` 比较） | 与平台适配无关，未修改（保持补丁最小化） |
| 8 | finish 的 G0 干净构建验证 `./configure` 报 exit 127（`./configure: not found`） | rio 是纯 Makefile 项目，没有 autotools configure；G0 管线固定执行 `./configure && make && make install` | 0002 补丁新增 `configure` wrapper（解析 `--prefix=` 写入 `config.mk`，makefile `-include`），0003 补丁给 makefile 加 `install` 目标。此后 G0 完整跑通 `configure && make && make install`，证明补丁自包含、可从 pristine tarball 复现构建（仓库既有惯例：progress 0.17 / hints/configure） |

## OHOS 平台适配说明（实质性）

1. **端口 I/O 抽象（核心）**：aarch64 根本没有 ISA I/O 端口空间，x86 的 `outb/inb`
   内联汇编在该架构上不可能编译或运行。补丁提供了基于 `/dev/port` 的可移植端口
   后端：`/dev/port` 是字节可寻址的字符设备，文件偏移即端口号，`pread/pwrite` 即可
   完成端口读写。x86 上仍优先使用原生 `ioperm()+outb/inb`（保留原行为）。
   - 这是"能力缺失 + 可移植替代"，不是空壳 stub：`Set()` 会真实 `open()` 该设备，
     失败时返回 `CRIO_ERROR_IOPRERM` 并给出 `strerror()` 文案；
   - `RIO_PORT_DEVICE` 环境变量可把端口后端指向任意字节可寻址文件（诊断用/非
     `/dev/port` 暴露的硬件），这使得端口后端在**没有并口硬件、也没有 /dev/port
     的 OHOS 设备上依然可被真实执行和验证**（见 test_ohos.sh 断言 12/13）。
2. **LP64 数据模型**：见问题 2，用 `static_assert` 把 32 位协议布局固化为编译期约束。
3. **libc 差异**：musl/OHOS 的 `sys_errlist`、`values.h`、`sys/perm.h`、`asm/io.h`
   差异全部按"能力探测/标准头"方式解决，未引入任何 `__OHOS__` 平台宏
   （patches 中无平台宏，符合 R8/PF5）。

## 依赖

无第三方依赖（仅 C/C++ 运行时库）。W0/R36：`requires` 为空，无需 `conan download` 验证。

## 验证结果

```text
$ file rio
rio: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ ./rio | head -3
Rio utility v1.07 - The Snowblind Alliance (c) 1999
----------------------------------------------------
command line switches available :-

$ make CXX=clang++ CXXFLAGS="-O1 -Wall -Wextra"
app.cpp / rio.cpp：0 error；仅 3 条上游原有的 -Wsign-compare 告警
（static_assert 512/128/16 字节在 LP64 下通过）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rio | Diamond Rio PMP300 管理工具（aarch64 ELF，约 46 KB） |

## 注意事项

- 无并口硬件/无 `/dev/port` 时，工具会明确报
  `open( /dev/port ) failed, reason 'No such file or directory'` 并正常退出（不崩溃）。
- 退出码沿用上游语义（`FALSE == 0`），故失败路径返回 0；本次适配未改变上游退出码，
  测试按输出文案与"未被信号终止"判定，不按退出码判定。
- 上游 1999 年原始站点（`sba@tessier-ashpool.cix.co.uk`）已不可达，源码以 Debian
  pool 的 pristine `orig.tar.gz` 为准。
---

**编译结束**: 2026-09-29 09:39
**最终状态**: built

## 对话记录

### 对话 #1 [2026-09-29]

- 问题: `rio.cpp:69:12: fatal error: 'sys/perm.h' file not found`（首个编译错误）
- 操作: 定位为 `__linux__` 分支用了 x86 专有头；实测 OHOS 上 `sys/perm.h` / `asm/io.h` 均不存在，
  而 `sys/io.h` 存在但为空壳（`bits/io.h` 为空），故 `__has_include` 探测会假阳性
- 结果: 0004 补丁按架构分派端口后端（x86 保留 ioperm/outb/inb，其余架构走 /dev/port 字节流）

### 对话 #2 [2026-09-29]

- 问题: 序列化目录结构在 aarch64 上大小错误（`CDirHeader` 516 而非 512 字节）
- 操作: 发现 `SIGNED32/UNSIGNED32` 被 typedef 成 `long/unsigned long`（ILP32 上恰好 32 位，LP64 上 64 位）
- 结果: 0005 补丁改为 `int/unsigned int` 并加 `static_assert` 锁定 512/128/16 字节；LP64 printf 格式串
  缺陷（6 处）在 0001 补丁一并修正

### 对话 #3 [2026-09-29]

- 问题: finish 首次运行 conan-verify G2 失败：`source/target file does not exist: --- b'a/configure'`
- 操作: 定位为 OHOS 上 GNU `patch --dry-run` 会真实创建 0 字节新文件，污染 `.orig` 基线，使
  refresh-patch 把新增 `configure` 当成"已存在文件"生成 `--- a/xxx` 形式（命中既有知识 E484/E254）
- 结果: 每次 refresh-patch/finish 前删除 `.orig` 下的占位文件 + `conan remove rio/1.07* -c` 清缓存，
  生成后校验补丁头为 `--- /dev/null`；G2 复跑通过

### 对话 #4 [2026-09-29]

- 问题: finish 的 G0 clean-verify 直接执行 `./configure`（exit 127），因为 rio 是纯 Makefile 项目
- 操作: 按仓库既有惯例（progress 0.17 / hints/configure）新增 0002-configure.patch（configure wrapper
  写 config.mk）+ 0003-makefile.patch 的 install 目标
- 结果: G0 完整跑通 `configure --prefix=... && make && make install`，证明补丁自包含、可从 pristine
  tarball 复现构建（`.g0-verified` 已生成）

### 对话 #5 [2026-09-29]

- 问题: W3 的 L4 静态扫描报 `dangerous functions in patches`（0005-rio.h.patch）
- 操作: 复查为误报——注释英文 "64 bit targets." 中的子串 `gets\b` 命中了 L4 的
  `(strcpy|sprintf|gets|strcat)\b` 正则
- 结果: 改写注释为 "LP64 (64 bit) systems." 后 L4 恢复 pass；同时删除补丁备份目录避免噪音
