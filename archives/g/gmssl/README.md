# gmssl

## 简介
GmSSL — 支持国密算法（SM2/SM3/SM4/SM9/ZUC）的密码库，提供兼容 OpenSSL 的 API 接口。

## OHOS 适配
- CMake 无法识别 HarmonyOS 平台，需创建工具链文件设置 `CMAKE_SYSTEM_NAME=Linux`
- 测试套件因 ELF 签名要求无法直接运行（平台限制，不影响功能）
- 编译产物需通过 `ohc-run.py sign-elf` 工具签名后才能执行

## 排除与替代
- 如需标准 TLS/SSL，推荐使用 openssl 而非 gmssl

## 依赖
- 编译依赖：CMake 3.0+, C11 编译器
- 运行依赖：无

## 功能验证
```bash
gmssl version
echo "hello" | gmssl sm3
```

## 参考
- 源码：https://github.com/guanzhi/GmSSL
