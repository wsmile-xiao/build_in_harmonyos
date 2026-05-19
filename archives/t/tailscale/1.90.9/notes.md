# Tailscale 1.90.9 适配笔记

## 编译环境
- 构建系统: prebuilt（预编译包）
- 编译日期: 2026-05-18
- 编译器: N/A（预编译）
- 状态: published

## 编译步骤

本版本为官方预编译包，无需从源码编译：

1. 下载预编译包：
   ```bash
   wget https://pkgs.tailscale.com/stable/tailscale_1.90.9_arm64.tgz -O tailscale.tgz
   ```

2. 解压：
   ```bash
   tar xzf tailscale.tgz
   ```

3. ELF 签名（鸿蒙系统必需）：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf tailscale_1.90.9_arm64/tailscale
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf tailscale_1.90.9_arm64/tailscaled
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 二进制无法执行 | 鸿蒙系统需要 ELF 签名 | 使用 ohc-run.py sign-elf 进行签名 |

## 源码修改

无源码修改（预编译包）

## 依赖版本

无编译依赖（预编译包）

## 验证结果

```bash
$ ./tailscale version
1.90.9
  tailscale commit: 6e8a4f2de795ae6801f4b599e3f64ca6b5465c01
  long version: 1.90.9-t6e8a4f2de-g19196f361
  other commit: 19196f3617f75c3898c4fdfd4e82dcf9d258a04b
  go version: go1.25.3

$ ./tailscaled --version
1.90.9
  tailscale commit: 6e8a4f2de795ae6801f4b599e3f64ca6b5465c01
  long version: 1.90.9-t6e8a4f2de-g19196f361
  other commit: 19196f3617f75c3898c4fdfd4e82dcf9d258a04b
  go version: go1.25.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tailscale | 24M | 主命令行工具 |
| tailscaled | 35M | 守护进程服务 |

## 注意事项

- 预编译包为 ARM64 架构，适用于鸿蒙系统
- 必须进行 ELF 签名才能执行
- tailscaled 守护进程可能需要额外权限配置