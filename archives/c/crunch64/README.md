# crunch64

crunch64 是 Rust 实现的 N64 压缩库，提供 Yaz0、Yay0、MIO0 压缩/解压及旧 gzip 格式压缩的 C API。

HarmonyOS 归档提供原生 arm64 C 静态库、头文件和 MIT 许可证。Rust 和 OpenSSL 仅为构建工具依赖；
C/C++ 消费者通过 Conan 的 `crunch64::crunch64` CMake target 链接，无需安装 Rust。
当前不提供独立 CLI 或 Python 扩展。
构建时仍会生成测试专用 Python 扩展，执行全部上游 Python 测试；它不进入交付包。

`0.6.2` 修复了 Yay0/MIO0 在小输入上的缓冲区上界与整数溢出问题，保持上游数据格式及 ABI。
运行测试包含全部355项上游 Rust/C/Python 检查，以及6项消费者测试，其中包含实际调用鸿蒙设备信息 API 的文件映射测试。
构建与运行限定为原生 HarmonyOS armv8；其他平台和架构尚未验证。

- 上游：[decompals/crunch64](https://github.com/decompals/crunch64)
- 版本构建、补丁原因和验证摘要：`0.6.2/notes.md`；完整原始日志保存在本地 `0.6.2/reports/`，不纳入 Git 提交。
- 构建工具：`rust-toolchain/1.97.1`、`openssl/3.5.6.1.1`、Clang、CMake、Ninja，以及运行 Conan 的原生 Python 解释器和对应共享库（用于上游绑定测试）。

在本仓库根目录、HarmonyOS PC 上：

```sh
conan create archives/c/crunch64/0.6.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=crunch64/*
```
