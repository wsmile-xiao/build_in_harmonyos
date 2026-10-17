# boot-info-script

**Inspect boot environment and generate a boot info report**

## 简介

boot-info-script 是 Boot-Repair 生态的诊断脚本工具，用于收集系统启动环境
信息（bootloader、分区表、内核模块、GRUB 配置等）并生成一份可分享的报告，
帮助排查无法自行解决的启动问题。

## 特性

- 🐚 纯 bash 脚本实现，无需编译
- 📋 生成启动环境诊断报告（RESULTS.txt）
- 🔍 检测 GRUB / Syslinux / EFI / MBR 等启动链
- 🖥️ 支持 `--stdout` 直接输出报告内容

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 0.78 | built | none (bash) | 2026-09-07 |

## 安装

```bash
# 从预编译包安装（注：该命令在制品仓发布（status=published）后生效）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- boot-info-script 0.78

# 验证安装
bootinfoscript --version
```

## 使用示例

```bash
# 输出版本信息
bootinfoscript --version

# 查看帮助
bootinfoscript --help

# 生成启动环境报告（需要 root 权限及 fdisk 等系统工具）
bootinfoscript RESULTS.txt
```

## 注意

- 脚本运行时依赖系统工具（fdisk、filefrag 等），缺失时会提示安装
- 完整报告生成需要 root 权限；`--version`/`--help` 无需 root
