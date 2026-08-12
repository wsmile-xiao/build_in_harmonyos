# IML (Integer Matrix Library)

## 简介
IML 提供整数矩阵的**精确**（无浮点误差）解法：零空间、线性方程组求解、行列式等。
是 LinBox、SageMath / passagemath 计算代数栈的依赖。

## 基本信息
- 官网: https://www.cs.uwaterloo.ca/~astorjoh/iml.html
- 许可证: GPL-2.0-or-later
- 构建系统: autotools

## 已编译版本
- 1.0.5 (2026-08-12)

## 依赖
- gmp（`--with-gmp-include` / `--with-gmp-lib`，不接受 `--with-gmp=<prefix>`）
- openblas（经 `--with-cblas` 提供 CBLAS；configure 默认找 ATLAS 但接受任意 CBLAS）

## 使用方式
```bash
conan install --requires=iml/1.0.5 -pr ohos-native
```
