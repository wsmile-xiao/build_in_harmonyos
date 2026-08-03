# aws-c-http 0.10.14 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: built

## 编译步骤
使用 Conan 2.x recipe 下载 aws-c-http 官方源码，并在同一个 recipe 内私有下载、构建和安装 AWS CRT 依赖源码。对外只暴露 `aws-c-http/0.10.14` 一个 Conan 包，避免 PR 级别新增多个 recipe。
当前配方对 `aws-c-http` 主库开启 `BUILD_TESTING=ON`，在私有 CRT 依赖安装完成后执行上游 `ctest --output-on-failure`，再安装打包产物；`test_package` 继续验证下游消费者初始化和 HTTP status 文本查询。由于本路径 A 基础适配采用 no-TLS 私有 CRT 构建，recipe 同时设置 `ENABLE_NET_TESTS=OFF`，并从上游 test driver 中移除 TLS/proxy-only 源文件和工具目标，保留 HTTP/H1/H2/WebSocket/HPACK/NO_PROXY 等核心上游单元测试实际执行。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AWS C runtime 依赖链需要 common/cal/compression/io | 上游 CMake 通过包配置查找依赖，单独适配会引入多个 recipe | 在 aws-c-http recipe 内私有构建依赖源码，安装到临时 prefix，并把静态库和头文件一起打包 |
| 2 | 部分依赖配置会继续查找 OpenSSL/s2n | 本次基础适配不引入外部 TLS 依赖 | 使用 BYO_CRYPTO，并在私有安装 prefix 中移除不需要的 CMake dependency 查找块 |
| 3 | 上游测试默认把 TLS/proxy 源码和 elasticurl/h2benchmark 工具一起编译 | no-TLS 构建下缺少 `aws_tls_*` 实现会导致测试目标编译失败 | 保留核心上游 CTest，禁用网络/TLS/proxy-only 用例和工具目标，最终通过 OpenDesk/CI 日志记录真实通过率 |

## 依赖版本
- aws-c-common 0.12.6（私有源码构建）
- aws-c-cal 0.9.13（私有源码构建）
- aws-c-compression 0.3.2（私有源码构建）
- aws-c-io 0.26.3（私有源码构建）
