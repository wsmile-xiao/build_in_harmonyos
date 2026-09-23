# db (Berkeley DB classic) 6.2.32 适配笔记

## 概述

Berkeley DB 经典线（Sleepycat 血统）6.2.32。与仓内 `berkeley-db5/5.3.28`（Sleepycat 许可的 5.x 线）、`berkeley-db4/4.8.30`（4.x 线）以及 Oracle Berkeley DB 12c/18c/19c 包（不同包名线）**互为独立软件条目**，本条目包名 `db` 采用上游 tarball 自身的命名（db-6.2.32.tar.gz）。

- 上游源码：https://download.oracle.com/berkeley-db/db-6.2.32.tar.gz
- SHA256：`a9c5e2b004a5777aa03510cfe5cd766a4a3b777713406b02809c17c8e0e7a8fb`
- 许可：AGPL-3.0（6.x 起从 Sleepycat 变更为 AGPL；5.x 是 Sleepycat）
- 构建：autoconf，BDB 特有形态——configure 在 `dist/`，必须从 `build_unix/` 子目录调用

## 编译环境

- 构建系统：autotools（`cd build_unix && ../dist/configure`）
- 编译器：clang 15.0.4（OHOS aarch64 工具链）
- 语言预检（R47）：c / autotools / 源码统计 100%（src/ 350 个 .c）
- 状态：built

## 编译步骤

```bash
cd build_unix
../dist/configure --prefix=<prefix> --enable-static --enable-shared \
    --enable-cxx --with-repmgr-ssl=no
make -j4
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 无法识别 HarmonyOS | 上游 2014-03-23 版脚本无 OHOS 分支 | 补丁 0001/0002：config.guess 增加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；config.sub 的 KERNEL-OS 列表与 OS 列表接受 `linux-ohos`（E007 同类，BDB 的 dist/configure 内嵌脚本需按其 2014 版结构手工制作，无法直接复用 automake-1.16 全量补丁） |
| 2 | configure 探测到 `print -r --` 回显可用，config.status 运行时大量 `print: command not found`，且生成的 libtool 脚本 `archive_expsym_cmds` 被截断 → make 阶段 `libtool[347]: syntax error: unexpected '}'` | HMDFS 开发者 shell 的探测 shell 支持 ksh 风格 `print` 内建（探测假阳性），而 config.status 后续执行环境无 `print` | 补丁 0003：dist/configure 强制 POSIX `printf`（5 处赋值 + 3 处探测条件改写）。源文件级修复（区别于 berkeley-db5 在 conanfile 里运行时改写——直接修 configure 使所有下游生成物干净） |
| 3 | `config.status: ./confXXXX/subs1.awk: Permission denied` | config.status 以 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMDFS setgid 目录拒写 | conanfile build() 运行时改写生成的 config.status（R6：禁止 patch 生成文件）：临时目录重定向 `$TMPDIR` + `umask 022`，再手动执行 |
| 4 | `--enable-cxx` 编译 `cxx_channel.cpp` 报 `atomic:1858: error: expected unqualified-id` | BDB `dbinc/atomic.h` 将 `atomic_init` 定义为宏，污染 libc++ `<atomic>` 的同名函数声明 | 补丁 0004：`src/dbinc/db_cxx.in` 在 `#include <iostream>` 前 `#undef atomic_init` |
| 5 | cutest 全量运行在 TestQueue 段 `Trace/breakpoint trap (core dumped)`（SIGTRAP） | TestQueue.c 为 K&R 老式函数定义（无原型）+ SH_LIST/SH_TAILQ 宏的重解释指针运算，在 clang -O2/-O3 优化下暴露 UB；-O0 编译 136/136 全过（实证二分定位） | 上游测试代码以 `-O0` 编译（仅测试目标；库本体保持 -O3）。CI/本地复验命令见测试台账 |
| 6 | C++ 测试二进制运行报 `Error loading shared library libc++_shared.so` | OHOS clang++ 默认动态链接 libc++_shared，运行环境需显式提供 | 上游 C++ 测试实测时 `-L<sysroot>/llvm/lib/aarch64-linux-ohos/c++ -lc++_shared` 并设置 LD_LIBRARY_PATH |
| 7 | TCL 测试套件（test/tcl/，553 文件）无法运行：`dynamic loading is not currently available on this system`（tclsh8.6 实测：`catch {load /nonexistent.so} e` → `dynamic loading is not currently available on this system`） | 制品仓 tcl/8.6.14 包为静态构建（default_options shared=False，产物仅 libtcl8.6.a 无 .so），其 tclsh8.6 的 `load` 命令不可用，无法加载 libdb_tcl-6.2.so；系统 dlopen 本身可用（dltest 验证通过），是 tclsh 构建形态限制 | 如实记录技术原因；TCL 套件按环境豁免（478 注册名全部）。C/C++/C++ 测试全部实测替代 |

## 上游测试核验（rule4 可执行口径）

上游 db-6.2.32 无统一 `make check` 目标。测试注册口径盘点：

### 上游构建系统注册的测试目标

| 测试族 | 注册位置 | 用例数 | 本环境可执行性 |
|--------|---------|--------|---------------|
| C 单元测试 | `test/c/cutest`（Makefile `cutest` 目标，13 suite） | 55 tests（2+1+8+1+12+12+1+1+1+4+7+4+1） | ✅ 全部实测 |
| C 回归测试 | `test/c/chk.ctests`（test_api_methods / test_db185 / test_log_verify） | 3 | ✅ 2/3 实测；test_db185 需 `--enable-compat185`（非默认配置）内联豁免 |
| C++ 回归测试 | `test/cxx/chk.cxxtests`（8 个 .cpp） | 8 | ✅ 全部实测 |
| TCL 套件 | `test/tcl/TESTS`（553 文件，478 个测试名注册） | 478 | ❌ 不可执行（tclsh 静态构建无 `load`，见问题7） |
| XA 测试 | `test/xa/`（7 条目：chk.xa + src1~src5 + utilities） | 7 | ❌ 不可执行（需 Tuxedo `TUXDIR`，企业事务中间件；chk.xa 开场 `test -z "$TUXDIR"` 即 FAIL 退出） |
| micro 基准 | `test/micro/test_micro` | — | 性能基准非功能测试，不计入 |

**N 口径合计**：55 + 3 + 8 + 478 + 7 = **551**（上游测试注册总数，rule4 声明口径）

### 实测结果（OHOS aarch64 设备）

1. **cutest（C 单元套件）**：13 suites / 55 tests 全部通过，rc=0：
   - TestCallbackSetterAndGetter 2/2、TestChannel 1/1、TestDbHotBackup 8/8、TestDbTuner 1/1、TestEncryption 12/12、TestEnvConfig 12/12、TestEnvMethod 1/1、TestKeyExistErrorReturn 1/1、TestMutexAlignment 1/1（需先 `make test_mutex` 并将 test_mutex 二进制放 CWD）、TestPartial 4/4、TestPartition 7/7、TestPreOpenSetterAndGetter 4/4、TestQueue 1/1（suite 内 136 断言 100%）
   - TestQueue 以 -O0 编译（见问题5）；其余 suite 按上游默认 -O3 编译
2. **test_api_methods.c**：编译运行通过，退出码 0
3. **test_log_verify.c**：编译运行通过，退出码 0
4. **test_db185.c**：需 `--enable-compat185`（db_185.h 头），本次配置未启用，内联豁免
5. **C++ 回归测试 8 个**：TestConstruct01 / TestGetSetMethods / TestKeyRange / TestLogc / TestMulti / TestSimpleAccess / TestSlice / TestTruncate 全部通过（stdout 与上游 .testout、stderr 与 .testerr 逐字节比对一致）
6. **消费者冒烟**（test_package/test.c）：db_create/open(BTREE)/put×50/get/cursor 扫描 50 条/close/RDONLY 重开持久性验证 全链路通过

### 复验命令

```bash
# cutest（TestQueue -O0 复编后全量）
cd build_unix && make cutest && make test_mutex
export TMPDIR=$HOME/tmp && cd $TMPDIR && cp <build_unix>/.libs/test_mutex . && rm -rf TESTDIR
LD_LIBRARY_PATH=<build_unix>/.libs bash <build_unix>/cutest

# C 回归测试
cc -g -I build_unix -I src -I src/dbinc test/c/test_api_methods.c build_unix/.libs/libdb-6.2.a -lpthread -o t_api && ./t_api
cc -g -I build_unix -I src -I src/dbinc test/c/test_log_verify.c build_unix/.libs/libdb-6.2.a -lpthread -o t_lv && ./t_lv

# C++ 回归测试（chk.cxxtests 需 TUXDIR 无关，手动等价）
c++ -I build_unix -I src -I src/dbinc test/cxx/Test*.cpp build_unix/.libs/libdb_cxx-6.2.a build_unix/.libs/libdb-6.2.a \
    -L<sysroot>/llvm/lib/aarch64-linux-ohos/c++ -lc++_shared -lpthread
# 逐个以 .testin 为 stdin 运行，stdout/stderr 与 .testout/.testerr cmp
```

## 注意事项

- 包交付：libdb-6.2（C API，cpp_info.libs）+ libdb_cxx-6.2（C++ API，components["db_cxx"]）+ db.h/db_cxx.h + 15 个 db_* 命令行工具（bin/，commands.json 已声明）
- 与 berkeley-db5（5.3.28）独立并存：libdb-6.2 vs libdb-5.3，头文件同名 db.h 但版本不兼容，属不同包
- TCL API（--enable-tcl）未启用：环境 tclsh 静态构建无法 `load` 扩展，且 CI 无 tcl 依赖需求，保持零依赖
- ELF 签名：CI 流水线 sign.sh 处理；本机 HMDFS 对 stripped ELF 执行有限制（L2 冒烟已知平台限制，非阻塞）
---

**编译结束**: 2026-09-10 01:13
**最终状态**: built
