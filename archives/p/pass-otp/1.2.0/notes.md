# 编译笔记 - pass-otp 1.2.0

## 基本信息

- **软件名称**: pass-otp
- **版本**: 1.2.0
- **构建系统**: Makefile（纯 shell 脚本，无需编译）
- **编译日期**: 2026-06-02

## 编译过程

### Step 1: 源码获取

使用 git clone 从 GitHub 获取源码（版本 v1.2.0）：
- 仓库: https://github.com/tadfisher/pass-otp
- 方法: `git clone --depth 1 --branch v1.2.0`

### Step 2: 安装

pass-otp 是纯 shell 脚本扩展，无需 configure 和编译步骤。
直接执行：
```bash
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

### Step 3: 验证

质量门禁验证通过：
- G1: 二进制完整性 PASS（无二进制文件）
- G2: 功能可用性 PASS（有 1 个警告）
- G3: 可移植性 PASS
- G4: 档案完整性 PASS

### Step 4: 打包

成功生成预编译包：pass-otp-1.2.0-ohos-aarch64.tar.gz（23KB）

### Step 5: 本地安装

核心文件安装成功：
- `/storage/Users/currentUser/usr/local/lib/password-store/extensions/otp.bash`
- `/storage/Users/currentUser/usr/local/share/man/man1/pass-otp.1`

**注意**: bash completion 文件无法安装到 `/etc/bash_completion.d/`（Read-only file system），用户需手动安装或使用 `PREFIX` 参数。

## 运行时依赖

pass-otp 需要以下运行时组件：
- **必需**: `pass` >= 1.7.0（密码管理器）
- **必需**: `oathtool`（OTP 生成工具，来自 oath-toolkit）
- **可选**: `qrencode`（QR 码生成）

用户在安装 pass-otp 后，需要自行安装这些依赖才能使用。

## 测试情况

由于缺少运行时依赖，无法执行 `make test`。测试报告已记录为 SKIPPED。

## 特殊说明

1. pass-otp 是 pass 密码管理器的扩展，不是独立软件
2. 安装路径遵循 pass 的扩展目录约定：`$PREFIX/lib/password-store/extensions/`
3. 无需 ELF 签名（纯文本脚本）

---
**编译结束**: 2026-06-02 11:19
**最终状态**: built（编译成功，预编译包已生成）
---

**编译结束**: 2026-06-02 11:20
**最终状态**: built
