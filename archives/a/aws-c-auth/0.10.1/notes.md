# aws-c-auth 0.10.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-04-24
- 编译器: Clang 15.0.4
- 状态: built

## 编译步骤
使用 Conan 2.x recipe 下载 aws-c-auth 官方源码，并在同一个 recipe 内私有下载、构建和安装 AWS CRT 依赖源码。对外只暴露 `aws-c-auth/0.10.1` 一个 Conan 包，避免 PR 级别新增多个 recipe。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AWS C runtime 依赖链需要 common/cal/compression/io/http/sdkutils | 上游 CMake 通过包配置查找依赖，单独适配会引入多个 recipe | 在 aws-c-auth recipe 内私有构建依赖源码，安装到临时 prefix，并把静态库和头文件一起打包 |
| 2 | 部分依赖配置会继续查找 OpenSSL/s2n | 本次基础适配不引入外部 TLS 依赖 | 使用 BYO_CRYPTO，并在私有安装 prefix 中移除不需要的 CMake dependency 查找块 |
| 3 | 旧依赖 recipe 的 replace_in_file 重复执行不幂等 | CI 重试时 Conan 复用源码缓存 | 不再导出/执行这些依赖 recipe，所有私有源码 patch 均在 auth recipe 的 source() 中用存在性检查保护 |

## 版本升级说明
从 0.7.7 升级到 0.10.1 的原因：
- aws-crt-cpp 0.38.5 需要 aws-c-auth >= 0.10.0
- 添加了新的凭证提供者 API
- 改进了 SigV4 签名性能

## 验证结果
- 产物为纯静态库。
- `test_package` 编译并链接 `aws-c-auth`，覆盖基础初始化与依赖链接场景。
- 上游认证/网络集成测试不纳入本次基础适配 CI，避免依赖不稳定的运行环境。

## 依赖版本
- aws-c-common 0.12.6（私有源码构建）
- aws-c-cal 0.9.13（私有源码构建）
- aws-c-compression 0.3.2（私有源码构建）
- aws-c-io 0.26.3（私有源码构建）
- aws-c-http 0.10.14（私有源码构建）
- aws-c-sdkutils 0.2.4（私有源码构建）
