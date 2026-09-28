# scrappie

scrappie 是 Oxford Nanopore Technologies 的信号处理与 basecalling 原型库，
提供原始纳米孔信号的事件检测、basecalling（callevent/mappy/seqmappy）与
sapien 模型推理，核心数据结构为 `scrappie_matrix`。

## 功能概述

- 原始信号事件检测（event detection）
- basecalling 与序列解码（raw/event table/sequence mappy）
- squiggle 匹配与信号归一化
- 可复用的矩阵运算与 BLAS 加速层

## OHOS 适配

- CMake 最低版本提升至 3.5（CMake 4 兼容），移除 `-march=native`
- SSE2/SSE4.1 内建经 sse2neon 1.9.1 映射到 NEON（shim 头 + `__v4sf` 补定义）
- GNU argp → argp-standalone/1.5.0（musl 无 argp）
- 依赖（openblas/hdf5/libaec/argp/cunit）全静态链接：
  OHOS 安全加固禁止 /storage 进程 exec-mmap conan store 的 DSO（见 E429）
- 公共头文件补装（上游 CMake 不安装），包内附带 `sse2neon_compat/` 头目录

## 构建

Conan 2.x recipe（`archives/s/scrappie/1.4.2/conanfile.py`），
profile `ohos-aarch64`；上游 CTest 19 项 + test_package 消费者用例 1 项全通过。

## 许可证

MPL-2.0（见上游 LICENSE.md）
