# fflas-ffpack 2.5.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
Finite Field Linear Algebra Subroutines / Package —— 有限域上的稠密线性代数
（矩阵乘法、消元、求秩、解方程），**header-only**。
是 LinBox、SageMath / passagemath 计算代数栈的核心依赖。

## header-only 但依赖不是

包本身只装头文件（无 `.so`/`.a`），但它**在头文件里直接调用 givaro 与 BLAS**：
- `--with-givaro=<prefix>` 指向 givaro/4.2.1
- `--with-blas-libs="-L<openblas libdir> -lopenblas"` 指向 openblas

因此 test_package 的价值格外高：header-only 包最容易「装上了、编不过」——
装出来只是一堆头，只有真去编译链接一段用到 givaro + BLAS 的代码，
才知道这两条链在鸿蒙上是否真的通。

其余：删除 `lib/*.la`（其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路）。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 2 条**真实计算断言**全绿：

```
fflas-ffpack: GF(101) 上 A*I==A 通过；rank=2 通过
```

- `FFLAS::fgemm` 在 GF(101) 上算 `A × I`，**逐元素**比对结果 == A
- `FFPACK::Rank` 求 `[[1,2],[3,4]]` 的秩，断言 == 2（det = −2 ≠ 0 故可逆）

两条都真正走到了 givaro（域运算）与 BLAS（gemm）后端。
