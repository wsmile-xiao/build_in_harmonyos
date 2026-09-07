# E546: aarch64 pt_regs 结构使用 regs[] 而非 uregs[]

## 问题描述
ARM32 和 aarch64 的 `pt_regs` 结构不兼容，导致跨架构的寄存器访问代码编译失败。

## 错误特征
```
error: 'struct pt_regs' has no member named 'uregs'
error: ARM_r0 undeclared (ARM register access via uregs)
```

## 根本原因
- **ARM32 (32-bit)**: `struct pt_regs` 包含 `uregs[18]` 数组
- **aarch64 (64-bit)**: `struct user_pt_regs` 包含 `regs[31]` 数组

许多 ARM 工具（如 ltrace, strace）假设 `uregs[]` 存在，在 aarch64 上无法编译。

## 解决方案

### 方法：创建兼容宏

在头文件中定义：
```c
#ifdef __aarch64__
#define PT_REGS_GET_REG(regs, n) ((regs)->regs[n])
#else
#define PT_REGS_GET_REG(regs, n) ((regs)->uregs[n])
#endif
```

使用宏访问寄存器：
```c
// 原代码（仅 ARM32）
long r0 = regs.uregs[ARM_r0];
long r1 = regs.uregs[ARM_r1];

// 修复后（ARM32 + aarch64）
long r0 = PT_REGS_GET_REG(&regs, ARM_r0);
long r1 = PT_REGS_GET_REG(&regs, ARM_r1);
```

## 实际案例

**ltrace 0.7.3** - trace.c 寄存器访问：
```c
// 补丁 0004-ohos-aarch64-compat.patch
#ifdef __aarch64__
#define PT_REGS_GET_REG(regs, n) ((regs)->regs[n])
#else
#define PT_REGS_GET_REG(regs, n) ((regs)->uregs[n])
#endif

// 应用到所有寄存器访问
long ret = PT_REGS_GET_REG(&regs, ARM_r0);
```

## 相关信息

### 头文件
- ARM32: `<linux/ptrace.h>` → `struct pt_regs`
- aarch64: `<asm/ptrace.h>` → `struct user_pt_regs`

### 寄存器数量
- ARM32: 18 个（r0-r15 + cpsr + orig_r0）
- aarch64: 31 个通用寄存器 + sp + pc + pstate

## 验证
```bash
# 检查直接访问 uregs
grep -n "\.uregs\[" *.c

# 检查是否使用了兼容宏
grep -n "PT_REGS_GET_REG" *.c
```

## 相关知识
- E547: ARM Thumb 模式处理
