# gnutls 3.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: failed（平台限制）

## 编译步骤

1. 初始化构建：`ohc-run.py init-build gnutls 3.8.4 --url=file:///storage/Users/currentUser/tmp/builds/gnutls-3.8.4.tar.xz`
2. 修改 config.sub 和 config.guess 支持 HarmonyOS 识别（E072）
3. 修改 configure 中的 umask 设置（E011）
4. ✅ **configure 成功完成**（重大进展）
5. ❌ **make 失败**：遇到新的平台限制

## 重大进展

### configure 成功完成（首次gnutls在HarmonyOS上configure成功）
- Host/Target system: aarch64-unknown-linux-ohos
- Build system: aarch64-unknown-linux-ohos
- Compiler: clang
- Install prefix: /storage/Users/currentUser/usr/local
- 所有依赖检测成功：nettle, hogweed, gmp, libtasn1, libcrypto, libz, libbrotlienc, libbrotlidec, libzstd

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 签名工具路径错误 | elf_sign_tool不存在 | 使用正确路径binary-sign-tool ✅ |
| 2 | E072 config.guess不识别HarmonyOS | 缺少HarmonyOS检测逻辑 | 添加aarch64:HarmonyOS:*:* → aarch64-unknown-linux-ohos ✅ |
| 3 | E072 config.sub不识别ohos三元组 | 缺少ohos-linux映射 | 添加ohos-linux → linux-ohos映射（3处修改）✅ |
| 4 | E011 umask限制 | configure中umask 077导致HMDFS失败 | 修改configure中的umask为022 ✅ |
| 5 | wrapper bash路径错误 | /bin/bash不存在 | 修改为使用~/usr/local/bin/bash ✅ |
| 6 | libtool使用zsh print命令 | ECHO="print -r --" | 修改libtool为ECHO="printf %s\\n" ✅ |
| 7 | make shell语法错误 | /system/bin/sh不支持bash语法 | 使用SHELL=/.../bash ❌仍有问题 |
| 8 | **新发现：cat -: Permission denied** | 平台限制：cat无法读取stdin | **无法绕过，等待平台更新** ❌ |

## 新发现的平台限制

### E??? - cat -: Permission denied
**问题描述**：
- make过程中出现大量"cat: -: Permission denied"错误
- configure脚本中的某些命令试图使用`cat -`读取stdin，但被拒绝
- 导致.lo文件生成失败（都是0字节）

**影响范围**：
- libtool编译.lo文件时失败
- configure重新运行时也失败（C compiler cannot create executables）
- 这是一个新的平台级限制，之前未发现

**根本原因**：
- 可能是shell环境的安全限制
- 可能是HMDFS文件系统的限制
- 可能是进程权限限制

**尝试过的方案**：
1. 修改libtool的ECHO变量 - 解决了print问题，但仍有cat问题 ❌
2. 使用bash作为SHELL - 仍有cat问题 ❌
3. 重新configure - 失败，因为cat -被拒绝 ❌

## 源码修改记录

### build-aux/config.sub
- 修改1：添加 ohos-linux → linux-ohos 映射
- 修改2：OS 白名单添加 ohos*
- 修改3：kernel-os 白名单添加 linux-ohos*

### build-aux/config.guess
- 添加：aarch64:HarmonyOS:*:* → aarch64-unknown-linux-ohos

### configure
- 修改：umask 077 → umask 022（2处）

### libtool（运行时修改）
- 修改第63行：ECHO="print -r --" → ECHO="printf %s\\n"

## 依赖版本

- nettle: 3.10（已安装）✅
- hogweed: 3.10（已安装）✅
- libxml2: 2.15.3（已安装）✅
- libtasn1: 系统版本✅
- gmp: 系统版本✅

## 验证结果

```bash
# 无法验证（编译失败）
# make成功但.lo文件都是0字节，无法链接
```

## 交付物

- **manifest.yaml**: 已更新，记录失败原因
- **notes.md**: 已更新，包含详细过程
- **patches/**: 3个补丁文件
  - 0001-build-aux-config.guess.patch
  - 0002-build-aux-config.sub.patch
  - 0003-configure.patch（umask修复）

## 注意事项

1. **configure成功是重大进展**：证明了E072和E011方案有效
2. **新平台限制**：cat -: Permission denied需要平台更新解决
3. **替代方案**：可使用OpenSSL替代gnutls的TLS功能

## 知识发现

### E072 修复验证成功 ✅
- config.guess需识别HarmonyOS（不是OHOS）
- config.sub需添加ohos三元组映射（3处修改）
- configure成功证明方案有效

### E011 修复验证成功 ✅
- configure中的umask 077改为022
- 临时文件创建成功

### libtool问题
- libtool脚本使用zsh的print命令
- 需要修改ECHO变量为bash兼容的printf

### 新发现的平台限制
- "cat -: Permission denied"
- 这是在make阶段遇到的新问题
- 需要等待平台更新

---

**编译结束**: 2026-05-30 05:49
**最终状态**: failed（configure成功，make失败）
**阻塞原因**: 新发现的平台限制（cat -: Permission denied）
