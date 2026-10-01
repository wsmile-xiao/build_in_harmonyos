# lapackpp

## 简介

LAPACK++ 是美国田纳西大学 ICL 实验室（SLATE 项目族）开发的 LAPACK 现代化 C++
封装库：在参考 LAPACK 之上提供模板化的 C++ API 与显式向量化友好的布局抽象，
s/d/c/z 四精度，覆盖 LU 分解、Cholesky、QL/QR、线性方程组、特征值与奇异值
等 LAPACK 例程族。它与 BLAS++（`blaspp`）同版本同上游发布。

## 功能

- LAPACK 例程的 C++ 模板封装（`lapack::gesv` / `potrf` / `geqrf` / `syev` / `gesvd` …）
- 强类型枚举替代 Fortran 字符参数（`lapack::Uplo` / `lapack::Op` / `lapack::Job` / `lapack::Diag`）
- 统一的列主序 / 64 位索引接口
- 标准 CMake 包配置（`find_package(lapackpp)` → `lapackpp::lapackpp`）

## OHOS 适配

- 设备原生 CMake 构建（C++17）；LAPACK 后端来自 ohpcd 已发布的
  `lapack/3.12.1`（参考实现 + flang Fortran 运行时）与前置包
  `blaspp/2024.10.26`、`cblas/3.12.1`。
- GPU 后端（cuda/hip/sycl）以 `gpu_backend=none` 禁用；纯 host API 面完整可用。
- **零补丁**：上游 CMakeLists 与源码零改动。BLAS++ 的对接（include 路径 +
  上游 finder 需要的两个私有配置变量）全部在 Conan 配方侧完成，细节见
  版本级 `notes.md`。
- 与 Linux 的差异：无 GPU 后端；静态链接顺序在配方内显式给定。

## 依赖关系

- 编译依赖：`blaspp/2024.10.26`、`lapack/3.12.1`、`cblas/3.12.1`（均 ohpcd 已发布）
- 运行依赖：无动态库依赖（静态库交付；Fortran 运行时符号由依赖链提供）

## 测试状态

- 上游 `test/run_tests.py` 共 **181** 个计划项（HOST 177 + DEVICE 4），
  本次 **NOT_RUN**：上游 tester 在 `test/CMakeLists.txt` 内以 `lapacke_found`
  硬门禁早退，而提供 LAPACKE 的 `lapacke/3.12.1` 配方已合入 main 但尚未发布
  到 ohpcd 制品仓——`conan install --requires=lapacke/3.12.1` 实核返回
  `Unable to find 'lapacke/3.12.1' in remotes`。
  按 R36 不在配方 PR 内捎带适配依赖。详见版本级 `notes.md`。
- 鸿蒙侧消费者测试（`test_package/`）**18 条数值断言全通过**：
  版本宏/运行时函数、potrf 回乘、gesv 求解、getrf+getrs 残差、trtri 逆矩阵、
  geqrf+orgqr 正交性、syev 特征值、gesvd 奇异值。

## 参考资料

- 上游仓库：https://github.com/icl-utk-edu/lapackpp
- 版本：v2024.10.26（tag）
- 相关包：blaspp/2024.10.26、lapack/3.12.1、cblas/3.12.1、lapacke/3.12.1（待发布）；下游 SLATE
