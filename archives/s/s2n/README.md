# s2n TLS

## 简介

s2n（Signal to Noise）是 AWS 开发的 TLS 协议的 C99 实现，专注于安全性和性能。它是一个纯静态库，提供现代 TLS 1.3 支持以及向后兼容的 TLS 1.2。

## OHOS 适配

- **构建系统**: CMake
- **产物类型**: 静态库（libs2n.a），无可执行文件
- **平台特性**: CMake 自动探测系统特性（OpenSSL 版本、支持的加密算法等）
- **已知问题**: 
  - CMake 显示 "System is unknown" 警告但不影响编译
  - G0 干净构建验证在 Python subprocess 中可能失败，需手动验证

## 排除与替代

无排除项。s2n 作为纯静态库，不提供命令行工具。

## 依赖

- **编译依赖**: OpenSSL libcrypto（1.1.1w 或更高版本）
- **使用依赖**: 需要在链接时提供 libcrypto 和 pthreads

## 功能验证

```bash
# 验证静态库安装
ls -lh ~/usr/local/lib/libs2n.a
# 应显示约 2.5MB 的静态库文件

# 验证头文件
ls -lh ~/usr/local/include/s2n.h
# 主头文件约 182KB，另有 unstable/ 子目录的扩展头文件

# 查看库内容
llvm-ar -t ~/usr/local/lib/libs2n.a | wc -l
# 应包含约 122 个目标文件
```

## 参考

- **官方仓库**: https://github.com/aws/s2n-tls
- **文档**: https://aws.github.io/s2n-tls/
- **安全设计**: https://github.com/aws/s2n-tls/blob/main/docs/USAGE-GUIDE.md