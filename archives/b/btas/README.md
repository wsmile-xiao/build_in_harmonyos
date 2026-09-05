# BTAS — Basic Tensor Algebra Subprograms

BTAS 是 Valeev Group 开发的 C++17 header-only 张量代数库,为量子化学与科学计算提供 Range/索引、`Tensor`/`TensorView`/`TensorMap`、逐元素运算、dot/scal/axpy/ger/gemv/gemm 线性代数原语、张量缩并(contract)以及 CP 分解等高级功能。

## 功能概述

- `btas::Range`/`btas::DEFAULT::index`:基于 Boost.Container `small_vector` 的默认索引类型(栈序,rank≤6)
- `btas::Tensor<T, Range, Storage>`:N 维稠密张量容器(默认 `std::vector` 存储)
- `TensorView`/`TensorMap`:零拷贝视图与外部存储映射
- 线性代数原语:`dot`/`scal`/`axpy`/`ger`/`gemv`/`gemm`,generic(纯 C++)与 BLAS 后端
- 张量缩并:`btas::contract`、`element_wise_contract`
- 高级功能:CP 分解(CP-ALS/RALS/DF-ALS/Tucker/Coupled-CP)
- 可选 Boost.Serialization 序列化支持、可选 BLAS++/LAPACK++ 绑定

## OHOS 适配

- **库形态**:上游 CMake 工程将 BTAS 声明为 `INTERFACE` 库,安装产物只有 `btas/` 头树 + 由 `btas/version.h.in` 配置生成的 `btas/version.h`;本包按相同规则生成该头,不做编译。
- **feature 宏自动探测**:`btas/features.h` 用 `__has_include` 探测 Boost.Iterator/Container,`btas/defaults.h` 在宏未定义时默认 `BTAS_TARGET_MAX_INDEX_RANK=6`,因此消费者不需要任何额外编译定义,包含路径由 Conan 依赖图传递。
- **BLAS/LAPACK 绑定**:上游默认开启(`BTAS_USE_BLAS_LAPACK=ON`),依赖 blas++/lapack++(BLAS/LAPACK 的 C++ 封装层);OHOS 制品仓无这两个包的配方,故采用上游支持的 `BTAS_USE_BLAS_LAPACK=OFF` 配置。generic 后端完整支持 dot/scal/axpy/ger/gemv/gemm/contract;仅 SVD(`gesvd`)按上游设计无 generic 实现,调用会抛 `btas::exception`(见 `btas/generic/gesvd_impl.h`)。
- **Boost.Serialization**:上游可选组件;制品仓的 boost 二进制不含 `libboost_serialization`,`BTAS_HAS_BOOST_SERIALIZATION` 未定义,张量序列化 API 不参与编译(与上游 CMake 探测失败时的行为一致)。

## 依赖关系

- **编译/运行依赖**(强制):Boost ≥ 1.71(实际使用 headers、container、iterator;random 供测试)
- **可选**(本包未启用):BLAS++/LAPACK++、Boost.Serialization

## 参考资料

- 上游仓库:https://github.com/ValeevGroup/BTAS
- 许可证:BSD-3-Clause(见源码 `LICENSE.md`)
