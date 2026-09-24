# libbpp-seq-omics 2.4.1 适配笔记

## 编译环境
- 构建系统：cmake；编译器 clang/clang++ 15.0.4
- 状态：built（本地交叉编译验证；上游 2 个 ctest 用例的执行由官方 CI 给出）
- 上游：https://github.com/BioPP/bpp-seq-omics ，tag v2.4.1
  （sha256 200da925b42065998d825f0b2a37e26b00a865883c85bc332beb3a94cae1e08b）
- 依赖：libbpp-seq/2.4.1（已发布，合并 bpp-core）

## 与同族的关系

Bio++ 家族中只依赖 bpp-seq 的一环。配方骨架完全复用同族先例 `libbpp-phyl`
（含 E543 的 CMAKE_<LANG>_COMPILER_TARGET 交叉目标注入与 libbpp-seq CMake 导出 shim）。
本包无 zlib 依赖、上游有 2 个测试（test_fastq / test_gff，带 example.fastq/example.gff
数据文件，WORKING_DIRECTORY 指向 test 目录）。

## 上游测试清点（源码审计，tag v2.4.1）

`test/CMakeLists.txt` 用 `file(GLOB *.cpp)` 收集，每个编译为独立程序并 `add_test` 注册，
`WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}`、`TIMEOUT 60000`。共 2 个：
test_fastq.cpp（FASTQ 格式读写）、test_gff.cpp（GFF 格式读写）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 交叉编译静默产出 x86-64 | 上游 set(CMAKE_CXX_FLAGS) 覆盖 --target（E543） | CMAKE_<LANG>_COMPILER_TARGET / CMAKE_SYSROOT 注入 |
| 2 | find_package(bpp-seq) 报 references ... libbpp-core.so 不存在 | libbpp-seq 包裁了 .so 但保留指向它的 CMake 导出 | 构建内 shim：复制依赖包、剔除 shared 目标（同 libbpp-phyl） |
| 3 | 测试进程在 OHOS 上起不来 | 构建树 shared 库斜杠相对 DT_NEEDED 无法解析 | testing 补丁：测试改链 bpp-seq-omics-static |

## 验证结果

- 本地交叉编译（x86_64 → OHOS aarch64）：构建通过，2 个上游测试与消费者测试编译成功
- 产物架构：libbpp-seq-omics.a 成员 = ARM aarch64
- 上游 ctest / test_package 执行由官方 CI 给出（本地交叉环境无法执行 aarch64 产物）
