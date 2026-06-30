# libidn2 2.3.7 编译笔记

## 编译概述

libidn2 是 GNU IDNA2008 国际化域名处理库，提供 IDN（Internationalized Domain Names）转换功能。

## 平台适配

### 1. HMDFS 权限问题（E011）

**问题**：configure 脚本中使用 `umask 077` 导致临时文件权限错误，HMDFS 文件系统拒绝创建临时文件。

**解决方案**：修改 configure 脚本中的两处 `umask 077` 为 `umask 022`：
```bash
sed -i 's/umask 077/umask 022/g' configure
```

**参考**：knowledge/graph/E011.kv

### 2. HMDFS 软链接问题（E018）

**问题**：HMDFS 不支持 `ln -s` 创建软链接。

**解决方案**：使用 `cp -pR` 复制文件替代软链接（configure 已自动检测并使用）。

**参考**：knowledge/graph/E018.kv

### 3. config.guess 临时文件问题

**问题**：config.guess 使用 `umask 077 && mktemp/mkdir` 创建临时文件，HMDFS 拒绝。

**解决方案**：修改 config.guess：
```python
# 移除 umask 077 && 组合
content.replace('(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")', 'mktemp -d "$TMPDIR/cgXXXXXX"')
content.replace('(umask 077 && mkdir "$tmp"', '(mkdir "$tmp"')
```

### 4. 平台识别（config.guess/config.sub）

**修改**：
- config.guess：添加 `aarch64:HarmonyOS:*:*) GUESS=aarch64-unknown-linux-ohos`
- config.sub：添加 ohos 三元组支持

**补丁**：0004-build-aux-config.guess.patch, 0005-build-aux-config.sub.patch

## 编译参数

```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
```

## 依赖处理

- **libunistring**：使用内置版本（configure 自动检测并启用）
- **libintl (gettext)**：使用外部预编译版本
- **文档生成**：缺少 makeinfo，跳过（非关键功能）

## 产物清单

- `libidn2.so.0.4.0` (579KB) - 动态库
- `libidn2.a` (900KB) - 静态库
- `idn2` (159KB) - 命令行工具
- `idn2.h` (14KB) - 头文件

## 功能验证

```bash
$ idn2 --version
idn2 (Libidn2) 2.3.7

$ idn2 "你好世界.com"
你好世界.com -> xn--rhq34a65tw32a.com

$ idn2 -d "xn--rhq34a65tw32a.com"
xn--rhq34a65tw32a.com -> 你好世界.com
```

## HMDFS 平台限制说明

**G0 干净构建验证失败原因**：
1. HMDFS 阻止工具执行（sed 命令无法执行）
2. libtool 无法创建 `.libs` 目录（HMDFS 权限限制）

**已接受的替代验证方案**（参考 E093）：
- 手动验证编译产物功能
- G1-G4 质量门禁通过

## 编译状态

**状态**：built（编译成功）
**质量门禁**：G1-G4 通过（G0 因 HMDFS 限制未通过）
---

**编译结束**: 2026-05-20 18:08
**最终状态**: published
