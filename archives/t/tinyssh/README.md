# TinySSH

## 简介
小型、安全的 SSH 服务器实现，使用现代加密算法（Ed25519、Curve25519、Chacha20-Poly1305），代码量小易于审计。

## OHOS 适配
- 无外部依赖，无需源码修改
- Makefile 构建系统，configure 脚本直接支持

## 依赖
- 无（自包含加密实现）

## 功能验证
```bash
tinysshd --help
```

## 参考
- 源码: https://github.com/janmojzis/tinyssh
