# NSPR 4.37 + NSS 3.118.1 编译笔记

**开始时间**: 2026-05-25 14:50

## 关键修改：TMPDIR 设置

**问题**：OpenHarmony HMDFS 临时目录权限限制导致 configure 无法创建临时文件。

**解决方案**：设置 TMPDIR=/data/storage/el2/base/cache

这是用户指定的关键解决方案，解决了 OpenHarmony HMDFS 临时目录权限问题。

## NSPR 编译结果

✅ **NSPR 4.37 编译成功**

### 编译步骤
1. 修改 config.status 脚本，添加 TMPDIR 支持
2. 设置环境变量：export TMPDIR=/data/storage/el2/base/cache
3. 运行 configure 并生成 Makefile
4. make -j4 编译
5. make install 安装

### 编译产物
- libnspr4.so (268KB)
- libnspr4.a (424KB)
- libplc4.so (35KB)
- libplc4.a (25KB)
- libplds4.so (26KB)
- libplds4.a (9KB)

### 安装位置
- 库文件：~/usr/local/lib/
- 头文件：~/usr/local/include/nspr/

## NSS 编译进展

### 配置文件创建
✅ 创建了以下配置文件：
1. **HarmonyOS.mk** - 基于 Linux.mk，适配 OpenHarmony
   - 设置 CC=clang, CXX=clang++
   - 设置 AR=llvm-ar, RANLIB=llvm-ranlib
   - 适配 aarch64 架构
   - 添加 -D__OHOS__ 定义

2. **修改 arch.mk** - 添加 HarmonyOS 平台识别
   - OS_ARCH = HarmonyOS
   - OS_RELEASE = 1.12
   - KERNEL = HarmonyOS

3. **修改 config.mk** - 添加 HarmonyOS 到 TARGET_OSES 列表

### 当前问题
⚠️ NSS 编译需要 NSPR 头文件，但路径不完整。

**解决方案**：需要将所有 NSPR 头文件复制到：
- archives/n/nss/nss-3.118.1/dist/public/nspr/
- archives/n/nss/nss-3.118.1/dist/HarmonyOS1.12_aarch64_clang_PTH_64_OPT.OBJ/include/

## 补丁文件

创建了以下补丁：

1. **0001-config-status-use-tmpdir.patch**
   - 修改 config.status 使用 TMPDIR 环境变量
   - 解决 OpenHarmony HMDFS 权限问题

2. **0002-nss-harmonyos-config.patch**
   - 添加 HarmonyOS.mk 配置文件
   - 修改 arch.mk 和 config.mk

## 下一步建议

1. 复制完整的 NSPR 头文件到 NSS dist 目录
2. 重新编译 NSS
3. 验证编译产物
4. 整理归档