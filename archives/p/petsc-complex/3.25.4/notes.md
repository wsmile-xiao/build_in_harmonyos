# petsc-complex 3.25.4 — OHOS 适配笔记

## 1. 这是什么

上游源码与 `petsc/3.25.4` 完全相同（同一份 release snapshot），差别只在 configure
时固定了 `--with-scalar-type=complex`。既然源码相同，为什么不把它做成 `petsc` 的一个
option？因为这不是编译开关，而是 **ABI 开关**：

- `PetscScalar` 从 `double` 变成 C99 `double _Complex`，宽度翻倍；
- 生成的 `petscconf.h` 里 `PETSC_USE_COMPLEX` 被打开，所有头文件的内联函数、
  宏定义随之改变；
- 目标文件里符号名、结构体布局全部不同。

若做成 option，同一个 Conan 图里两个分别需要实数和复数 PETSc 的下游就无法同时解析
（同一个 `petsc/3.25.4` 引用只能有一个二进制）。因此独立成包 `petsc-complex/3.25.4`。

## 2. 构建

沿用 `petsc/3.25.3` 已验证的 Python-configure 流程，`--with-fc=0 --with-mpi=0
--download-f2cblaslapack=1` 保持自包含（无需 MPI、无需 Fortran、无需外部
BLAS/LAPACK provider）。新增四项：

```
--with-petsc-arch=arch-ohos-c-opt
--with-x=0
--with-scalar-type=complex
--with-precision=double
```

### 2.1 `--with-petsc-arch` 是必需的，不是可选优化

PETSc 的构建树目录名由 **构建主机** 决定
（`config/PETSc/options/arch.py:32`）：

```python
arch = 'arch-' + sys.platform.replace('cygwin','mswin')   # 在 Linux 上是 'linux'
arch += '-' + clanguage.lower() + '-opt'
```

配方里 `make PETSC_DIR=… PETSC_ARCH=arch-ohos-c-opt` 用的却是自定义名。configure
不知道这个名字，就只会建出 `arch-linux-c-opt`；随后 make 找不到构建树：

```
gmakefile:72: arch-ohos-c-opt/lib/petsc/conf/files: No such file or directory
make: *** [GNUmakefile:17: .../arch-ohos-c-opt/include/petscconf.h] Error 2
```

（本地实测复现：先按原配方 configure，再 `make PETSC_ARCH=arch-ohos-c-opt` → 上面
这条错误。）把同一个名字用 `--with-petsc-arch=` 一并告诉 configure 即可，二者从此
永远一致，也不再依赖 worker 的 `sys.platform`。

### 2.2 `--with-x=0` 关掉画图用的 X11 后端

PETSc 的 `--with-x` 是**自动探测**，探的是**构建主机**的 X11 头文件，不是目标平台。
worker 上只要有 `libX11-dev`，X 画图后端就会被编进 `libpetsc.a`；`PetscInitialize`
会引用这些符号，于是**每一个消费方**在链接期都被迫带 `-lX11`：

```
undefined reference to `XGetGeometry'
undefined reference to `XSetIOErrorHandler'
undefined reference to `XSetForeground'
```

OHOS 上没有 X11，这些后端毫无用处，直接 `--with-x=0` 关掉，保持自包含。
（本地实测：不带这一项时，消费者测试程序必须额外 `-lX11` 才能链接成功。）

### 2.3 复数标量

`--with-precision=double` 是显式写出的：PETSc 的默认精度就是 double，但复数变体的
消费方一定关心精度，把默认值写死可以避免上游将来改默认值时悄悄改变 ABI。

BLAS/LAPACK 仍然走 `--download-f2cblaslapack=1`。已确认自带的
`f2cblaslapack-3.8.0.q2` 里含复数例程（`blas/zgemm.c`、`blas/zdotc.c`、
`lapack/zheev.c`），所以复数构建不会退化成"缺 z 例程"的半成品。

编译参数：`COPTFLAGS='-fPIC -O2'`，`AR=llvm-ar`，`RANLIB=llvm-ranlib`，
编译器取自 `tools.build:compiler_executables`（缺省 clang / clang++）。

## 3. 与 petsc/3.25.3 的关系

| 项 | petsc/3.25.3 | petsc-complex/3.25.4 |
|----|--------------|----------------------|
| 源码 | petsc-3.25.3.tar.gz | petsc-3.25.4.tar.gz |
| scalar type | real（默认） | **complex** |
| `PetscScalar` | `double` | `double _Complex`（2x） |
| conan defines | `PETSC_USE_REAL_DOUBLE` | `PETSC_USE_REAL_DOUBLE`, **`PETSC_USE_COMPLEX`** |
| Conan 包名 | `petsc` | `petsc-complex` |
| CMake 目标 | `petsc::petsc` | `petsc-complex::petsc-complex` |

`PETSC_USE_COMPLEX` 其实已经烘进安装出来的 `petscconf.h` 里（`petscsys.h` 会 include
它），消费方不用额外 `-D` 也能拿到一致的 ABI。配方里再声明一遍是为了让生成的
CMake / pkg-config 文件本身就带这个变体标识，对只看 `-D` 的场景也安全。

## 4. 验收测试为什么这样写

`test_package/test.c` 不复用 `petsc/3.25.3` 的 smoke test。理由很直接：如果变体包的
测试是一个实数 PETSc 也能跑过的程序，那它根本验证不了"这个包是复数变体"，属于
**假通过**。所以这里的断言全部选成实数 PETSc 不可能产生的可观测行为：

- `sizeof(PetscScalar) == 2 * sizeof(PetscReal)`（ABI 层面）
- 开头 `#ifndef PETSC_USE_COMPLEX / #ifndef PETSC_USE_REAL_DOUBLE #error`，
  实数构建连预处理都过不去（编译期闸门）
- `PetscCMPLX(2.5, -1.25)` 的实部虚部往返
- `PetscAbsScalar(3+4i) == 5`（模长真的用到了虚部；实数下这是 3）
- `VecNorm((2+1i)*[1,1,1]) == sqrt(15)`（实数下是 2*sqrt(3)）
- `|VecDot(x, i*x)| == |x|^2 == 15` 且虚部非零
- `MatGetValue` 取回 `1-1i`
- GMRES 解一个 2x2 复数方程，右端项由 `MatMult(A, x_true)` **算出来**而不是手写，
  检查解的第 0 分量是 `1+1i`（虚部穿过整个求解过程存活）且 `||sol - x_true||_2 < 1e-10`

共 12 条断言，输出 TAP-ish 的 `ok N` / `not ok N` 与末行
`assertions: 12, failures: 0`，失败时返回非零，CI 可以直接 grep。

这套测试在本机（x86_64 + gcc、同一份 3.25.4 源码、同样的 configure 参数）实跑过：

```
ok 1 - sizeof(PetscScalar) == 2 * sizeof(PetscReal)
...
ok 11 - KSP solution[0] == 1 + 1i (imaginary part survives the solve)
ok 12 - ||KSP solution - x_true||_2 < 1e-10
assertions: 12, failures: 0
```

安装出来的 `petscconf.h` 里也确实有 `#define PETSC_USE_COMPLEX 1`
与 `#define PETSC_USE_REAL_DOUBLE 1`（第 155/163 行），第 2.1、2.2 两条结论都是在
这次实跑里发现的。

## 5. 已知问题 / 后续

- 本包不含 Fortran 接口（`--with-fc=0`），与 `petsc/3.25.3` 一致。
- 未开启 shared；复数 shared 变体贴合 `options = {"shared": ...}`，但当前默认关，
  与同族实数包保持一致的静态产物。
- 如需复数 + 非 double 精度（single / __float128），应当再建独立包名，不要在本包加
  option —— 理由同第 1 节。
