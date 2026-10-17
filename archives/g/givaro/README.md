# Givaro

## 简介
Givaro 是 C++ 计算代数库，提供有限域、环、多项式等代数结构的实现。
是 fflas-ffpack、LinBox、SageMath / passagemath 计算代数栈的核心依赖。

## 基本信息
- 官网: https://github.com/linbox-team/givaro
- 源码: https://github.com/linbox-team/givaro/releases
- 许可证: CeCILL-B
- 构建系统: autotools

## 已编译版本
- 4.2.1 (2026-08-12)

## 依赖
- **gmp/6.3.0.1**（必须是开了 `--enable-cxx` 的版本，givaro 用 GMP 的 C++ 接口）

## 使用方式
```bash
conan install --requires=givaro/4.2.1 -pr ohos-native
```

⚠️ `Givaro::Modular<T>` 的特化分散在各头文件中。用总入口 `<givaro/modular.h>`
搭配 `Modular<double>`；写 `Modular<int64_t>` 会撞
`implicit instantiation of undefined template`。详见 `4.2.1/notes.md`。
