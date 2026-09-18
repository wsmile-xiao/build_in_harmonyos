# libgff

## 简介
libgff 是 COMBINE-lab 维护的轻量 C++ 库，用于解析 GFF/GTF 基因注释文件，被 salmon 等 RNA-seq 工具使用。

## OHOS 适配
- CMake 工程，上游无条件构建静态库（`add_library(gff STATIC ...)`），Conan 侧 `package_type = "static-library"`
- 无外部依赖，无需补丁；OHOS aarch64 (clang 15) 直接交叉编译通过
- 上游无注册测试（无 `enable_testing()`/`add_test()`），适配验证由 `test_package` 消费者测试承担：解析内联 GFF3 并断言转录本/基因 ID、exon 数与属性

## 依赖
- 无编译依赖

## 功能验证
```bash
conan create archives/l/libgff/2.0.0 -pr:h=ohos-aarch64
# test_package: test_libgff（GffReader 解析 + 断言）
```
