# cauchy

Cauchy Mathematic Compiler：将 MATLAB/Octave 脚本翻译为 C++（Eigen 后端）的库与 cauchymc/cauchydeclgen 工具。

## 上游信息
- 上游: https://bitbucket.org/cyrille/cauchy（已失效）
- 发行版源码: Ubuntu `cauchy_0.9.0.orig.tar.bz2`（.hg tag v0.9.0）
- 协议: LGPL-2.1-or-later
- 依赖: Eigen3

## OHOS 适配
- CMake 构建，静态库；依赖 eigen/3.4.0。
- 现代 CMake 需 cmake_minimum_required>=3.5；去掉 SHARED（OHOS 默认静态）。
- xUnit/Asserts.h 的 std::complex 前向声明改 #include <complex>（libc++ 兼容）。
- 产物：libCauchy.a、libCauchyXUnit.a、libm2mml.a + bin/cauchymc、bin/cauchydeclgen、bin/cauchymake。

## 依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| eigen | 3.4.0 | header-only 线性代数（生成的 C++ 代码消费） |

> 注意：cauchymc 的 MATLAB→C++ 代码生成路径在本机存在 SIGSEGV（上游运行时缺陷），
> 详见 notes.md 已知限制；库本身构建与 consumer ABI 验证通过。
