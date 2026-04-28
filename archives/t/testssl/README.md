# testssl.sh

## 简介
TLS/SSL 安全测试工具，检查服务器的密码套件、协议版本和加密缺陷。

## OHOS 适配
- 纯 Shell 脚本工具，无需编译
- 需移除捆绑的 x86_64 OpenSSL 二进制文件
- 创建系统 OpenSSL 符号链接到 bin/ 目录
- 需修补 AWS-LC 兼容性（openssl version -d → openssl version）

## 依赖
- bash >= 3.2
- OpenSSL
- 标准 Unix 工具 (sed, awk, grep)

## 功能验证
```bash
testssl.sh --version
testssl.sh https://example.com
```

## 参考
- 官网: https://testssl.sh
- 源码: https://github.com/testssl/testssl.sh
