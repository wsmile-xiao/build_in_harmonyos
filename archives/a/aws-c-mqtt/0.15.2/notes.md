# aws-c-mqtt 0.15.2 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-18
- 编译器: clang
- 状态: built

## 编译步骤
使用 Conan 2.x recipe 下载 aws-c-mqtt 官方源码，并在同一个 recipe 内私有下载、构建和安装 AWS CRT 依赖源码。对外只暴露 `aws-c-mqtt/0.15.2` 一个 Conan 包，避免 PR 级别新增多个 recipe。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AWS C runtime 依赖链需要 common/cal/compression/io/http | 上游 CMake 通过包配置查找依赖，单独适配会引入多个 recipe | 在 aws-c-mqtt recipe 内私有构建依赖源码，安装到临时 prefix，并把静态库和头文件一起打包 |
| 2 | 部分依赖配置会继续查找 OpenSSL/s2n | 本次基础适配不引入外部 TLS 依赖 | 使用 BYO_CRYPTO，并在私有安装 prefix 中移除不需要的 CMake dependency 查找块 |
| 3 | CI Worker 访问 GitHub 源码偶发超时 | Worker 网络对 github.com 不稳定 | 保留官方 URL 作为来源，并补充 SHA256 校验一致的镜像 URL 作为下载兜底 |

## 验证
- 源码镜像均通过 SHA256 校验。
- `test_package` 编译并链接 `aws-c-mqtt`，覆盖基础初始化与依赖链接场景。
- 上游网络/会话测试不纳入本次基础适配 CI，避免依赖不稳定的运行环境。

## 依赖版本
- aws-c-common 0.12.6（私有源码构建）
- aws-c-cal 0.9.13（私有源码构建）
- aws-c-compression 0.3.2（私有源码构建）
- aws-c-io 0.26.3（私有源码构建）
- aws-c-http 0.10.14（私有源码构建）
