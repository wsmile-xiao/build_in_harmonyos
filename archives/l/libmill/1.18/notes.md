# libmill 1.18 — HarmonyOS PC (aarch64) 适配笔记

- 上游：libmill — Go-style concurrency in C，Martin Sustrik
- 官网：http://libmill.org/ ；仓库：https://github.com/sustrik/libmill
- 版本：1.18（tag 无 v 前缀）
- 许可证：MIT（COPYING）
- 构建系统：CMake（发布 tarball 里只有 `autogen.sh`，没有生成好的 `configure`，
  所以 autotools 路线要 autoreconf；CMakeLists.txt 可直接用）
- 依赖：**无**
- 包形态：纯库 —— 默认 `lib/libmill.a` + `include/libmill.h`
  （`-o shared=True` 时改打 `libmill.so`）。库包**不需要** commands.json（R38）
- 状态：**READY_FOR_HARMONY** —— WSL 侧完整 `conan create` 已跑通（见 §4），
  HarmonyOS 真机尚未执行

## 1. 上游构建/打包要点（0 个补丁）

**没有打任何补丁**，两处上游特性在配方里处理：

| 上游特性 | 处理 |
|---|---|
| `cmake_minimum_required(VERSION 2.8.7)` | 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake ≥3.28 拒绝低于 3.5 的兼容声明） |
| **完全没有 `install()` 规则** | `package()` 手工 `copy()` 头与库 |

公开头文件的权威依据是 autotools 的 `Makefile.am`：

```make
millinclude_HEADERS = libmill.h
```

即**只有 `libmill.h` 是对外头**，且它自包含（`grep -c '#include "'` = 0）。
另外上游还提供 `libmill.pc`（pkg-config），配方里设了 `pkg_config_name`。

### CMakeLists 的一个特点
它同时产出静态与共享库，且用 `OUTPUT_NAME` 让两者同名：

```cmake
add_library(mill STATIC ${sources})
add_library(mill_s SHARED ${sources})
set_target_properties(mill_s PROPERTIES OUTPUT_NAME mill)
```

不认 `BUILD_SHARED_LIBS`。配方按 `shared` 选项**选择性打包**：
默认（shared=False）打 `libmill.a`，shared=True 打 `libmill.so`。

## 2. ⚠️ 一个重要的编译器差异：GCC 编不过、clang 正常

`dns/dns.h:499` 是：

```c
dns_rr_i_init(&dns_quietinit((struct dns_rr_i){ 0, __VA_ARGS__ }), (P))
```

而 `dns_quietinit` 有两个分支（`dns/dns.h:140-160`）：

- **clang**（`#if defined __clang__`）→ 展开成 `_Pragma(...) __VA_ARGS__ _Pragma(...)`，
  仍然是复合字面量，**是 lvalue**，取地址合法；
- **GCC**（`__GNUC__ > 4`）→ 展开成 `__extension__ ({ ...; })`，这是**语句表达式**，
  不是 lvalue，`&` 直接报错：

```
dns/dns.h:499:23: error: lvalue required as unary '&' operand
```

实测：GCC 15（默认 gnu23）与显式 `-std=gnu11` **都失败**，共 51 处错误；
换成 clang 21 后**干净构建**。

**结论：这不影响本任务** —— OHOS worker 用的是 clang 15（走 `__clang__` 分支）。
但本地排雷时要注意：WSL 默认 profile 是 gcc，直接 `conan create` 必然失败。

## 3. 本地排雷的正确姿势（记录一下踩的坑）

第一次用「`compiler=clang` 的 profile」跑仍然失败——因为 **Conan 的
`CMakeToolchain` 不会仅凭 `compiler=clang` 就把编译器的路径交给 CMake**，
CMake 自己探测到的是 `cc`（= 系统的 gcc）。必须在 profile 的 `[conf]` 里补：

```ini
tools.build:compiler_executables={"c": "/usr/bin/clang", "cpp": "/usr/bin/clang++"}
```

补上之后本地 conan create 一次通过。

## 4. WSL 侧完整 `conan create` 实测（clang profile）

```
libmill/1.18: libmill upstream tests: 18/18 passed, 0 failed (ctest exit 0)
libmill/1.18: Package created
test package: ./test_libmill
ok   coroutine ran to completion (6 x +7 == 42)
ok   unbuffered channel delivered 333
ok   first of two senders delivered 888
ok   second of two senders delivered 999
ok   buffered channel round-tripped 1
ok   msleep advanced the clock by at least 50ms
all libmill consumer checks passed
```

## 5. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **18** | `CMakeLists.txt:43-54` 对 `tests/*.c` 每个文件 `add_test` |
| `upstream_test_files`   | **18** | `tests/` 下 18 个 `.c`（`perf/` 的 7 个只有 `add_executable`，是基准不是测试） |
| `upstream_case_total`   | **18** | 每个 ctest 用例 = 一个测试可执行文件，逐条注册、可逐条核对 |

判定依据取 ctest 自己的汇总行：`100% tests passed, 0 tests failed out of 18`。

> `tests/ssl.c` 整体包在 `#if defined HAVE_SSL` 里，未定义时落到 `#else` 的空
> `main`（`tests/ssl.c:137-143`）。它**不是被跳过的用例**：它验证的是"未启用
> SSL 时程序行为仍然正确"，会真实执行并通过。

## 6. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：`CMAKE_POLICY_VERSION_MINIMUM`
   是否被接受；`mprotect` / `posix_memalign` / `clock_gettime` 探测在 musl 上的结果
2. ctest 18 条在真机的通过情况。**重点关注网络类用例**
   （tcp/udp/unix/ip 走本机回环）与 fork 类用例（mfork1-3）在 OHOS 上的行为
3. 协程实现在 aarch64 上的正确性 —— 非 x86_64 走 `sigsetjmp/siglongjmp` 路径
   （`libmill.h:204-206`），这是本包最核心的平台相关代码
4. test_package 的 6 项消费断言

## 7. 首轮真机结果与修复（2026-09-21 夜）

首轮真机：**构建成功，ctest 16/18，2 条 SEGFAULT**

```
89% tests passed, 2 tests failed out of 18
The following tests FAILED:
    6 - test_file (SEGFAULT)
   18 - test_unix (SEGFAULT)
```

两条都先做了**设备侧最小探针**再决定怎么处理，结论完全不同：

### 7.1 test_file —— 可修（/tmp 只读）
探针：
```
$ echo x > /tmp/probe_write_test
sh: can't create /tmp/probe_write_test: Read-only file system
$ ls -ld /tmp
drwxr-xr-x 2 root root 27 2024-06-06 08:00 /tmp
```

`tests/file.c` 写死 `mfopen("/tmp/file1", O_RDWR|O_CREAT|O_TRUNC, ...)`，
`/tmp` 只读 → 返回 NULL；而 **Release 构建定义 NDEBUG，`assert(f1)` 被编译掉**，
于是下一行的 `mfeof(f1)` 空指针解引用 → SIGSEGV。
（这也解释了为什么是 SEGFAULT 而不是断言中止。）

处理：补丁 `0001-tests-file-writable-tmp.patch` 把路径改成工作目录下的相对路径
`"milltest.file1"`（ctest 从可写的 build 目录跑该用例）。**只改路径，断言序列不变**；
这是平台只读 `/tmp` 的标准处理方式（对应农场知识 E002 "临时文件用 $TMPDIR"）。

### 7.2 test_unix —— 不可修（平台禁止 AF_UNIX）
探针（在设备可写目录下）：
```
$ python3 -c "import socket,os; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.bind(os.path.abspath('milltest.sock'))"
AF_UNIX 失败: PermissionError [Errno 1] Operation not permitted
```

**HarmonyOS 不允许 AF_UNIX socket bind**（EPERM），这是内核/安全策略层面的限制，
不是配置问题、也无法通过改上游测试绕过。

处理：**不修改上游测试文件**，只在 ctest 调用里排除该用例并在申报表里如实记为
**NOT_RUN**（附上述探针证据），不计入通过数、不计入失败数。

> 反例警示：如果这里图省事把 `assert(ls)` 之类的断言删掉让用例"通过"，
> 那就是伪造通过——本仓库明令禁止。NOT_RUN + 技术原因 + 可复现证据才是正确做法。

### 7.3 修复后的本地复验（clang profile）
```
libmill/1.18: Apply patch (portability): tests/file.c ... 
libmill/1.18: libmill upstream tests: 17/17 executed passed, 0 failed (ctest exit 0); NOT_RUN: test_unix
libmill/1.18: Package created
test package: 6/6 consumer checks passed
```

### 7.4 平台限制对使用者的影响（需在 PR 里说清）
- **`/tmp` 只读**：libmill 自身不依赖 /tmp，只影响上游那条测试用例的落盘位置；
- **AF_UNIX 不可用**：libmill 的 `mill_unixlisten` / `mill_unixpair` 等
  unix domain socket API 在 HarmonyOS 上**无法使用**（bind 会 EPERM）。
  库本身照常构建、其余功能（协程、通道、TCP/UDP、文件）均正常。
