# libsodium — HarmonyOS/OpenHarmony 预编译包

## 软件简介

libsodium 是一个现代、易于使用的加密库，基于 NaCl (Networking and Cryptography library) 开发。它提供了用于加密、解密、签名、密码哈希等操作的高质量 API，广泛用于安全敏感型应用。

**主要功能**：
- 对称加密：ChaCha20, AES-256-GCM, AEGIS
- 非对称加密：X25519, Ed25519
- 密码哈希：Argon2, scrypt
- 数字签名：Ed25519
- 密钥派生：HKDF, BLAKE2b

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools |
| 目标平台 | ohos-aarch64 |
| 源码地址 | https://github.com/jedisct1/libsodium |

## 可用版本

| 版本 | 状态 | 补丁数 | 说明 |
|------|------|--------|------|
| 1.0.22 | ⚠️ partial | 2 | 静态库可用，动态库测试失败 |

## 编译指导

### 环境要求
- HarmonyOS/OpenHarmony aarch64 SDK
- autotools 构建工具链
- `ohc-run.py` 编译脚本

### 基本命令
```bash
# 使用 ohc-run.py 初始化编译环境
ohc-run.py init-build libsodium 1.0.22

# 执行编译流程
# Phase 1: 初始化
# Phase 2: configure + make + make install
# Phase 3: 测试验证
# Phase 4: 预编译包制作
```

## 已知限制

### E007: config.guess 无法识别 HarmonyOS
autotools 的 config.guess 无法自动识别 HarmonyOS 系统，需要补丁添加 `__OHOS__` 检测和 `ohos-linux` 三元组支持。

### HMDFS 临时文件限制
在 HMDFS 文件系统上执行 configure 时，config.status 创建临时子目录可能失败。建议使用 VPATH 构建（在 `$TMPDIR` 中构建）。

### 动态库加载问题
HarmonyOS 对动态库加载有特殊限制，即使设置 `LD_LIBRARY_PATH` 也可能无法加载。建议优先使用静态库链接方式。

## 功能验证

```bash
# 链接静态库编译测试程序
gcc -o test_sodium test.c -I/path/to/include -L/path/to/lib -lsodium -static

# 运行测试
./test_sodium
```

## 相关链接
- 官方文档：https://libsodium.gitbook.io/doc/
- GitHub：https://github.com/jedisct1/libsodium