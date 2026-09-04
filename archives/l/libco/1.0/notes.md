# libco 1.0 适配笔记

## 编译环境
- 构建系统: makefile（无 configure，无 install 目标；`make colib` 只建库）
- 编译日期: 2026-09-02
- 编译器: clang/clang++（OHOS aarch64，musl libc）
- 状态: built（conan-verify 通过后升级 published）

## 编译步骤

上游无 configure，直接 make：

```bash
# 探索阶段（本机 aarch64 OHOS 环境，编译器来自系统路径）
cd $BUILD_SRC_DIR
make -j1 CC=clang CXX=clang++ colib
# 产物: lib/libcolib.a + solib/libcolib.so

# example 测试（上游测试套件即 8 个 example 程序）
./example_closure; ./example_cond; ./example_copystack
./example_specific; ./example_thread
./example_poll 127.0.0.1 <port>
./example_echosvr 127.0.0.1 <port> <cnt> <size> &  # 与 echocli 对测
./example_echocli 127.0.0.1 <port> <cnt> <size>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | coctx_swap.S 无 aarch64 实现 | 上游 v1.0（含 master）仅有 i386/x86_64 | 自行编写 aarch64 协程切换汇编（见源码修改 #1） |
| 2 | co_hook_sys_call.cpp 编译失败: `rdtscp` 内联汇编寄存器冲突 | x86 专用 rdtsc/rdtscp | 改用 `clock_gettime(CLOCK_MONOTONIC)`（见 #2） |
| 3 | 编译失败: `NETDB_INTERNAL` 未定义 | glibc 专用宏，musl 无 | 按 musl 语义改写 h_errno 错误分支（见 #3） |
| 4 | example 编译失败: socket `bind` 解析到 `std::bind` | co_routine.cpp:47 `using namespace std;` + libc++ 头 | example_poll/example_echosvr 显式 `::bind`（见 #4） |
| 5 | 首版 aarch64 汇编全例程崩溃 | ARM64 `BL` 不压栈返回地址，且栈式保存/恢复与 coctx_make 的 regs 槽位错位 | 重写为 x86_64 原版"存/取 regs 数组"语义（见 #1） |

## 源码修改

### #1 coctx.h / coctx.cpp / coctx_swap.S — 新增 aarch64 协程上下文支持

- `coctx.h`：`coctx_t.regs` 对 `__aarch64__` 扩为 `void *regs[24]`
- `coctx.cpp`：`coctx_make` 新增 `__aarch64__` 分支，
  槽位常量 `kA64SP=12, kA64RETAddr=13, kA64X0=22, kA64X1=23`（ss_sp 按 16 字节对齐）
- `coctx_swap.S`：新增 `__aarch64__` 段，语义对齐 x86_64 原版：
  - 保存当前上下文到 `a->regs[0..23]`：x19-x28（callee-saved）、x29/x30（fp/lr）、
    real sp→槽 12、resume 地址（x30）→槽 13、d8-d15（callee-saved FP）、参数 x0/x1→槽 22/23
  - 从 `b->regs` 恢复后 `mov sp, x9; br x8` 切换
  - 关键差异：ARM64 `BL` 不压栈返回地址，返回地址（resume 点或新协程 pfn）
    与 real sp 必须像 x86_64 那样显式存入 regs 槽位，不能依赖栈
- 布局验证：8 个 example 全部通过（含 10 万次切换的 copystack 与 20 万次创建的 thread 压测）

### #2 co_hook_sys_call.cpp — 时钟获取 musl 化

x86 `rdtscp` 内联汇编（读 TSC）在 aarch64 不可用，`GetTickMS()` 改用
`clock_gettime(CLOCK_MONOTONIC)` 换算毫秒。

### #3 co_hook_sys_call.cpp — NETDB_INTERNAL musl 兼容

musl libc 的 netdb.h 无 glibc 专用的 `NETDB_INTERNAL` 枚举，
`getaddrinfo`/`gethostbyname` hook 的错误分支按 musl 语义改写
（`__OHOS__` 守卫 + musl 下直接用返回码判断）。

### #4 example_poll.cpp / example_echosvr.cpp — bind 二义性

`co_routine.cpp` 全局 `using namespace std;` 使无修饰 `bind` 在 libc++ 下
解析到 `std::bind`，socket 调用点显式写 `::bind`。

> R3：以上修改目前直接改在源码上；finish 阶段由 `refresh-patch --auto` 固化为 patches/。

## 依赖版本

无第三方依赖（libco 自包含，仅 libc/libpthread/libdl 系统库）。

## 验证结果

```bash
# 8 个上游 example 全部通过（详见 test_package/MANIFEST.yml upstream_tests）
example_closure  exit=0   # co_sleep hook
example_cond     exit=0   # 生产者/消费者条件变量
example_copystack exit=0  # 共享栈 10 万次切换
example_specific exit=0   # 协程私有变量往返
example_thread   exit=0   # 4 线程 × 5 万协程压测
example_poll     exit=0   # poll hook 回环
echosvr/echocli  exit=0   # 网络回显对测
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libcolib.a | 静态库 |
| solib/libcolib.so | 动态库 |

## 注意事项

- `co_routine.h` 无 `extern "C"`，C++ 编译单元 include 时按 C++ 符号解析——
  test_package 用 C++（test.cpp）而非 C
- 上游 Makefile `LINKS` 硬编码 `-ldl`（Linux 分支），OHOS musl 下 dl 系列符号在 libc 内，冗余但无害
- co.mk 的 `CFLAGS` 是赋值式（`CFLAGS= ...`），命令行传 `CFLAGS=` 会覆盖调试参数；
  注入编译器用 `CC=`/`CXX=` 变量（co.mk 用 `$(CC)`/`$(CXX)` 拼命令），不要传 CFLAGS
- example 程序未随 conan 包交付（配方只打包 colib 目标与头文件），example 仅作上游测试载体
---

**编译结束**: 2026-09-02 20:57
**最终状态**: built
