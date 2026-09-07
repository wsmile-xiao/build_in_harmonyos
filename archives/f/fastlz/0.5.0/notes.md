# fastlz 0.5.0 适配笔记

## 上游信息
- 上游仓库: https://github.com/ariya/FastLZ
- 版本: 0.5.0（官方 tag 0.5.0，2020-02-02 release）
- 官方归档: https://github.com/ariya/FastLZ/archive/refs/tags/0.5.0.tar.gz
- SHA-256: 4bd422e06ff53e95b743818096a17bfda47f73ce14f14c7d3d74b91dd139d580

## 构建系统
- 无顶层 Makefile：库本体为单源文件 `fastlz.c` + `fastlz.h`（C90 可编译，纯 ANSI C，无外部依赖）。
- examples/ 与 tests/ 各自带 Makefile（编译 6pack/6unpack 工具与 roundtrip 测试）。
- conanfile.py 直接以 clang 编译 `fastlz.c` 生成 libfastlz.a（R33：编译器取自 Conan conf）。

## 平台适配
- 纯 C 无平台相关代码，无需补丁（patches/ 为空）。
- 无系统同名库冲突，默认静态库，支持 shared 选项。

## 上游测试
- tests/test_roundtrip.c：Level 1/2 压缩-解压 round-trip 正确性测试。
- 注意：测试运行需要 `compression-corpus` git 子模块（0.5.0 release tarball 不包含该子模块），
  本地无语料时以 test_package 的 round-trip 消费者测试覆盖（R51 已清点）。
- test_package/test.c：fastlz_compress + fastlz_decompress round-trip 断言。

## 依赖
- 无第三方依赖。
---

**编译结束**: 2026-09-06 23:57
**最终状态**: built
