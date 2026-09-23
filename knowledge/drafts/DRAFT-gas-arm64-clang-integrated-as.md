# DRAFT: GAS 语法 ARM64 汇编经 clang 集成汇编器零补丁编译 + dynarec OHOS 可行性

> 来源：mupen64plus-core 2.6.0 适配（N64 模拟器核心 dynarec ARM64 后端，任务 #6728，2026-09-09）
> 状态：草稿（随 PR 提交，定稿编号由主编确认）

## 问题场景

模拟器核心的动态重编译器（dynarec/JIT）在交叉编译到 OHOS 时的三个疑虑：

1. **ARM64 汇编后端能否编译**：new_dynarec 的 arm64 后端是裸 GAS 汇编
   （linkage_arm64.S，含 .macro/.globl/.hidden/.type 等完整 GAS 语法）
2. **C↔汇编的桥接管线**：asm_defines.c 编译产物中提取结构体偏移生成
   asm_defines_gas.h 的管线是否跨工具链可用
3. **运行时可行性**：dynarec 用 mmap PROT_EXEC 生成可执行代码页，
   OHOS 沙箱是否禁止（W^X）

## 实测结论（OHOS clang 15.0.4，aarch64-linux-ohos）

| 疑虑 | 结论 |
|------|------|
| GAS 语法 ARM64 .S 编译 | ✅ clang 集成汇编器（默认开启）原生支持，`clang -c foo.S` 零补丁 |
| asm_defines 生成管线 | ✅ `grep -a '@ASM_DEFINE' <asm_defines.o>` 对 LLVM bitcode（-flto）产物同样命中 |
| -flto 与 .S 混合链接 | ✅ bitcode + ELF 混合，lld 正常处理 |
| mmap PROT_EXEC 运行时 | ✅ 匿名映射无限制，dlsym/mprotect 符号在导出表实测可用 |
| 端到端 | ✅ 真机跑 ROM_OPEN→CIC 检测全链路（dynarec 数据结构初始化路径）|

## 关键机制

```make
# 上游 Makefile 的 .S 规则就是 $(COMPILE.c)（C 编译器驱动）：
$(OBJDIR)/%.o: $(SRCDIR)/%.S $(SRCDIR)/asm_defines/asm_defines_gas.h
	$(COMPILE.c) -o $@ $<     # clang -c → integrated assembler
```

asm_defines 管线（跨平台 trick）：asm_defines.c 在结构体里构造
`"\n@ASM_DEFINE offsetof_x 0x1234\n"` 字节串 → 编译产物无论 ELF 还是
LLVM bitcode，`grep -a` 都能扫出 → 生成 `.h` 给 .S 用。

## 适用边界与退路

- ✅ `.S`（GAS 语法，大小写 S = 先过 cpp）经 `$(CC) -c` 编译的项目
- ❌ `.asm`（nasm 语法，x86 专属）——交叉不可编，用 `NO_ASM=1` 走解释器
  （mupen64plus 上游支持该降级，性能降但 API 全）
- Makefile 硬编码独立 as 的项目：patch 构建规则改 `$(CC) -c`

## 价值

N64 模拟器核心（r4300 仿真 + dynarec）在 OHOS PC 的完整可行性证明；
对 ppsspp（JIT ARM64）、各类 retroarch 核心（含 ARM64 汇编优化路径）
直接适用。JIT 类应用在 OHOS 的「能编译+能运行」双结论一次给出。

## 关联

- E016（汇编指令不支持 → 禁汇编）——本条是先验证「直接可编」的正面对偶
- E045（mmap RWX 平台限制）——本条补充 OHOS 上 PROT_EXEC 匿名映射无限制
  的实测结论
