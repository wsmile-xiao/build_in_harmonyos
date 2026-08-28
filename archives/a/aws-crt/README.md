# AWS Common Runtime (C++)

aws-crt（上游仓库名 aws-crt-cpp）是 AWS Common Runtime 的 C++ 发行版，为
AWS SDK 与 IoT Device SDK 提供 C++ 绑定：MQTT5/MQTT311 客户端、HTTP/1.1、
HTTP/2、WebSocket、S3、Sigv4/Sigv4a 签名、CBOR、CRC/XXHash 校验和等。

## OHOS 适配

- 构建采用上游默认的 `BUILD_DEPS=ON` 全栈源码模式：aws-lc（libcrypto）、
  s2n-tls 与全部 aws-c-* 库按 v0.38.5 固定 commit 随主库一起编译，无需外部
  Conan 依赖。
- OHOS 经 Conan toolchain 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，而 aws-c-io
  只识别 Linux/Android 来启用 epoll；配方强制 `CMAKE_SYSTEM_NAME=Linux`
  （OHOS 为 musl/epoll 兼容平台）。
- toolchain 交叉构建下 `CMAKE_CROSSCOMPILING` 恒为 TRUE，上游默认因此从不
  注册单元测试；补丁仅对 `add_subdirectory(tests)` 放开该守卫，
  `ENABLE_NET_TESTS=OFF` 在配置期剔除全部联网用例后于真机执行完整离线套件。

## 依赖关系

- 无外部 Conan 依赖；13 个 crt/* 子模块源码内嵌编译。
- 下游消费仅需链接 `aws-crt::aws-crt`，捆绑依赖经 `--whole-archive` 注入。

## 参考资料

- 上游仓库: https://github.com/awslabs/aws-crt-cpp
- 许可证: Apache-2.0
