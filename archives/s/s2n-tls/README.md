# s2n-tls — OpenHarmony 移植指南

## 软件简介

s2n-tls 是 AWS 开发的一个 TLS/SSL 协议实现，设计目标是简单、安全、高性能。它是 Amazon 的开源项目，广泛应用于 AWS 服务中。

**主要特性**：
- 简洁的设计：代码量小，易于审计和验证
- 安全优先：采用防侧信道攻击设计，默认启用安全配置
- 高性能：针对现代 CPU 架构优化
- 标准兼容：支持 TLS 1.0-1.3 协议

**适用场景**：
- 嵌入式设备的 TLS 通信
- 需要轻量级 TLS 库的应用
- 对安全性要求较高的网络应用

## 构建系统

- 构建系统：CMake（推荐）/ Autotools
- 依赖项：OpenSSL 或 AWS libcrypto
- 目标平台：HarmonyOS/OpenHarmony aarch64

## 可用版本

| 版本 | 状态 | 补丁数 | 备注 |
|------|------|--------|------|
| 1.7.2 | partial | 0 | 基础功能可用，部分测试未通过 |

## 编译指导

### 通用注意事项
- s2n-tls 需要密码学库支持（OpenSSL 或 AWS libcrypto）
- 默认使用 CMake 构建系统，也支持 Autotools
- 需要设置正确的交叉编译工具链

### OpenHarmony 特定配置
- 设置 `CMAKE_TOOLCHAIN_FILE` 指向 OpenHarmony 工具链
- 配置依赖库路径（libcrypto）
- 根据需求启用/禁用测试套件

## 补丁清单

当前版本无需补丁，原生源码支持 OpenHarmony 编译。

## 已知限制

1. **部分测试未通过**：由于 OpenHarmony 平台特性，部分测试用例需要适配
2. **依赖管理**：需要手动配置 libcrypto 路径
3. **功能验证**：建议在实际应用中进行充分的功能回归测试

## 功能验证

### 基本验证命令
```bash
# 检查库文件
ls -l packaging/pkg-s2n-tls-1.7.2/lib/libs2n.a

# 检查头文件
ls -l packaging/pkg-s2n-tls-1.7.2/include/s2n.h

# 运行基本测试（需要链接 libcrypto）
# 根据实际环境配置测试
```

### 集成验证
建议通过实际应用测试 TLS 连接功能。

## 参考链接

- 官方仓库：https://github.com/aws/s2n-tls
- 官方文档：https://aws.github.io/s2n-tls/
- OpenHarmony 编译记录：参见各版本目录下的 PROGRESS.md
