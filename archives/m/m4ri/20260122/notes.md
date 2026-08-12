# m4ri 20260122 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
GF(2) 上的稠密矩阵运算库（Method of Four Russians），产出 `libm4ri.so`。
是 SageMath 系（linbox / fflas-ffpack 等）与 passagemath 的底层依赖。

## 关键适配
- **必须依赖 libpng**：`m4ri/io.c:29` 无条件 `#include <png.h>`，上游 configure
  并未把 PNG 做成可选项，缺头文件直接编译中断（首轮实撞
  `io.c:29:10: fatal error: 'png.h' file not found`）。故 recipe 里 `requires("libpng/1.6.58")`。
- 修 configure 的 umask 077→022（HMDFS E011）
- 删除 `lib/*.la`：其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 4 条**真实计算断言**全绿：

```
m4ri: I*B==B 通过；rank(I3)=3 通过
```

- 构造 3×3 单位阵 I 与随机阵 B，`mzd_mul` 后**逐元素**校验 I×B == B
- `mzd_echelonize` 求秩，断言 rank(I₃) == 3

断言比对计算结果本身，不是「能 dlopen」这类空转。
