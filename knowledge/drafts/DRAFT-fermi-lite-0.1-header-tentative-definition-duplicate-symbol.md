# DRAFT-fermi-lite-0.1: 头文件暂定定义（tentative definition）导致 duplicate symbol

## 症状

链接 `fml-asm` 时报：

```
ld.lld: error: duplicate symbol: rle_auxtab
>>> defined at rle.h:33 (./rle.h:33)
>>>            misc.o:(rle_auxtab) in archive libfml.a
>>> defined at rle.c:7 (.../rle.c:7)
>>>            rle.o:(.rodata+0x0) in archive libfml.a
```

## 根因

`rle.h` 中写的是：

```c
const uint8_t rle_auxtab[8];   // 只有声明、没有初始化 → 暂定定义 (tentative definition)
```

C 语言中，**无初始化器的全局数组声明在头文件里是暂定定义**：每个包含该头文件的编译单元（misc.c、rope.c、rle.c）都会为它生成一个符号。在 GCC 旧行为（`-fcommon`）下这些符号会合并；而现代 Clang 默认 `-fno-common`，多个强定义直接冲突 → `duplicate symbol` 链接失败。

## 方案

头文件只留纯声明，定义收敛到唯一 .c 文件：

```c
/* rle.h */
extern const uint8_t rle_auxtab[8];

/* rle.c */
const uint8_t rle_auxtab[8] = { 0x01, 0x11, 0x21, 0x31, 0x03, 0x13, 0x07, 0x17 };
```

## 验证

1. `make CC=clang AR=llvm-ar -j1` 链接通过，生成 `libfml.a` 与 `fml-asm`；
2. `./fml-asm test/MT-simu.fq.gz > MT.fq`（退出码 0，输出 2 条 unitig）；
3. conan create + test_package（调用 `fml_assemble()`）通过。

## 适用边界与限制

- 适用于**头文件内无初始化器全局数组/变量**的 C 代码（const 表、lookup 表等）；
- 若数组在头文件内**带初始化器**（`= { ... }`），每个 TU 都会产生副本，同样需要 extern 化（否则是每个 TU 私有副本而非链接冲突，行为更隐蔽）；
- 修复前后 ABI 不变：符号名、类型、对齐均一致，仅从「每 TU 一个 common」变为「唯一强定义 + extern 引用」。

## 反例

- 不能用 `-fcommon` 编译参数掩盖（CI/其他构建者环境可能不开，问题复发）；
- 不能简单删除该全局（rle.c 与引用方都需要它）。