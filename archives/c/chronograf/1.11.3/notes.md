# chronograf 1.11.3 适配笔记

## 编译环境
- 构建系统: prebuilt (预编译二进制包)
- 编译日期: 2026-06-05
- 编译器: N/A (预编译)
- 状态: published

## 编译步骤

本次使用 InfluxData 官方提供的预编译 ARM64 二进制包：
1. 从 https://dl.influxdata.com/chronograf/releases/ 下载 chronograf-1.11.3_linux_arm64.tar.gz
2. 解压得到预编译的二进制文件 usr/bin/chronograf 和 usr/bin/chronoctl
3. 对二进制文件进行 ELF 签名（使用 ohc-run.py sign-elf）
4. 打包成 chronograf-1.11.3-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙系统缺少CA证书 | 使用 SSL_CERT_FILE 环境变量指定证书路径 |
| 2 | 二进制无法执行（permission denied） | 需要ELF签名 | 使用 ohc-run.py sign-elf 签名 |
| 3 | 进程被 killed | 首次运行需要安全授权 | 需用户手动授权后再使用 |

## 源码修改

无（使用预编译包）

## 依赖版本

无（静态链接二进制）

## 验证结果

```bash
file /storage/Users/currentUser/usr/local/bin/chronograf
# 输出: ELF executable, 64-bit LSB arm64, static, not stripped

# 注意: 首次运行需要安全弹窗授权
# chronograf --version 可能返回 killed，需用户手动授权
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chronograf-1.11.3-ohos-aarch64.tar.gz | 202 MB | 预编译包（含 chronograf + chronoctl） |

## 注意事项

1. 这是预编译包，不是从源码编译
2. 首次运行时系统会弹出安全授权窗口，用户需要手动确认才能使用
3. 预编译包包含两个二进制：chronograf 和 chronoctl
4. 包内目录结构：usr/bin/, etc/logrotate.d/, var/log/chronograf/
5. 安装时需要将 usr/bin/* 复制到目标系统的 bin 目录