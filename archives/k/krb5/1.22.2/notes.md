# krb5 1.22.2 编译记录

## 基本信息
- 版本: 1.22.2
- 编译日期: 2026-05-21
- 编译状态: built (核心编译成功，归档流程部分问题)
- 构建系统: autotools

## 遇到的问题和解决方案

### E001: init-build 源码结构识别
- **问题**: krb5 源码在 src 子目录下，init-build 脚本自动识别并提升到 .orig 目录
- **解决**: 脚本自动处理，无需手动干预

### E011: HMDFS 文件系统 umask 问题
- **问题**: configure 脚本中 umask 077 导致临时目录权限拒绝
- **位置**: configure 行 15721, 15726
- **解决**: sed 替换 umask 077 → umask 000
- **补丁**: 0003-configure.patch

### E072: HarmonyOS 平台识别
- **问题**: config.guess/config.sub 不识别 aarch64-unknown-linux-ohos
- **解决**: patch-autotools-ohos.pl 打补丁添加 OHOS 支持
- **补丁**: 0001-config-config.guess.patch, 0002-config-config.sub.patch

### E073: musl libc _res 全局变量缺失
- **问题**: dnsglue.c 中 PRIMARY_DOMAIN 宏使用 _res.defdname，musl libc 不提供 _res
- **位置**: lib/krb5/os/dnsglue.c 行 107-108
- **解决**: 修改 PRIMARY_DOMAIN 宏在 fallback 路径返回 NULL
- **补丁**: 0004-lib-krb5-os-dnsglue.c.patch
- **备注**: musl libc 没有 res_ninit/res_nsearch，只能使用 res_search

### E074: gettext 工具库依赖问题
- **问题**: msgfmt 缺少 libtextstyle.so.0 和 libintl.so.8
- **位置**: po 目录编译
- **解决**: 创建空的 .mo 文件绕过（不影响核心功能）
- **影响**: 翻译文件缺失，但 krb5 核心功能正常

## 编译产物
- 安装路径: /storage/Users/currentUser/test-install-krb5-1.22.2
- 主要二进制: kinit, klist, kadmin, ktutil, krb5-config 等
- 主要库: libgssapi_krb5.so, libk5crypto.so, libkrb5.so, libcom_err.so 等
- pkgconfig: mit-krb5.pc, krb5-gssapi.pc, gssrpc.pc 等

## 质量门禁
- G1 (二进制完整性): ✅ PASS
- G2 (功能可用性): ⚠️ 1 warning
- G3 (可移植性): ✅ PASS
- G4 (档案完整性): ❌ FAIL (缺少 tar.gz)
- G0 (干净构建): ❌ 补丁路径适配问题

## 后续建议
1. 补丁路径需适配 src 子目录结构
2. gettext 依赖需单独编译或从 cmd-pkgs 安装
3. 完成归档打包流程

## 补丁列表
1. 0001-config-config.guess.patch - 添加 __OHOS__ 平台识别
2. 0002-config-config.sub.patch - 添加 ohos-linux triplet 支持
3. 0003-configure.patch - 修复 umask 077 → umask 000
4. 0004-lib-krb5-os-dnsglue.c.patch - musl libc _res 变量适配
