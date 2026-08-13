# LinBox

## 简介
LinBox 是精确线性代数库，提供整数与有限域上的行列式、秩、线性方程组求解、
Smith 标准形等运算。是 SageMath / passagemath 计算代数栈的**顶层聚合库**——
它把 givaro、fflas-ffpack、ntl、flint、iml、openblas、gsl、mpfr、gmp 串在一起。

## 基本信息
- 官网: https://github.com/linbox-team/linbox
- 许可证: LGPL-2.1-or-later
- 构建系统: autotools

## 已编译版本
- 1.7.0 (2026-08-12)

## 依赖
givaro/4.2.1、fflas-ffpack/2.5.0、iml/1.0.5、**mpfr/4.2.2.1**、ntl、flint、
openblas、gsl、gmp/6.3.0.1

⚠️ mpfr 必须用 **4.2.2.1**：4.2.2 装出的 `libmpfr.la` 里 `dependency_libs` 烤死了
`//lib/libgmp.la`，链接 `liblinbox.la` 时 libtool 顺着它递归解析并失败。

## 使用方式
```bash
conan install --requires=linbox/1.7.0 -pr ohos-native
```

消费方注意：`Givaro::Integer` **没有 `get_str()`**，只重载了 `operator<<`，打印走 iostream。
