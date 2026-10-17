# ECL (Embeddable Common-Lisp)

## 简介
ECL 是可嵌入的 Common Lisp 实现，既可作独立解释器（`bin/ecl`），
也可作为运行时链接进 C/C++ 程序（`libecl.so`）。
是 Singular、SageMath / passagemath 计算代数栈的 Lisp 后端。

## 基本信息
- 官网: https://common-lisp.net/project/ecl/
- 许可证: LGPL-2.1-or-later
- 构建系统: autotools

## 已编译版本
- 24.5.10 (2026-08-12)

## 依赖
- gmp/6.3.0.1（bignum 后端）
- readline/8.3、gc/8.2.12（Boehm GC）、libffi/3.4.4

## 使用方式
```bash
conan install --requires=ecl/24.5.10 -pr ohos-native
```

嵌入用法（见 `24.5.10/test_package/test.c`）：
```c
cl_boot(argc, argv);
cl_object r = cl_eval(c_string_to_object("(* (+ 1 2) 7)"));   /* → 21 */
cl_shutdown();
```
