# astyle 3.6.18 适配记录

## 适配范围

- 上游项目：`https://gitlab.com/saalen/astyle`
- 上游版本：`3.6.18`
- 上游提交：`7e66f6fbb11d5bd2135f73aa87b661889413da9e`
- Conan 包名：`astyle`
- 类型：开发库（对应 Debian `libastyle-dev`）
- 依赖：无外部 Conan 运行时依赖

## 构建配置

配方使用 CMake，默认 `BUILD_STATIC_LIBS=ON`，可通过 `shared=True` 构建共享库；
Java/JNI 与文档安装关闭。上游 CMake 只安装库目标，不安装头文件，因此配方在
`package()` 阶段复制 `AStyle/src/astyle.h` 和 `AStyle/src/astyle_main.h`。

## 测试设计

`test_package/test.cpp` 链接 `astyle::astyle`，调用 `AStyleMain` 格式化 C++ 片段并
校验 `AStyleGetVersion()` 返回 `3.6.18`。上游 `AStyleTest/regression-sh/run_tests.sh`
属于命令行构建入口，配方在 native `build()` 中额外构建 CLI 后运行完整回归目录；
OHOS 交叉构建不在构建主机执行目标二进制。

## 源码与完整性

- 源码归档 SHA-256：`3cf671a726e9b14e75fd9ad862dc6b5500f948a12700bc842e9bd4bc3a9a9915`
- 官方归档大小：`1147278` bytes

## 验证记录

native Linux 已完成静态/共享库构建、消费者运行测试（`NATIVE_LIBRARY_CONSUMER_PASS`、
`NATIVE_SHARED_CONSUMER_PASS`），并用安装前缀中的实际头文件和库重新链接通过
`NATIVE_PACKAGED_CONSUMER_PASS`；上游 CLI 回归为 16/16（`UPSTREAM_REGRESSION_PASS`）。
Windows 主机未被当作 OHOS
结果；OHOS arm64 目标验证仍需在正式设备/CI 环境完成。
