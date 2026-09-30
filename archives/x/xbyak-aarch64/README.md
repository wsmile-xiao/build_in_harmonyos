# xbyak-aarch64

## 简介

xbyak_aarch64 是 Fujitsu 的 **AArch64 用 C++ JIT 汇编器**。它以 C++ 类的方式描述
AArch64 / NEON / SVE 指令，在运行期把这些指令编码成机器码写入可执行内存，刷新
指令缓存后直接调用——用于需要按运行时条件生成专用代码的场景（解释器、正则引擎、
数值内核等）。

## 功能概述

- 指令覆盖：整数/分支/加载存储、NEON（ASIMD）标量与向量、**SVE** 与 SVE 寻址
- 运行期代码生成：`CodeGenerator` → `ready()` → `getCode<T>()` → 直接调用
- 可执行内存：`XBYAK_USE_MMAP_ALLOCATOR`（测试与 sample 均启用）
- 标签、跳转、即时数、寄存器分配等汇编器基础设施
- 运行时 CPU 特性探测（`util::getCPUType()`）与缓存信息查询（`getCacheSize()`）
- 自带测试：`test/` 逐条指令与 **GNU as** 输出做机器码比对

## OHOS 适配

- **路径 C 证据（源码/构建/测试配置级）**
  - 库在运行期向可执行内存写入 AArch64 机器码并跳转执行；
  - 上游测试 `test/test_all.sh` 不比对字符串，而是用
    `as -march=all -mcpu=all -acdnl=a.lst` 生成参考编码、由 xbyak JIT 生成同一批
    指令的编码，再 `diff -w x.lst ok.lst` **逐字节比对机器码**；
  - 上游 CI（`.github/actions/test_action/entrypoint.sh`）执行的就是
    `./test_all.sh -q`。
- **鸿蒙 PC 实测**：自带 **GNU as 2.45** 接受 `-acdnl=` 且输出格式完全匹配；
  原生 aarch64 下 `EMULATOR` 为空，**不需要 qemu**；设备无 `g++`，以 PATH 前置
  `g++ -> clang++` 包装脚本解决（不改测试脚本）。
- **两处 musl 障碍**（最小补丁，9 文件 25 行）：
  1. `src/util_impl_linux.h` 使用 glibc 私有 `sysconf(_SC_LEVEL*_CACHE_SIZE)`，
     musl 未声明 → 用 `#if defined(...)` 保护该回退块，保留上游已声明的默认值；
     **主路径（cacheInfoDict 查表、sysfs 遍历）不变**，且该 API 不被 test/test2/sample 使用。
  2. 测试驱动中 8 处 `uint jj;` —— `uint` 是 glibc typedef（等价 `unsigned int`），
     改为等价的 `unsigned int`，**测试逻辑与断言一字未改**。
- 未删除测试、未放宽断言、未跳过场景、未把失败改为通过。

## 上游测试

| 套件 | 用例数 | 说明 |
|---|---:|---|
| `test/test_all.sh` | 11 | 8 个 `make_nm*` 编码场景 + 3 个 integrated（mov / mov_imm / add_sub_adds_subs_imm） |
| `test2/test_all.sh` | 15 | 指令模式 `a b c f e l m n p r s t u w x` |

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libxbyak_aarch64.a` | 静态库 |
| `include/xbyak_aarch64/*.h` | 公共头文件 |
