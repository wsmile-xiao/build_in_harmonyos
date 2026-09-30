# DRAFT: clang 集成汇编器不支持 GNU gas 的 .func/.endfunc 指令

- Source package: tinymembench/0.4（上游 tag v0.4，手写 makefile，C + 各架构 .S 汇编）
- 发现于：tinymembench 0.4 OHOS 前置适配（W4 本机交叉编译验证）

## 现象

用 OHOS SDK clang（--target=aarch64-linux-ohos）编译含 `.func \function_name` /
`.endfunc` 指令的 `.S` 文件（大写 .S，经 C 预处理器）时报错：

```
<instantiation>:3:1: error: unknown directive
.func aligned_block_copy_ldpstp_x_aarch64
^
tinymembench-0.4/aarch64-asm.S:40:1: note: while in macro instantiation
```

## 根因

`.func`/`.endfunc` 是 GNU gas 的 DWARF 调试注记指令（标记汇编函数边界，
仅供调试器使用，不影响生成的机器码）。clang 的**集成汇编器**
（integrated assembler）没有实现这两个指令，遇到即报 `unknown directive`。
tinymembench 在 `.macro asm_function` 宏内使用 `.func \function_name`，
并在每个汇编函数结尾 `.endfunc`，四个架构文件（x86-sse2.S / arm-neon.S /
aarch64-asm.S / mips-32.S）共 46 处。

## 解法

删除所有 `.func`/`.endfunc` 行（纯注记，删除不改变任何生成代码）。
OpenEmbedded 上游 master 对 tinymembench 也做了同样修改
（`0001-asm-Delete-.func-.endfunc-directives.patch`）。

```python
# 配方 conandata.yml patches + source() 中 apply_conandata_patches(self)
```

## 验证

- 本机（OHOS SDK clang 15，aarch64-linux-ohos）：无补丁编译失败于
  `unknown directive .func`；打补丁后 0 警告编译链接成功，
  ELF64/AArch64，NEEDED 仅 libc.so。
- 对 gas 不产生影响（DWARF 注记可选）。

## 附带发现

同包 `main.c` 使用 `ioctl()` 但未 `#include <sys/ioctl.h>`：glibc 经其它
头间接暴露原型而 musl 不会，交叉编译报 C99 隐式函数声明警告；补 include
消除。

## 适用范围

所有在 `.S` 里使用 `.func/.endfunc` 的项目移植到 clang/OHOS 工具链时必踩。
