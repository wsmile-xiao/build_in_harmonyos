# dmg2img 1.6.7 适配笔记

## 编译环境
- 构建系统: makefile (raw, no configure)
- 编译日期: 2026-08-06
- 编译器: clang / clang++
- 状态: success (conan-verify passed)

## 源码来源
- 原始 URL: http://vu1tur.eu.org/tools/dmg2img-1.6.7.tar.gz (已下线)
- 替代源: https://github.com/citruz/dmg2img (GitHub fork, version 1.6.7)

## 编译步骤
1. 下载并解压 dmg2img 1.6.7 源码 (citruz/dmg2img GitHub fork)
2. 应用 4 个补丁:
   - 0001-Makefile: LZFSE 条件编译, 交叉编译 CC/CFLAGS/LDFLAGS 支持
   - 0002-dmg2img.c: LZFSE 代码用 #ifdef HAVE_LZFSE 保护
   - 0003-dmg2img.h: BT_LZFSE 定义用 #ifdef HAVE_LZFSE 保护
   - 0004-vfdecrypt.c: OpenSSL 1.1.1 API 兼容性修复
3. make CC=clang CFLAGS=... LDFLAGS=... -j1
4. 验证 dmg2img 和 vfdecrypt 二进制可执行

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LZFSE 依赖缺失 | citruz fork 硬编码了 lzfse 依赖 | 用 #ifdef HAVE_LZFSE 条件编译 |
| 2 | vfdecrypt.c 编译错误 | OpenSSL 1.1.1 API 变更 | 适配 EVP_CIPHER_CTX/HMAC_CTX 指针式 API |
| 3 | Makefile 不支持 conan 依赖 | 原始 Makefile 硬编码 CC=gcc | 传递 CC/CFLAGS/LDFLAGS 到 make 命令行 |
| 4 | conan conf.get 不支持嵌套 key | OHOS 适配版 conan 限制 | 使用 dict 访问 tools.build:compiler_executables |
| 5 | make 找不到 Makefile | conan build folder 与 source folder 不同 | cd 到 source folder 后执行 make |

## 依赖版本
- zlib/1.3.1
- bzip2/1.0.8
- openssl/1.1.1w

## 交付物
| 文件 | 说明 |
|------|------|
| dmg2img | DMG 转 IMG 工具 |
| vfdecrypt | 加密 DMG 解密工具 |
---

**编译结束**: 2026-08-06 07:47
**最终状态**: built
