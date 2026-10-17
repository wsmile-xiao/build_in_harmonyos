# libsigmf

## 简介
libsigmf 是一个仅头文件的 C++17 库，用于读写 SigMF（Signal Metadata Format）元数据，
提供 `sigmf::SigMF` / `sigmf::Global` / `sigmf::Capture` / `sigmf::Annotation` 四个核心类，
支持 core、antenna、capture_details、signal 等命名空间扩展。Apache-2.0 许可。

## OHOS 适配
- Header-only 库（CMake INTERFACE 目标），`package_id` 恒定，无 shared/fPIC 选项
- 上游发布包不含 submodule 内容，改用 Conan 制品仓依赖并以 `USE_SYSTEM_JSON=ON`
  `USE_SYSTEM_FLATBUFFERS=ON` 消费；`flatc` 代码生成由 flatbuffers 依赖的 bindir 提供
- 零补丁；`cmake_minimum_required(VERSION 3.0)` 经 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x
- 上游 2 个 `add_test` 示例在 `build()` 内直接运行并输出机器标记

## 依赖
- 编译依赖：clang, cmake
- 第三方：nlohmann_json/3.12.0、flatbuffers/25.12.19（ohpcd 制品仓已有版本）

## 功能验证
```bash
# 头文件安装检查
ls $PREFIX/include/sigmf/sigmf.h
ls $PREFIX/include/sigmf/sigmf_core_generated.h
# 消费者测试（二进制退出码 0 且输出 test_libsigmf passed）
./test_libsigmf
```

## 参考
- 源码：https://github.com/deepsig/libsigmf
- 版本：1.0.2（标签 `v1.0.2`）
- 许可证：Apache-2.0
