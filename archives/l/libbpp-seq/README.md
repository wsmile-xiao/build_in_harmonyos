# libbpp-seq

Bio++ Sequence library：面向系统发育与序列分析的 C++ 基础库，提供字母表（DNA/RNA/蛋白/密码子）、序列与容器、比对打分、序列 IO（Fasta/Mase/Clustal/Phylip/GenBank/Nexus 等）及遗传密码等模块。

## 功能概述

- 字母表：DNA、RNA、蛋白、密码子、RNY、词字母表及类型判定工具（AlphabetTools）
- 序列：BasicSequence、SequenceTools（基序查找、互补/转录/反向、一致性统计、Bowker 检验）
- 容器：VectorSequenceContainer、VectorSiteContainer、比对容器与迭代器
- IO：Fasta、Mase、Clustal、Phylip、GenBank、Nexus、Stockholm、Phred 等格式读写
- 遗传密码：标准及多种线粒体遗传密码翻译

## OHOS 适配

- 构建系统为 CMake，原生构建（build = target = OHOS/aarch64），`BUILD_TESTING=ON` 构建并运行上游 7 个 ctest 用例。
- 强依赖同版本 `libbpp-core/2.4.1`（提供 `bpp-core` 4.1.0 CMake 包）；Conan 包名前缀 `lib`，生成的 `libbpp-seq-config.cmake` 不遮蔽上游 `bpp-seq-config.cmake`，下游 Bio++ 模块可继续 `find_package(bpp-seq CONFIG)`。
- 上游 `cmake_minimum_required(VERSION 2.8.11)`，通过 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 进入兼容模式，不改上游源码；补丁 2 个（portability 1 个 + testing 1 个，测试源码与断言零改动）。
- 上游同时构建 `bpp-seq-static` 与 `bpp-seq-shared`（`OUTPUT_NAME` 均为 `bpp-seq`，SOVERSION 12），ctest 改链 static 目标（OHOS loader 无法解析构建树 shared 的斜杠相对 DT_NEEDED）；两个产物均打包。

## 依赖关系

- 编译依赖：libbpp-core/2.4.1
- 运行依赖：同上（链接时需要 bpp-core 的核心类型与数值工具）

## 参考资料

- 上游仓库：https://github.com/BioPP/bpp-seq
- 文档：https://github.com/BioPP/bpp-documentation/wiki
- API 文档：https://pbil.univ-lyon1.fr/bpp-doc/bpp-seq/html/
