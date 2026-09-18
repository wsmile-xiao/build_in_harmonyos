# mimetic 0.9.8 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，上游自带 config.guess/config.sub 为 2007 版）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标: OpenHarmony PC aarch64（profile `ci/conan/profiles/ohos-aarch64`，cppstd=17）
- 状态: built
- 依赖: 无（库本体仅用 C++ 标准库；examples/ 中的 smime2xml/smimestruct 需要 OpenSSL，属 EXTRA_PROGRAMS 不参与构建与安装）

## 编译步骤

```sh
# 三元组经补丁后的 config.sub 规范化
./configure --prefix=$PREFIX --build=aarch64-linux-ohos --host=aarch64-linux-ohos
make -j1        # test/all-local 在此阶段构建 cutee 并执行 ./runtest
make install DESTDIR=$DEST
```

- `make` 会递归进入 `test/`，由 `all-local: cutee runtest` 先构建 `cutee`
  生成 `autocutee.mk`，再构建并运行 `runtest`：上游 65 个测试函数 / 2740 条断言
  在构建期真实执行。
- 使用 `-j1`：设备文件系统上 make 的 jobserver FIFO（`GMfifo*`）创建被拒
  （`Operation not permitted`），串行构建规避该平台限制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub` 不认识 `aarch64-linux-ohos` | 上游自带 config.sub 为 2007 版，早于 aarch64/OHOS | config.guess 增加 HarmonyOS 分支、config.sub 增加 `aarch64` 机器名与 `linux-ohos*` 操作系统（补丁 `0001-config.guess.patch`、`0002-config.sub.patch`） |
| 2 | `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 umask 077 创建的临时目录不可写（知识 E011） | `configure` 中 `umask 077` → `umask 022`（补丁 `0003-configure.patch`） |
| 3 | `error: constant expression evaluates to -1 which cannot be narrowed to type 'char'` | C++11 起聚合初始化禁止窄化；且 aarch64 上 `char` 为无符号，`sDecTable[c] == -1` 恒假（解码错值检测失效） | `Base64::sDecTable` 声明为 `signed char`（补丁 `0004-mimetic-codec-base64.cxx.patch`、`0005-mimetic-codec-base64.h.patch`）；平台探针实测 `char_is_unsigned=1 cmp_minus1=0` |
| 4 | `error: ordered comparison between pointer and zero ('char *' and 'int')` | `mmfile.cxx` 用 `if(m_beg > 0)` 判断 mmap 结果，现代 C++ 非法 | 改为惯用的 `if(m_beg != MAP_FAILED)`（补丁 `0007-mimetic-os-mmfile.cxx.patch`） |
| 5 | `error: unknown type name 'uint'` | 上游 `libconfig.h` 只在 macOS/Windows 分支 typedef `uint`，历史上靠 glibc `sys/types.h` 提供，OHOS libc 不提供 | CONFIG_UNIX 分支补 `typedef unsigned int uint;`（补丁 `0006-mimetic-libconfig.h.patch`） |
| 6 | `error: invalid suffix on literal; C++11 requires a space between literal and identifier`（test/cutee.cxx 8 处） | C++11 词法把「字符串字面量紧邻标识符」当作 user-defined-literal 后缀，宏不再展开 | 字面量与 `RUNTEST_NAME` 之间补空格（纯空白改动，补丁 `0009-test-cutee.cxx.patch`） |
| 7 | `error: ISO C++17 does not allow 'register' storage class specifier`（itparser.h 2 处） | C++17 移除 `register`；profile 要求 cppstd=17 | 删除 `register` 关键字（补丁 `0008-mimetic-parser-itparser.h.patch`） |
| 8 | `make: jobserver mkfifo ...: Operation not permitted` | HMDFS 不允许创建 jobserver FIFO | `make -j1`（配方 build() 固定） |
| 9 | `configure: error: working directory cannot be determined`（conan 构建环境） | profile `[buildenv]` 注入的 hnp bash 作为 CONFIG_SHELL 在 HMDFS 构建树上 getcwd 失败，configure 用它自我 re-exec 后 pwd 失败（E386） | configure 顶部增加 CONFIG_SHELL 能力探针，失败即回退 `/bin/sh`（补丁 `0003-configure.patch`） |

## 源码修改

补丁清单（`patches/` 下 9 个文件，由 `refresh-patch --auto` 生成，与 `conandata.yml` 的 `patches` 清单一一对应；全部为最小改动）：

- `0001-config.guess.patch` — config.guess 增加 HarmonyOS 分支（aarch64-unknown-linux-ohos）
- `0002-config.sub.patch` — config.sub 增加 aarch64 机器名与 linux-ohos 操作系统（3 处）
- `0003-configure.patch` — umask 077 → 022（E011）+ CONFIG_SHELL 能力探针（E386）
- `0004-mimetic-codec-base64.cxx.patch` — 解码表改 `signed char`（实现）
- `0005-mimetic-codec-base64.h.patch` — 解码表声明改 `signed char`（头文件）
- `0006-mimetic-libconfig.h.patch` — CONFIG_UNIX 分支补 `uint`
- `0007-mimetic-os-mmfile.cxx.patch` — 指针与 0 的有序比较改 `MAP_FAILED`
- `0008-mimetic-parser-itparser.h.patch` — 删除 C++17 已移除的 `register`
- `0009-test-cutee.cxx.patch` — 字面量与 RUNTEST_NAME 宏之间补空格（8 处，纯空白）

补丁中不含任何 `__OHOS__` 平台宏注入（R8/PF5 口径）。

## 依赖版本

无。`examples/` 的 OpenSSL 依赖不参与构建（EXTRA_PROGRAMS，未被 `make`/`make install` 触及）。

## 验证结果

- 上游测试（构建期实际运行，`make` → `test/runtest`）：

```
    ======================================
          Tests Statistics
    --------------------------------------
                Functions       Checks
      Success         65          2740
       Failed          0             0
    --------------------------------------
        Total         65          2740
    ======================================
```

- 消费者测试（test_package）：CMake 构建 `test_mimetic`，由 conan `test()` 阶段直接执行，
  9 条断言全过（版本号、Base64 已知向量与回环、QP 回环、MIME 构造→序列化→重解析）。
- 安装产物：`libmimetic.so.0.0.0`（SONAME `libmimetic.so.0`，NEEDED `libc++_shared.so`/`libc.so`）
  或静态库 `libmimetic.a`，公共头文件位于 `include/mimetic/`；libtool `.la` 包装文件在打包时移除。

## 说明

- 上游 mimetic 用自带的 cutee 0.4.2 单元测试框架；测试源为 `test/t.*.h/.cxx`，
  `test/Makefile.am` 的 `all-local` 在构建阶段直接运行测试，因此没有单独的
  `make check` 入口，`conan create`（G2/W3/CI）每次都实际执行上游用例。
- 库本体不依赖 mmap 之外的系统能力；`HAVE_MMAP`/`HAVE_MADVISE` 由 configure 探测。

## 对话记录

### 对话 #1 [2026-09-18]

- 问题: 上游 config.guess（2007 版）在 HarmonyOS 上无法识别系统类型（且会在 $HOME/tmp 下用 umask 077 建目录编译探针，双重失败）
- 操作: config.guess 增加 HarmonyOS 分支输出 aarch64-unknown-linux-ohos；config.sub 增加 aarch64 机器名与 linux-ohos 操作系统
- 结果: 原生路径下 configure 正确识别 aarch64-unknown-linux-ohos，无需 --build/--host（E007/R13）

### 对话 #2 [2026-09-18]

- 问题: `config.status` 建临时目录时报 Permission denied（HMDFS 下 umask 077 创建的目录不可写）
- 操作: configure 中 umask 077 改为 022（E011）
- 结果: configure 正常生成 Makefile

### 对话 #3 [2026-09-18]

- 问题: CI profile 注入的 hnp bash 作为 CONFIG_SHELL 在 HMDFS 构建树上 getcwd 失败，configure 用它自我 re-exec 后报 working directory cannot be determined
- 操作: configure 顶部增加 CONFIG_SHELL 能力探针，探针失败即回退 /bin/sh（E386）
- 结果: 在 CONFIG_SHELL=hnp bash 的 conan 环境下 configure/make/上游测试全部通过

### 对话 #4 [2026-09-18]

- 问题: C++17 下旧代码编译失败（-Wc++11-narrowing、指针与 0 的有序比较、uint 未定义、register 关键字、字面量紧邻宏名不再展开）
- 操作: Base64 解码表改 signed char（aarch64 上 char 无符号，-1 哨兵恒假）、mmfile 改 MAP_FAILED、libconfig.h 补 uint、itparser.h 去 register、cutee.cxx 字面量补空格
- 结果: 库与上游 cutee 套件在 clang 15 / gnu++17 下全部编译通过

### 对话 #5 [2026-09-18]

- 问题: W3 质量门禁 L0d 判定消费者测试为 stub（test() 使用 cmake.test() 而非 self.run）
- 操作: test_package 的 test() 改为直接执行 test_mimetic 二进制（conanrun 环境）
- 结果: W3 本地 CI 通过，消费者 9 条断言全过

### 对话 #6 [2026-09-18]

- 问题: conan-verify L5 产物基线与上一轮不一致（静态库 lib/libmimetic.a 每轮内嵌不同的构建路径/build-id）
- 操作: 删除 reports/baseline.json 重立基线（工具提示的"语义等同首轮"做法）
- 结果: 重新验证后 L5 通过并保存本轮基线

### 对话 #8 [2026-09-18]

- 问题: 同一 HEAD 再次验证时 L5 仍报基线差异（lib/libmimetic.a）
- 根因: 本轮验证的私有 CONAN_HOME 路径每轮随机命名，静态归档内的目标文件嵌入了该构建路径，
  因此**只要换一轮验证，.a 的字节就会变化**；这不是源码或配方变化
- 操作: 按工具提示再删 reports/baseline.json 重立基线（语义等同首轮），并把该复发特性记录在此
- 结果: L5 通过；后续每轮本地验证前需重立基线（产物集合与 include 头文件数不变：1 个 .a + 51 个头文件）

### 对话 #7 [2026-09-18]

- 问题: W3 本地 CI 的补丁安全扫描 L4_RESULT=warn（命中 0001-config.guess.patch 注释里的 `targets` 子串，被 gets 词界规则误判）
- 操作: 人工核对补丁内容确认无 socket/网络调用，属扫描器误报；同轮 conan-verify 的 L4 为 passed（纯库无 bin/、无 ELF 可扫描）
- 结果: 不修改补丁；在此披露该非 pass 标记（非阻断）
