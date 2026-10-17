# aws-c-mqtt 0.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang
- 状态: built

## 适配方案

### Fat Package 模式
aws-c-mqtt 0.14.0 采用 fat package 模式，将所有 AWS CRT 依赖（aws-c-common 0.12.6、
aws-c-cal 0.9.13、aws-c-compression 0.3.2、aws-c-io 0.26.3、aws-c-http 0.10.14）
作为 private_sources 下载并从源码编译，最终打包为一个自包含的 conan 包。

此模式与仓库中已有的 aws-c-http/0.10.14 配方一致，原因：
1. aws-c-common/0.12.6 和 aws-c-io/0.26.3 未作为独立 conan 包发布到制品仓
2. aws-c-http/0.10.14 本身就是 fat package，不提供 aws-c-common 的 cmake modules
3. aws-c-mqtt 的 CMakeLists.txt 需要 find_package(aws-c-common REQUIRED) 获取 cmake modules

### 构建顺序
aws-c-common → aws-c-cal (BYO_CRYPTO) → aws-c-compression → aws-c-io (BYO_CRYPTO) → aws-c-http → aws-c-mqtt

### OHOS 平台适配
- aws-c-common: 添加 HarmonyOS/OHOS 到平台检测条件
- aws-c-io: 添加 HarmonyOS/OHOS 到 Linux/Android 平台分支
- aws-c-cal: 注入 include(CTest) 以提供 BUILD_TESTING option
- 所有依赖: 注入 Threads::Threads fallback 以解决 OHOS 上 Threads 未定义问题
- BYO_CRYPTO=ON 用于 aws-c-cal 和 aws-c-io，剥离 s2n-tls/openssl 依赖

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-c-common/0.12.6 不在制品仓 | 只有 0.14.3 发布 | 使用 fat package 模式从源码编译 |
| 2 | aws-c-io/0.26.3 不在制品仓 | 只有 0.27.5 发布 | 使用 fat package 模式从源码编译 |
| 3 | aws-c-http 是 fat package 不提供 cmake modules | package() 不复制 cmake config | 将 aws-c-http 也作为 private source 编译 |
| 4 | OHOS 上 Threads::Threads 未定义 | 平台差异 | 在每个依赖的 CMakeLists.txt 注入 fallback |
| 5 | s2n-tls/openssl 依赖在 OHOS 上不可用 | 平台限制 | BYO_CRYPTO=ON 剥离 TLS 依赖 |
---

**编译结束**: 2026-08-27 15:36
**最终状态**: built
