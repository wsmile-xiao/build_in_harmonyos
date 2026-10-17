# SDSL Succinct Data Structure Library

Succinct Data Structure Library (SDSL) 是 C++11 实现的紧凑数据结构库，涵盖 40 篇研究论文的成果，包括位向量、整数向量、Wavelet 树、压缩后缀数组（CSA）、压缩后缀树（CST）、LCP 数组、RMQ 结构等。本归档适配的版本为 2.1.1。

## 功能概述

- **位向量与秩选择结构**：bit_vector、rank_support、select_support、sd_vector
- **整数向量**：int_vector、int_vector_buffer、int_vector_mapper
- **Wavelet 树**：wt_huff、wt_int 等字节/整数.afabet 实现
- **压缩后缀数组与后缀树**：csa_wt、cst_sada/cst_sct3，含 SA/LCP 构造算法
- **RMQ 与编码器**：rmq_support_sparse_table、coder_elias_gamma/delta/fibonacci

## OHOS 适配

- 使用 CMake 构建，产物为 `libsdsl` + `libdivsufsort`/`libdivsufsort64`，头文件位于 `include/sdsl`
- 官方 release tarball 不含 `external/libdivsufsort` 与 `external/googletest` 子模块内容（空目录），配方在 `source()` 阶段单独下载对应 release 并放到预期路径
- 上游测试为 24 个 gtest 程序共 162 个 TEST/TEST_F；其中 10 个无需在线语料（bits/coder/int_vector 等共 46 个用例）在配方 `build()` 内离线运行，14 个需下载 Pizza&Chili 语料（faust/zarathustra/moby）的重型测试不在 CI 内运行，原因见版本 notes
- aarch64 无 SSE4.2，`BUILTIN_POPCNT` 保持关闭，走通用实现；无需平台补丁

## 依赖关系

- 编译/运行依赖：无（libdivsufsort 与 googletest 随源码 vendor，不作为 conan 依赖）
- 系统依赖：无（pthread/m 由 OHOS libc 提供）

## 参考资料

- 源码仓库：https://github.com/simongog/sdsl-lite
- 发布 tag：https://github.com/simongog/sdsl-lite/releases/tag/v2.1.1
- 上游文档：https://github.com/simongog/sdsl-lite#readme
