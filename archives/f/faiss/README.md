# FAISS 1.14.3 for HarmonyOS

## 概述
FAISS 是 Facebook AI Research 开发的高效向量相似度搜索和聚类库，支持 IVF（Inverted File Index）等多种索引类型。

## 软件信息
| 项目 | 值 |
|------|-----|
| 名称 | faiss |
| 版本 | 1.14.3 |
| 下载地址 | https://github.com/facebookresearch/faiss/archive/refs/tags/v1.14.3.tar.gz |
| 官方仓库 | https://github.com/facebookresearch/faiss |
| 许可证 | MIT |

## 编译配置
- 构建系统: CMake (C++20)
- 编译器: clang 15.0.4
- 构建类型: Release (静态库 libfaiss.a)

## OHOS 平台适配
- 禁用 GPU/MKL/Python/Metal/Extras
- BLAS/LAPACK: 使用最小 stub 实现（sgemm_/dgemm_/sgemv_）
- ARM NEON 优化自动启用
- CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64

## 构建产物
- libfaiss.a (静态库)
- faiss/ 头文件
- faiss-config.cmake (CMake 配置文件)
