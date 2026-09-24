# petsc-complex 3.25.4：改 ABI 的上游开关要独立成包，变体包的验收测试必须能区分变体

> Draft: DRAFT-PETSC-COMPLEX-3254-ABI-VARIANT-SEPARATE-CONAN-PACKAGE
> Stem: `petsc-complex-3.25.4-abi-variant-separate-conan-package` — 与本名 `.kv` 成对

## 基本信息

- **ID**: DRAFT-PETSC-COMPLEX-3254-ABI-VARIANT-SEPARATE-CONAN-PACKAGE
- **严重度**: 3
- **类别**: conan-recipe-variant-design
- **触发工具**: conan|configure|make
- **阶段**: recipe-design|testing

## 错误特征

```
./configure --with-scalar-type=complex   # 不是编译开关，而是 ABI 开关
#define PETSC_USE_COMPLEX 1              # 被写进安装出来的 petscconf.h
sizeof(PetscScalar) == 2 * sizeof(PetscReal)   # double _Complex
```

两种失败模式：

1. **图不可解**。如果把 `complex` 做成 `petsc` 的一个 option，同一个
   `petsc/3.25.4` 引用只能有一个二进制。某下游要实数、另一个要复数时，解析器会把
   同一份目标文件交给两者，图根本无解。
2. **假通过**（更隐蔽）。变体包的 `test_package` 如果只调用两个变体都实现的 API
   （`VecCreate`/`VecNorm`/`MatMult`），那么在基础变体上跑同样一批断言会全绿。
   于是 CI 绿说明不了"这个包是复数变体"——配方被错写成实数构建也能过。

## 根因分析

PETSc 的 `--with-scalar-type={real,complex}` 会：

- 把 `PetscScalar` 从 `double` 变成 C99 `double _Complex`，宽度翻倍；
- 重新生成 `petscconf.h`，打开 `PETSC_USE_COMPLEX`；
- 改变所有头文件内联函数、宏定义、结构体布局与符号。

换句话说，它不是"换指令选型"，而是"换 ABI"。Conan 的包身份只有 `name/version`
两个维度，ABI 变体必须占用一个新的 name，否则无法共存。

同理，`--with-precision=<single|double|__float128>` 也是同一形状的开关。

## 解决方案

**主方案**: sibling-package-with-variant-distinguishing-test

### 1）独立包名，开关写死在 build() 里

源码 tarball 与 `petsc/3.25.x` **完全相同**，只是 configure 参数多两项：

```
--with-scalar-type=complex
--with-precision=double          # 显式写出默认值，防止上游改默认值时 ABI 悄悄变
```

包名 `petsc-complex/3.25.4`，`package_info()` 里：

```python
self.cpp_info.defines = ["PETSC_USE_REAL_DOUBLE", "PETSC_USE_COMPLEX"]
self.cpp_info.set_property("cmake_file_name", "petsc-complex")
self.cpp_info.set_property("cmake_target_name", "petsc-complex::petsc-complex")
self.cpp_info.set_property("pkg_config_name", "petsc-complex")
```

- 重复声明 ABI 宏：`PETSC_USE_COMPLEX` 本来就烘进 `petscconf.h`（`petscsys.h`
  会 include 它），但配方里再声明一遍能让生成的 CMake / pkg-config 文件自带变体
  标识，对只看 `-D` 的消费方也安全。
- 改 CMake target / pkg-config 名：万一某个目标接错了变体，**链接期**就报错
  （找不到 `petsc-complex::petsc-complex`），而不是运行期算出错误结果。

### 2）测试必须能区分变体

`test_package/test.c` 不用基础包的 smoke test，四类断言全部选成实数构建不可能
产生的可观测行为：

| 类别 | 断言 | 实数构建下会怎样 |
|------|------|------------------|
| 编译期闸门 | `#ifndef PETSC_USE_COMPLEX` / `#ifndef PETSC_USE_REAL_DOUBLE` → `#error` | 预处理就失败 |
| ABI | `sizeof(PetscScalar) == 2*sizeof(PetscReal)`；`sizeof(PetscReal)==sizeof(double)` | 第一个断言失败 |
| 数值 | `PetscAbsScalar(PetscCMPLX(3,4)) == 5` | 实数下是 3 |
| 数值 | `VecNorm((2+1i)*[1,1,1]) == sqrt(15)` | 实数下是 `2*sqrt(3)` |
| 数值 | `\|VecDot(x, i*x)\| == \|x\|^2 == 15` 且虚部非零 | 虚部恒为 0 |
| 端到端 | GMRES 解 2x2 复数方程，右端项由 `MatMult(A, x_true)` 算出（非手写），断言 `solution[0] == 1+1i` 且 `\|\|sol - x_true\|\|_2 < 1e-10` | 解不出复数 |

输出 TAP-ish 的 `ok N` / `not ok N`，末行 `assertions: N, failures: M`，
失败返回非零，CI 直接 grep。共 11 条断言。

### 3）推广到精度变体

复数 + `single` / `__float128` 需要**第三个**包名，绝不在本包上加 option ——
理由同第 1 节：精度同样改 ABI。

## 适用范围

任何"上游开关改的是 ABI 而不是指令选型"的项目：

- PETSc `--with-scalar-type` / `--with-precision`
- HDF5 / MPI 的 datatype 或 ABI 选项
- 形如 "single vs double" 的数值库构建
- protobuf lite vs full

判断标准很简单：**这个开关会不会改变已安装头文件里的某个宏、或某个公共类型的
宽度/布局？** 会，就独立成包。

## 验证

```sh
conan create archives/p/petsc-complex/3.25.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr
# test_package: assertions: 11, failures: 0
```

## 关联条目

- 同族 smens：`E### petsc 3.25.3`（self-contained serial PETSc 的 configure 范式）
- 配套条目：`petsc-complex-3.25.4-self-contained-complex-blas`（带 z 例程的
  f2cblaslapack，使复数变体无需外部 provider）
