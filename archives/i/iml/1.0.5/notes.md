# iml 1.0.5 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
Integer Matrix Library —— 整数矩阵的精确解法（零空间、线性方程组、行列式），
产出 `libiml.so`。是 linbox、SageMath / passagemath 计算代数栈的依赖。

## 关键适配

### BLAS 用 `--with-cblas`，不是 `--with-atlas-*`
首轮撞 `configure: error: ATLAS not found!`。iml 的 configure 确实以 ATLAS 为默认 BLAS
实现，但它同时接受**任意 CBLAS**，开关是 `--with-cblas` / `--with-cblas-include`
（不是 `--with-atlas-lib` / `--with-atlas-include`）。这里指向 openblas：

```
--with-cblas="-L<openblas libdir> -lopenblas"
--with-cblas-include=<openblas includedir>
```

### GMP 用 include/lib 分开的开关
iml 不接受 `--with-gmp=<prefix>`，要分别给 `--with-gmp-include` 与 `--with-gmp-lib`。

其余：删除 `lib/*.la`（其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路）。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 2 条**真实计算断言**全绿：

```
iml: nullspace 维数=1 且 A*N==0 通过
```

对 `A = [[1,2],[2,4]]`（两行成比例，秩=1，2 列）调 `nullspaceMP`：
- 断言零空间维数 == 1
- 再用 GMP 逐行算 `A·N`，断言结果全为 0

第二条是关键——只看维数对不对，拿不出"解真的是解"的证据。
