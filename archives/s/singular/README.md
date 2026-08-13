# Singular

## 简介
Singular 是面向交换代数、代数几何与奇点论的计算机代数系统，
擅长多项式运算与 Gröbner 基计算。产出 `libSingular.so` 等库与 `bin/Singular`。
是 SageMath / passagemath 计算代数栈的多项式后端。

## 基本信息
- 官网: https://www.singular.uni-kl.de/
- 源码: https://github.com/Singular/Singular/releases
- 许可证: GPL-2.0-or-later
- 构建系统: autotools

## 已编译版本
- 4.4.1 (2026-08-13)

## 依赖
ntl、flint、readline、**mpfr/4.2.2.1**、cddlib/0.94m、gmp/6.3.0.1

⚠️ mpfr 必须用 **4.2.2.1**：4.2.2 装出的 `libmpfr.la` 里 `dependency_libs` 烤死了
`//lib/libgmp.la`，链接 `libsingular_resources.la` 时报
`'//lib/libgmp.la' is not a valid libtool archive`。

## 构建开关
`--disable-doc --disable-polymake --without-python --disable-gfanlib`

## 使用方式
```bash
conan install --requires=singular/4.4.1 -pr ohos-native
```

嵌入用法见 `4.4.1/test_package/test.cpp`：`siInit` 起内核 → `rDefault` 建环 →
`pp_Mult_qq` 做多项式乘法。
