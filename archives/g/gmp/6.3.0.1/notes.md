# gmp 6.3.0.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 为什么另起 6.3.0.1 这个版本

仓里已有 `gmp/6.3.0`，但它是 `--disable-shared` 的**纯静态包，且没有 `--enable-cxx`** ——
不产 `gmpxx.h` 与 `libgmpxx`。而计算代数一族（givaro / singular / linbox / fflas-ffpack）
全部走 GMP 的 **C++ 接口**，缺 gmpxx 直接 configure 失败。

故按仓库既有的 `.N` 递增惯例（参见 zlib 1.3.1 → 1.3.1.1）新增 6.3.0.1：

- 上游 tarball **与 6.3.0 完全同一份**（sha256 `a3c2b8…8898`，与 6.3.0 的 conandata 逐字一致）
- 差异只在构建配置：`--enable-cxx` + `shared=True`

两个版本并存、互不影响：只要 C 接口的下游继续用 6.3.0。

## 关键适配
- `--enable-cxx` 产出 `libgmpxx`，供 C++ 计算代数库链接
- 删除 `lib/*.la`：其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 3 条**真实计算断言**全绿：

```
gmp: C 接口 2^100 位数=31 通过；gmpxx 大整数与有理数 通过
```

- C 接口：`mpz` 求 2^100 的十进制位数 == 31
- C++ 接口：`mpz_class` 大整数乘法结果比对
- C++ 接口：`mpq_class` 有理数 1/3 + 1/6 == 1/2

断言均比对**计算结果本身**，不是「能 dlopen / 能链接」这类空转。
