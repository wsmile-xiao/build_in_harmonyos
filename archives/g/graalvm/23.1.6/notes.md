# GraalVM SDK 23.1.6 适配笔记

## 概述
- 三方库名称：GraalVM SDK (org.graalvm.sdk:graal-sdk)
- 版本：23.1.6
- 上游仓库：https://github.com/oracle/graal
- 许可证：Universal Permissive License (UPL), Version 1.0
- 类型：Java 库（JAR），预构建二进制包

## 适配策略
GraalVM SDK 是 Java 库，提供 Polyglot API、Native Image API 等接口。
本配方采用"预构建二进制"模式，直接从 Maven Central 下载 JAR 打包。

### 源码说明
- GraalVM SDK 源码位于 oracle/graal 仓库的 `sdk/` 目录
- 构建需要 `mx` 工具和 JDK 21+，不适合 conan 的 C/C++ 构建流程
- Maven Central 上的 JAR 是官方发布的预构建产物，SHA256 已验证

### 版本号
- 23.1.6 对应 Maven Central 上 org.graalvm.sdk:graal-sdk 的版本
- GraalVM 23.1.x 系列基于 JDK 21
- oracle/graal 仓库标签 vm-23.1.5 是最接近的源码标记

## 依赖
- 无外部 C/C++ 依赖
- 运行时需要 Java 环境 (JDK 21+)

## 测试
- test_package 验证 JAR 文件存在、非空且为合法 ZIP 格式
- 上游无 C/C++ 测试套件（GraalVM SDK 是 Java 库）

## 已知限制
- GraalVM SDK 是 Java 库，在 C/C++ 项目中作为纯数据包使用
- 下游 C/C++ 项目如需使用 GraalVM Native Image C API，需额外安装 GraalVM JDK