# cddlib 0.94m 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
双描述法（Double Description Method）多面体计算库，产出 `libcdd.so` 与 `libcddgmp.so` 两个库。
是 SageMath 系与 passagemath 的底层依赖。

## 关键适配
- 修 configure 的 umask 077→022（HMDFS E011）
- 删除 `lib/*.la`：其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路

## 消费方必看的两个头文件坑

### 1）链 libcddgmp 必须先 `#define GMPRATIONAL`——否则编译链接全过、运行时 Signal 11

cddlib 装出**两套 ABI 不同**的库：

| 库 | 数值类型 |
|---|---|
| `libcdd` | `double` |
| `libcddgmp` | `mpq_t`（GMP 有理数） |

而 `cdd.h` 是**同一个头**，靠 `GMPRATIONAL` 宏决定 `mytype` 展开成哪种。
链 `libcddgmp` 却忘了定义该宏时，头文件把 `mytype` 降级成 `double`，
于是调用方按 8 字节 double 传参、库按 `mpq_t` 结构体解释——
**编译通过、链接通过、一运行就 Signal 11**。

首轮 test_package 就是这么挂的。这类错误 dlopen-only 的空转测试**永远发现不了**，
必须做真实计算断言才暴露。

### 2）`cdd.h` 用到 `FILE` 却不自带 `<stdio.h>`

必须在 include `cdd.h` 之前先 `#include <stdio.h>`，否则一串
`unknown type name 'FILE'`。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 4 条**真实计算断言**全绿：

```
cddlib: 单位正方形顶点数=4 通过
```

由单位正方形的 4 条半空间不等式（x≥0, y≥0, x≤1, y≤1）经 `dd_DDMatrix2Poly`
求 V-表示，断言顶点数 == 4。走的是有理数（GMP）路径。
