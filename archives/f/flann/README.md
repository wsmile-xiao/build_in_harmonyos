# FLANN

FLANN (Fast Library for Approximate Nearest Neighbors) 是一个高效的近似最近邻搜索库, 自动能根据数据集特征选择最优索引算法与参数, 在高维空间下提供比精确搜索快数个量级的查询性能。广泛用于计算机视觉 (特征匹配)、机器学习、信息检索等领域。

## 功能概述
- 多种索引结构: 随机 kd-tree、分层 k-means、LSH、自动调参索引等
- 近似 k 近邻 (knn) 与半径搜索
- C 与 C++ 两套 API
- 索引的保存/加载 (基于 lz4 压缩序列化)
- 可选 OpenMP / MPI / CUDA 加速 (本适配默认关闭)

## OHOS 适配
- C++ 库, CMake 构建
- 上游对 **lz4 是硬依赖** (`flann/util/serialization.h` 直接 `#include <lz4.h>`, 顶层 CMakeLists 用 `pkg_check_modules(LZ4 REQUIRED liblz4)`, 无 CMake 选项可关闭)。HarmonyOS PC 无 system liblz4 / pkg-config, 制品仓亦无 lz4 配方, 故 **vendor lz4 1.9.4 源码** (`lz4.c` + `lz4hc.c`) 编为静态 PIC 内部目标, 链入 `libflann_cpp.so`/`libflann.so`, 产物自包含、无运行期 lz4 依赖。
- 显式 `CMAKE_SYSTEM_NAME=Linux` (flann 唯一的 Linux 专属分支还要求 GNUCC, clang 不取, 故安全)。
- 关闭 Python/Matlab/CUDA 绑定、示例、文档、GTest 单测与 OpenMP/MPI, 仅产出核心 C/C++ 库。
- 删除上游 `lib/cmake/flann` 导出, 下游统一通过 conan 的 `flann::flann` 目标链接。

## 依赖关系
- **编译依赖**: 无 (lz4 已 vendor 进源码树)
- **运行依赖**: 无 (vendored lz4 已静态链入)

## 参考资料
- 官网: https://github.com/flann-lib/flann
- 论文: Muja & Lowe, "Fast Approximate Nearest Neighbors with Automatic Algorithm Configuration", VISAPP 2009
