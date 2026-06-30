# nasm 2.16.03 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从官方源下载源码包（因SSL证书问题，使用 curl -k 手动下载）
   - URL: https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/nasm-2.16.03.tar.gz

2. 初始化编译环境
   - 使用 ohc-run.py init-build 创建工作目录

3. 修复平台识别问题（E007/E072）
   - 更新 autoconf/helpers/config.guess 和 config.sub（从 automake 1.16 复制支持 ohos 的版本）

4. 修复 HMDFS 权限问题（E011）
   - 修改 configure 脚本中的 umask 077 为 umask 022

5. 执行标准编译流程
   - configure --prefix=/storage/Users/currentUser/usr/local
   - make -j4
   - make install DESTDIR=/storage/Users/currentUser/test-install-nasm-2.16.03
   - make install（本地安装）

6. 验证和归档
   - 质量门禁验证通过（G0-G4）
   - 创建预编译包 nasm-2.16.03-ohos-aarch64.tar.gz
   - finish 收尾归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙系统CA证书问题 | 使用 curl -k 绕过验证，手动下载源码 |
| 2 | config.guess无法识别系统 | 旧版本不支持 ohos | 更新 config.guess 和 config.sub（从已安装的 automake 1.16 复制） |
| 3 | config.status临时目录权限失败 | HMDFS文件系统 umask 077 限制 | 修改 configure 中 umask 077 为 umask 022（E011） |

## 源码修改

应用了 3 个补丁文件：
- 0001-autoconf-helpers-config.guess.patch：更新 config.guess 支持 ohos
- 0002-autoconf-helpers-config.sub.patch：更新 config.sub 支持 ohos
- 0003-configure.patch：修改 umask 077 为 umask 022

## 依赖版本

- automake 1.16（提供支持 ohos 的 config.guess/config.sub）
- clang 15.0.4
- GNU Make 4.4.1

## 验证结果

```bash
# 版本验证
/storage/Users/currentUser/usr/local/bin/nasm --version
NASM version 2.16.03 compiled on May 25 2026

# 二进制文件检查
ls -lh /storage/Users/currentUser/usr/local/bin/nasm
-rwxr-x--- 1 20001006 file_manager 3.2M 2026-05-25 17:07 nasm

ls -lh /storage/Users/currentUser/usr/local/bin/ndisasm
-rwxr-x--- 1 20001006 file_manager 1.7M 2026-05-25 17:07 ndisasm

# 质量门禁
质量报告: PASS
G1 Binary Integrity: PASS
G2 Functional: PASS (⚠️ 1)
G3 Portability: PASS
G4 Archive: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nasm-2.16.03-ohos-aarch64.tar.gz | 5.0M | 预编译包（包含 nasm/ndisasm 二进制和 man 文档） |
| 0001-autoconf-helpers-config.guess.patch | 11K | 平台识别补丁 |
| 0002-autoconf-helpers-config.sub.patch | 18K | 三元组验证补丁 |
| 0003-configure.patch | 889B | umask 修改补丁 |
| quality-report.md | - | 质量门禁报告 |

## 注意事项

1. HMDFS 文件系统的 umask 077 限制会导致 autotools 的 configure 失败，需要修改为 umask 022（E011）
2. 鸿蒙系统需要使用支持 ohos 的 config.guess 和 config.sub 文件
3. SSL 证书问题可能导致无法直接从 HTTPS 源下载，需要使用 curl -k 或 HTTP 协议

---
**编译结束**: 2026-05-25 17:11
**最终状态**: published