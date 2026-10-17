# boxfort 0.1.2 OHOS 适配笔记

日期：2026-09-05　设备：HUAWEI MateBook Pro (HAD-W24, OpenHarmony 6.1.1, aarch64)
工具链：clang 15.0.4 (aarch64-unknown-linux-ohos)、meson 1.12.0、ninja 1.13.1、Conan 2.29.1、cmake 4.1.2

## 探索路径

1. 源码：`https://github.com/Snaipe/BoxFort/archive/refs/tags/v0.1.2.tar.gz`，SHA-256 `7651a02c4ed159bb1631c34b4dd2a3df60253cd1956490a434a7ef22f20cd7c8`。
2. 原生 `meson setup build` + `ninja -j1`：全部 19 个目标一次通过（含 aarch64 trampoline 汇编）。
3. 首轮 `meson test`：4/4 全部 SIGABRT。诊断：父进程 `bxf_run` 返回 `-71 (EPROTO)`，`wait_stop` 报 EPROTO 意为 fork 子进程未停在 SIGSTOP 而是直接退出。

## 两个根因（均有设备实测证据）

### 根因 1：代码页自改被 OHOS 内核策略 (XPM) 全面禁止

boxfort 沙箱握手 = fork 后子进程 `execve(自身)` 重执行，构造器 `patch_main` 把 `main` 代码页 `mprotect(PROT_READ|PROT_WRITE|PROT_EXEC)` 后写入跳板。实测探测程序输出：

- `mprotect(text, R|W|X)` → rc=-1 EINVAL(22)
- `mprotect(text, R|W)` → 进程被内核直接 SIGSEGV 击杀（无用户态信号可达）
- `/proc/self/mem` pwrite 代码页 → EPERM(13)
- `mmap(MAP_FIXED|MAP_ANONYMOUS)` 覆盖代码页 → 进程被击杀

结论：重执行+跳板改写机制在 OHOS 上不可实现（平台安全设计，非可修复缺陷）。

修复（patches/0003、0002、0004，**运行时能力探测**，POSIX 实现无平台宏）：
- 新增 `bxfi_probe_text_writable()`：fork 一次性探测子进程，尝试对本函数所在代码页 `mprotect(RWX)`→`mprotect(RW)`+回写首字节（探测子进程在强制系统上被内核击杀，父进程据 `WIFEXITED` 判定）；探测结果按进程缓存；
- 判定不可写时走直跑分支：fork 子进程跳过 SIGSTOP/shm 握手/重执行，直接 `setsid()`、按需 adopt 上下文、调用沙箱函数、`fflush(NULL)` 后以其返回值 `_exit()`；父进程侧跳过两轮 `wait_stop` 与 shm 上下文，直接注册 child pump、设置运行时配额；`suspended` 时父进程以 `waitpid(WUNTRACED)` 与子进程同步后再标记 stopped（避免 resume 的 SIGCONT 丢失竞态）；
- 探测可写时保持上游自执行+跳板路径不变（Linux/CI 行为与上游完全一致）；
- 新增 `bxfi_context_adopt()`（context.c/h）：fork 镜像中继承的上下文地址不变，直接置为 `bxf_context_current()`。
- 副作用核查：探测子进程的内核击杀不留 faultlogger 记录（实测运行前后 faultlogger 数量不变）。

### 根因 2：OHOS 用户态 VA 上限 39 位，arena 高地址窗口全部越界

`bxf_arena_init` 用 `MAP_FIXED` 在预留窗口放置共享 arena：64 位默认窗口 `[0x200000000000, 0x7f0000000000)`（32–125 TiB）。实测（shm fd）：

- `MAP_FIXED @0x4000000000` OK；`@0x8000000000` EINVAL；`@0x1000000000` OK；`@0x2000000000` OK。

即 39 位（512 GiB）用户 VA 上限。修复（patches/0001，运行时探测）：`bxf_arena_init` 首次调用时以 `MAP_FIXED` 匿名页探测默认基址 0x200000000000，被拒（EINVAL）则窗口降为 `[0x100000000, 0x4100000000)`（4 GiB 起，~259 GiB 止，16 MiB 步长、16384 槽位）；默认窗口可用时行为与上游完全一致。

`mremap` 说明：prescan 报 arena.c:433 `mremap` critical；实测 OHOS musl `nm -D libc` 存在 `mremap` 弱符号但头文件不声明 `MREMAP_MAYMOVE`。核对源码：`HAVE_MREMAP` 在 meson.build checks 列表、config.h.in、源码中均无定义点——该分支是永假死代码，真实运行路径是 mmap MAP_FIXED 回退分支（构建成功 + arena 行为正常证明其可用），prescan 项判误报，无需补丁。

## 最终验证

- 原生构建：`meson setup build && ninja -j1` 通过。
- 上游测试 `meson test`：TOTAL=5（4 个注册 sample 测试 + 1 个未注册 cram 测试）；PASS=4 FAIL=0 SKIP=0 NOT_RUN=1。
  - NOT_RUN：`test/cram/core.t` 依赖 cram/cram3 程序（`command -v cram cram3` 为空），上游 `required: false` 使其不注册；替代验证：按 core.t 的 3 组命令用 sh 手工执行，输出与期望逐行一致。
  - sample 输出与 upstream cram 期望逐字一致（nested 两行、callback code 5、context 42/24、timeout 1s+2.0s）。
- `test_package`：真实消费者 12 项断言全通过（嵌套沙箱、回调退出码、配额击杀、context 往返）。
---

**编译结束**: 2026-09-05 14:52
**最终状态**: built
