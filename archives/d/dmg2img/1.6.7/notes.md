# dmg2img 1.6.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-24
- 编译器: clang / clang++
- 状态: success

## 编译步骤
1. 下载并解压 dmg2img 1.6.7 源码
2. 应用 2 个补丁（Makefile 调整、vfdecrypt.c OpenSSL API 兼容修复）
3. 修改 Makefile 设置 CFLAGS 和 LDFLAGS
4. make 编译
5. 手动安装二进制到目标目录
6. 独立目录安装验证通过
7. 预编译包制作完成

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | vfdecrypt.c 编译错误 | OpenSSL 1.1.1 API 变更（EVP_CIPHER_CTX、HMAC_CTX 结构体不再透明） | 适配 OpenSSL 1.1.1+ API |
| 2 | Makefile 不支持交叉编译 | 原始 Makefile 硬编码 CC=gcc | 修改 Makefile 添加 CFLAGS/LDFLAGS 支持 |

## 依赖版本
- zlib >= 1.3.1
- bzip2 >= 1.0.8
- openssl >= 1.1.1w

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| dmg2img-1.6.7-ohos-aarch64.tar.gz | 68KB | 主包 |

## 注意事项
- packaging 目录还包含 debug tar.gz 和已解压的 pkg 目录（待清理）
