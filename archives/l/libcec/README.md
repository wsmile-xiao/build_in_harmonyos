# libcec

## 简介
libCEC (Pulse-Eight libCEC) 是用于控制 CEC（Consumer Electronics Control）能力 HDMI
设备（电视、功放、机顶盒）的 C/C++ 库，同时提供 `cec-client` / `cecc-client` 命令行
客户端。8.1.7 版本核心为 C++（CMake 构建），附 Rust/.NET/Node/Python 可选绑定。

## OHOS 适配
- CMake 构建；设备无 `whoami`，上游 SetBuildInfo.cmake 的 `string(STRIP)` 空值报错，
  需以 `DISABLE_BUILDINFO=ON` 关闭内嵌构建信息（官方可复现构建选项）
- 沿用项目 json-c 同款做法，`CMAKE_SYSTEM_NAME=Linux` 使 CMake 生成带 SONAME 的
  版本化共享库（libcec.so.8 → libcec.so.8.1.7），cec-client 的 cecloader 按此加载
- 上游无独立 C++ 测试目标（无 ctest/enable_testing、无 make check）；唯一测试入口为
  可选 Rust 绑定（ENABLE_RUST_LIB=OFF 默认关闭，需 cargo）

## 依赖
- 编译依赖：clang, make, cmake
- 运行依赖：libc，无三方库依赖

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libcec.so*
# CLI 冒烟（无 CEC 硬件时正常初始化并报错打开串口）
cec-client --help
# 消费者/鸿蒙专项测试
test_libcec && test_libcec_ohos
```

## 参考
- 源码：https://github.com/Pulse-Eight/libcec
- 文档：https://pulse-eight.github.io/libcec/