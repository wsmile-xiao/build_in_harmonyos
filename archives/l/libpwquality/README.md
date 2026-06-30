# libpwquality

## 简介

libpwquality 是一个密码质量检查和生成库，提供密码强度评估和随机密码生成功能。

## OHOS 适配

### 关键问题

1. **PAM 支持缺失**：鸿蒙系统缺少完整的 PAM（Pluggable Authentication Modules）支持，部分功能受限。

2. **cracklib 依赖**：默认需要 cracklib 库，鸿蒙系统无预编译包，需要使用 `--disable-cracklib-check` 禁用。

3. **HMDFS 限制**：config.status 在创建临时文件时遇到 HMDFS 文件系统限制，需要使用预创建的固定临时目录。

### 编译选项

```bash
./configure --prefix=$DEFAULT_PREFIX --disable-cracklib-check
```

### 与 Linux 的差异

- Linux：完整 PAM 支持，cracklib 可用
- OHOS：无 PAM，需要禁用 cracklib

## 依赖

- 无必需依赖（禁用 cracklib 后）

## 功能验证

```bash
# 检查库是否安装
ls ~/usr/local/lib/libpwquality.so

# 检查头文件
ls ~/usr/local/include/pwquality.h

# pkg-config 验证
pkg-config --modversion pwquality
```

## 参考

- 源码仓库：https://github.com/libpwquality/libpwquality