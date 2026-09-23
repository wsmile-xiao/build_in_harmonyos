# superlu 7.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4
- 状态: built（conan-verify 全门禁通过，待 CI 合并后 upload 发布为 published）

## 历史核验（W0b）

- 前版本 superlu 5.3.0（archives/s/superlu/5.3.0，状态 built，无 conan 配方）：cmake + 内置 CBLAS + 禁用 Fortran。
- 历史踩坑比对：
  1. CMake 版本兼容（5.3.0 需 patch 到 3.5）→ 7.0.1 上游已升到 `cmake_minimum_required(VERSION 3.12)`，**无需 patch**
  2. 禁用 Fortran → 已遵循（`enable_fortran=OFF` + `XSDK_ENABLE_Fortran=OFF`）
  3. 内置 CBLAS → **改用外部 openblas/0.3.34**（偏离历史方案，理由见下）
- 环境语义可迁移性：cmake/clang/make 在 CI 能力矩阵内 ✅，历史命令 CI 可逐字执行。

## 关键决策：外部 openblas 替代内置 CBLAS

历史 5.3.0 用内置 CBLAS（`enable_internal_blaslib=ON`）。7.0.1 配方改用制品仓已发布的
`openblas/0.3.34`（W0 已验证发布），理由：

1. 性能：内置 CBLAS 是参考实现，性能低（5.3.0 notes 亦注明）；openblas 为 ARM 优化实现。
2. 生态：内置 CBLAS 会在包内产出一个通用 `libblas.a`，与制品仓 `blas`/`openblas` 包基名冲突，
   下游同时引用时链接混乱（R26 风险面扩大）。
3. 产物干净：单一 `libsuperlu.a`，BLAS 符号由 openblas 提供。

用法：cmake 变量 `TPL_BLAS_LIBRARIES` 指向 openblas 静态库（XSDK 上游机制，无需改源码）。
此时上游 CMake 自动加 `-DUSE_VENDOR_BLAS`，openblas 提供 f2c 风格符号（`dgemv_` 等）兼容。

## 编译步骤（探索阶段实测）

1. 源码：https://github.com/xiaoyeli/superlu/archive/refs/tags/v7.0.1.tar.gz
2. cmake 配置（源外构建）：
   `-DCMAKE_INSTALL_PREFIX=... -Denable_internal_blaslib=OFF -DTPL_BLAS_LIBRARIES=<openblas.a> -DXSDK_ENABLE_Fortran=OFF -Denable_fortran=OFF -Denable_tests=ON -Denable_examples=ON`
3. `make -j4` → 100% 成功，零源码修改
4. `ctest --output-on-failure` → **24/24 通过**（Total 2.49s）
5. `make install DESTDIR=$TEST_PREFIX` → staging 验证：libsuperlu.a + 12 头文件 + cmake config + pkgconfig

## 上游测试清点与实测（R51 三步法）

清点：TESTING/ 注册 4 个驱动（s_test/d_test/c_test/z_test，对应 single/double/complex/complex16），
每个 6 个 ctest 用例（4 LA：`-t LA -n {9,19} -s 2 -l {0,10000000}`；2 SP：`-t SP -f EXAMPLE/g20.rua`），
共 **24 个注册用例**。

实测（本机 ohos-aarch64，与 CI 同源 profile）：

```
100% tests passed, 0 tests failed out of 24
Total Test time (real) =   2.49 sec
```

- s_test: 6/6 通过
- d_test: 6/6 通过
- c_test: 6/6 通过
- z_test: 6/6 通过

通过率 24/24 = 100%。上游测试未做任何修改。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | XSDK 默认禁用内置 BLAS | 7.0.1 `set(USE_XSDK_DEFAULTS TRUE)` 使 `enable_internal_blaslib` 默认 OFF | 顺势改用外部 openblas（见关键决策） |
| 2 | cmake 4.1.2 对旧 CMakeLists 兼容 | 5.3.0 时代问题（cmake_minimum_required 2.8.12） | 7.0.1 上游已要求 3.12，无需处理 |

## 源码修改

**无**（零 patch）。7.0.1 上游 CMakeLists 对 OHOS 交叉编译完全兼容
（E092 HarmonyOS 平台告警为 cmake 提示性信息，不阻塞）。

## Conan 配方要点

- `requires("openblas/0.3.34")`（制品仓已发布）
- `generate()`：`enable_internal_blaslib=OFF`、`TPL_BLAS_LIBRARIES=<openblas libdir>/libopenblas.a`、
  禁用 fortran/matlabmex/doc/examples/tests
- 默认 `shared=False`（libsuperlu.a，纯 C 无 runtime 传播问题）
- `package_info()`：libs=["superlu"]，system_libs=["m"]，cmake target superlu::superlu
- test_package：真实 dgssv API 调用，求解 4x4 稀疏系统并校验解误差 < 1e-8（R34）

## 验证结果

```bash
# conan create（conan-verify G2 干净构建）:
superlu/7.0.1@ohpcd/stable (test package): RUN: "./test_superlu"
solution: 1.000000 2.000000 3.000000 4.000000
superlu 7.0.1 dgssv sparse solve: OK

# G0-G4 + L2/L4/L5 门禁: 全部 PASS
# R26 系统同名库: PASS（包内无系统同名库）
```

## 交付物

| 文件 | 说明 |
|------|------|
| libsuperlu.a | SuperLU 核心静态库（c/s/d/z 四精度统一库） |
| slu_*.h supermatrix.h superlu_enum_consts.h superlu_config.h | 公共头文件 |
| superlu.pc / superluConfig.cmake | pkg-config 与 CMake 配置 |

## 注意事项

1. superlu 7.0.1 四种精度（single/double/complex/complex16）默认全开，打进单一 libsuperlu.a
2. METIS 默认禁用（TPL_ENABLE_METISLIB=OFF），与上游默认一致
3. XSDK_INDEX_SIZE 默认 32 位（int_t = int32）
---

**编译结束**: 2026-09-18 18:15
**最终状态**: built
