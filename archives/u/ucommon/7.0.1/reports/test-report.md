# ucommon 7.0.1 设备端验证报告

## 范围

- 平台：HarmonyOS PC arm64
- Conan：2.29.1
- 配置：`ci/conan/profiles/ohos-aarch64` 作为 host/build profile
- 验证方式：`conan create` 构建配方并执行 `test_package`

## 结果

| 配置 | 结果 | 关键证据 |
| --- | --- | --- |
| `with_ssl=gnutls` | PASS | 找到 `gnutls 3.8.10`；生成并链接 `ucommon::ucommon`；程序输出 `Hello from ucommon`、`ucommon test passed` |
| `with_ssl=False` | PASS | 构建 `nossl` 后端；生成并链接 `ucommon::ucommon`；程序输出 `Hello from ucommon`、`ucommon test passed` |

消费者程序实际调用了 `String`、`Thread::sleep`、条件 TLS 初始化和 `Digest::sha256`，不是空壳测试。默认配置打包的静态库为 `libcommoncpp.a`、`libucommon.a`、`libusecure.a`。

## 未覆盖项

- 上游 `BUILD_TESTING=OFF`，未执行上游测试套件。
- 本机没有 Conan，因此未运行本机 `conan_verify`；设备端 `conan create` 是本轮 HarmonyOS 构建与消费者运行证据。
- `with_ssl=openssl` 配置未在本轮设备端执行。

构建过程中出现的 CMake `System is unknown to cmake`、jobserver FIFO `Operation not permitted` 以及 SSH 本地端口转发提示均未阻止编译、链接或消费者运行。
