# FAISS for HarmonyOS

## 概述
FAISS 是 Facebook AI Research 开发的高效向量相似度搜索和聚类库，支持 IVF（Inverted File Index）等多种索引类型。

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.14.3 | built | 2026-07-22 | C++17, BLAS stub |
| 1.15.0 | built | 2026-08-28 | C++20, BLAS stub, 新增 SVS/LTO 选项禁用 |

---

## 1.15.0

### 软件信息
| 项目 | 值 |
|------|-----|
| 名称 | faiss |
| 版本 | 1.15.0 |
| 下载地址 | https://github.com/facebookresearch/faiss/archive/refs/tags/v1.15.0.tar.gz |
| 官方仓库 | https://github.com/facebookresearch/faiss |
| 许可证 | MIT |

### 编译配置
- 构建系统: CMake 3.24+ (C++20)
- 编译器: clang 15.0.4
- 构建类型: Release (静态库 libfaiss.a)

### OHOS 平台适配
- 禁用 GPU/MKL/SVS/Python/Metal/Extras/C_API/LTO
- BLAS/LAPACK: 使用最小 stub 实现（sgemm_/dgemm_/sgemv_）
- ARM NEON: CMake patch (fix-neon-simd-on-ohos.patch) 在 project() 后强制 CMAKE_SYSTEM_PROCESSOR=aarch64，确保 faiss CMake SIMD 选择命中 aarch64 分支，10 个 NEON TU 编入 libfaiss.a（conan_toolchain 的 tc.variables CACHE set 被 project() 覆盖回 unknown，必须用 patch 在 project() 之后重设）
- CMAKE_SYSTEM_NAME=HarmonyOS（OHOS→HarmonyOS 由 CMakeToolchain 映射），CMAKE_SYSTEM_PROCESSOR=aarch64（patch 在 project() 后强制设置）

### 与 1.14.3 的主要差异
1. C++ 标准从 C++17 提升到 C++20（`CMAKE_CXX_STANDARD=20`）
2. CMake 最低版本要求提升至 3.24
3. 新增 `FAISS_ENABLE_SVS` 选项（Intel Scalable Vector Search），需禁用
4. 新增 `FAISS_USE_LTO` 选项（Link-Time Optimization），需禁用
5. 新增 RaBitQ 量化器、Panorama 索引等特性
6. BLAS stub 方案与 1.14.3 完全通用，无需改动

### 构建产物
- libfaiss.a (静态库, ~17.6 MB)
- faiss/ 头文件 (~150+)

---

## 1.14.3

### 软件信息
| 项目 | 值 |
|------|-----|
| 名称 | faiss |
| 版本 | 1.14.3 |
| 下载地址 | https://github.com/facebookresearch/faiss/archive/refs/tags/v1.14.3.tar.gz |
| 官方仓库 | https://github.com/facebookresearch/faiss |
| 许可证 | MIT |

### 编译配置
- 构建系统: CMake (C++17)
- 编译器: clang 15.0.4
- 构建类型: Release (静态库 libfaiss.a)

### OHOS 平台适配
- 禁用 GPU/MKL/Python/Metal/Extras
- BLAS/LAPACK: 使用最小 stub 实现（sgemm_/dgemm_/sgemv_）
- ARM NEON 优化自动启用
- CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64

### 构建产物
- libfaiss.a (静态库)
- faiss/ 头文件
- faiss-config.cmake (CMake 配置文件)
