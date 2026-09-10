# afl 1.35b 适配笔记（HarmonyOS PC / arm64）

## 基本信息

| 项 | 值 |
|----|-----|
| 库名 | afl（经典 American Fuzzy Lop，Michal Zalewski 原版） |
| 版本 | 1.35b（任务看板写 1.35a，官方从未发布 1.35a；1.35b 为 1.35 代真实版本，2026-08-24 与用户确认） |
| 上游 | lcamtuf.coredump.cx 原站已下线；使用社区镜像 cmouse/afl-fuzz（托管经典 afl 全部版本 tag） |
| 许可证 | Apache-2.0 |
| 构建系统 | Makefile（无 configure/CMake） |
| 依赖 | 零 Conan 依赖（仅需 clang，OHOS SDK 自带） |
| 补丁 | 4 个（0001 test_x86 门禁 + 0002-0004 三工具 shmget→mmap） |
| 源码 SHA256 | a3bab8b26aa267d445047f67ade7b916bed7eeff36d959e97384a37f549c89c5 |

## 平台适配要点

### 1. SysV 共享内存被 OHOS 沙箱拦截（核心攻坚点，参考文档预判命中）

- 上游 afl-fuzz.c/afl-showmap.c/afl-tmin.c 均硬编码 `shmget(IPC_PRIVATE,...)` + `shmat()`，
  **1.35b 无 USEMMAP/shm_open 选项**（该特性是后续版本加的）。
- OHOS 沙箱对 SysV IPC 返回 SIGSYS → 工具无法启动。
- 修复：三个工具统一改为 `shm_open + ftruncate + mmap`（POSIX 共享内存），
  与 AFL++ USEMMAP 方案同源（OHOS 已验证可用）。env 变量 `__AFL_SHM_ID` 内容
  由 shm ID 改为 shm 名称（aarch64 上无插桩消费者，无兼容问题）。
- 需要 `<sys/mman.h>`（afl-fuzz.c 已有；afl-showmap.c/afl-tmin.c 通过补丁将
  `<sys/shm.h>` 替换为 `<sys/mman.h>`）。

### 2. Makefile test_x86 门禁在 aarch64 必挂

- `make all` 首先编译 `__asm__("xorb %al, %al")`（x86 内联汇编）探测，
  aarch64 clang 编译失败 → make 中止。
- 修复（0001）：探测失败改为非致命（回显提示后继续）。x86 上仍会真实探测。

### 3. 插桩模式平台限制（如实声明，R40）

- 经典 afl 的插桩由 afl-as 在汇编层注入（afl-as.h trampoline/main_payload 为
  纯 x86/x86_64 AT&T 汇编），**上游从未支持 aarch64**（experimental/arm_support
  仅 32 位 ARM；2.35b/2.52b 等经典全系同样无 aarch64 插桩，LLVM 插桩是 AFL++ 独有）。
- 因此 OHOS arm64 上：afl-gcc/afl-as 可编译打包，但**插桩模式不可用**；
  已验证可用范围为 **dumb 模式（-n）模糊测试**（随机变异 + 崩溃/超时检测，
  不依赖覆盖率）+ afl-gotcpu/afl-showmap（fork/exec 链路）+ 脚本工具。
- 上游 `test_build`（test-instr.c 插桩冒烟）依赖 x86 插桩，aarch64 不执行
  （配方 build() 只构建 PROGS 各目标，不走 `all`）。

## 与 4.33c（AFL++）经验的关系

- 复用知识：OHOS musl 不传递包含 `<sys/types.h>`（本次源码未触发，但知识草稿
  DRAFT-aflplusplus-ohos-posix-types 仍为本族通用）；shmget→mmap 与 USEMMAP 同源方案。
- 不可复用：LLVM 插桩路线（1.35b 无）、afl-cmin.py spawn 修复（1.35b 是
  afl-cmin.bash，无 Python）、test-basic/test-llvm 脚本体系（1.35b 无）。

## 实机验证记录（2026-09-02，OHOS aarch64 / clang 15.0.4）

- `conan create` 编译通过（6 工具 + 3 脚本打包，仅上游格式类警告）。
- test_package 3 项全过：afl-gotcpu PASS / afl-showmap fork-exec 成功 /
  afl-fuzz -n 启动并创建 out/queue（"PASS: afl-fuzz -n created out/queue with initial seed"）。

### 实机坑位

| # | 坑 | 根因 | 解决 |
|---|-----|------|------|
| A | conan test 里 afl-showmap 报 `Unable to execute '<target>'`，但 shell 直接跑同一目标成功 | ① 相对路径在 conan test cwd 下解析不到（需绝对路径）；② **默认 50MB RLIMIT_AS**（`-m` 默认 MEM_LIMIT=50）施加在 fork 子进程上——子进程继承 conan/python 父进程的巨大虚拟地址空间，超限后加载器 mmap 失败 → exec ENOMEM | ① 目标用绝对路径；② 加 `-m none`（mem_limit=0，跳过 setrlimit）。两处都要，缺一不可 |
| B | conan test 的 cwd 不可靠 | test() 与 build() 的 cwd 语义在无 layout 的 test_package 下不直观 | 所有命令参数用 `self.build_folder` 绝对路径 |
| C | 鸿蒙 PC 上 git 报 dubious ownership | 仓库属主与当前用户不一致 | `git config --global --add safe.directory <repo>` |

> A 坑的 RLIMIT_AS 问题与 4.34c 测试中 afl-showmap 一律加 `-m none` 的经验一致，
> 属 OHOS 平台运行特性（父进程 VA 大 + fork + 低 RLIMIT_AS 的组合），已在测试指令中固化。

## 验证指令（鸿蒙 PC）

见 `md汇总/留痕工作/afl/afl测试指令.md`。
