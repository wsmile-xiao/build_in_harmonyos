# aws-c-auth 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C Auth Library |
| 版本 | 0.7.7 |
| 官网 | https://github.com/awslabs/aws-c-auth |
| 源码下载 | https://github.com/awslabs/aws-c-auth/archive/refs/tags/v0.7.7.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

aws-c-auth 0.7.7 提供 AWS 认证机制：
- AWS 凭证管理
- 签名版本 4（SigV4）

**注意**: 此版本不兼容 aws-crt-cpp 0.38.5，建议使用 0.10.1 版本。

## 编译步骤

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF

cmake --build build -j$(nproc)
DESTDIR=$HOME/tmp/aws-c-auth cmake --install build
```

## 参考链接

- [aws-c-auth GitHub](https://github.com/awslabs/aws-c-auth)