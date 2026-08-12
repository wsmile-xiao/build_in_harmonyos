# cddlib

## 简介
cddlib 实现双描述法（Double Description Method），在多面体的 H-表示（半空间不等式组）
与 V-表示（顶点/射线）之间互相转换。SageMath / passagemath 计算代数栈的底层依赖。

## 基本信息
- 官网: https://github.com/cddlib/cddlib
- 源码: https://github.com/cddlib/cddlib/releases
- 许可证: GPL-2.0-or-later
- 构建系统: autotools

## 已编译版本
- 0.94m (2026-08-12)

## 依赖
- gmp（有理数精确计算路径）

## 使用方式
```bash
conan install --requires=cddlib/0.94m -pr ohos-native
```

⚠️ **链接 `libcddgmp` 必须先 `#define GMPRATIONAL`**，否则 `cdd.h` 把数值类型
降级成 `double`，编译链接均通过但运行时 Signal 11。另外 `cdd.h` 用到 `FILE`
却不自带 `<stdio.h>`，须先 include。详见 `0.94m/notes.md`。
