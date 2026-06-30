# GNU Octave

GNU Octave is a high-level interpreted language primarily intended for numerical computations and solving linear and nonlinear problems. It provides capabilities for the solution of linear algebra problems, finding roots of nonlinear equations, integrating ordinary differential equations, and manipulating polynomials.

## 功能概述

- **数值计算**: 矩阵运算、线性代数 (det, eig, svd, qr, lu, chol)
- **数学函数**: 超越函数、特殊函数、统计函数
- **图形可视化**: 2D/3D 绘图 (本构建仅包含 CLI 版本 octave-cli)
- **编程语言**: 类 MATLAB 语法，支持脚本和函数文件 (.m)
- **包管理**: 支持加载和创建扩展包

## OHOS 适配要点

### Fortran 编译器缺失
HarmonyOS 无原生 Fortran 编译器。使用 f2c (Fortran-to-C 转译器) + 自定义 gfortran wrapper 脚本作为替代方案。wrapper 脚本将 .f 文件经 f2c 转为 C，再用 clang 编译。

### f2c 类型大小修复
f2c.h 中 `integer` 类型默认为 `long int` (aarch64 上 8 字节)，而 Octave 的 `F77_INT`/`F77_INT4` 为 `int32_t` (4 字节)。必须将 f2c.h 中的 `integer`, `uinteger`, `logical`, `flag`, `ftnlen`, `ftnint` 改为 `int`。

### BLAS/LAPACK .f90 文件
BLAS 3.12.0 中部分函数使用 Fortran 90 语法 (.f90 文件，如 dnrm2.f90, drotg.f90)，f2c 无法编译。需提供 C 实现替代：
- dnrm2_, snrm2_, dznrm2_ (Euclidean norm)
- drotg_, srotg_, crotg_, zrotg_ (Givens rotation)
- dlamc3_, slamc3_ (machine epsilon)

### DGEBAL Fortran 90 语法
LAPACK 3.12.1 的 dgebal.f 使用 EXIT、CYCLE、END DO 等 Fortran 90 语法，f2c 不支持。需手动改写为 Fortran 77 语法 (GO TO + labeled CONTINUE)。

### DLAMCH 机器参数
f2c 编译的 dlamch 返回错误的机器参数，导致 Octave 启动时检测浮点格式失败。解决方案：创建 C 文件 mach-params.c 直接返回 IEEE 754 常量。

### OpenMP 缺失
HarmonyOS 无 OpenMP 运行时。创建 omp_stub.c 提供所有 OpenMP API 的单线程 stub 实现。

### Autotools 重生成循环
Octave 的 Makefile 中 autotools 规则 (aclocal, config.status recheck) 会触发重生成并卡住。需 patch 为 no-op 或手动链接。

## 依赖关系

### 编译依赖
| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| f2c | - | 预装 | Fortran-to-C 转译器 |
| BLAS | 3.12.0 | 源码编译 | 参考实现，使用 f2c |
| LAPACK | 3.12.1 | 源码编译 | 参考实现，使用 f2c |
| PCRE | 8.45 | 源码编译 | 正则表达式库，需 UTF 支持 |
| FreeType | - | 预装/源码 | 字体渲染 |
| libpng | - | 预装/源码 | PNG 图像库 |
| zlib | - | 预装 | 压缩库 |
| libohpc_compat | - | 源码编译 | reallocarray 兼容 |

### 运行依赖
- 无额外运行依赖 (静态链接)

## 参考资料

- 官网: https://www.octave.org
- 源码: https://ftp.gnu.org/gnu/octave/
- 文档: https://docs.octave.org/v8.3.0/
- f2c: https://github.com/barak/f2c
- BLAS: https://github.com/OpenMathLib/BLAS
- LAPACK: https://github.com/Reference-LAPACK/lapack
