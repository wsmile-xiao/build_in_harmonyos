# rkhunter 1.4.6 — OpenHarmony 预编译包

## 简介

Rootkit Hunter（rkhunter）是一款 Unix 系统的 Rootkit 扫描工具，用于检查系统中是否存在 rootkit、后门程序和可疑文件。它通过比对文件哈希值、检查隐藏文件、检测异常端口等方式来发现潜在的安全威胁。

## 版本信息

- **软件版本**: 1.4.6
- **许可证**: GPL-2.0
- **构建系统**: script（纯Shell脚本+Perl程序）
- **目标平台**: OpenHarmony (aarch64)
- **预编译包**: `rkhunter-1.4.6-ohos-aarch64.tar.gz`

## 特性说明

rkhunter 是纯 Shell 脚本 + Perl 程序项目，**没有 C/C++ 代码需要编译**，也没有 ELF 二进制文件。其安装过程通过 `installer.sh` 脚本完成，将脚本文件和数据库文件复制到指定目录。

## 安装说明

### 预编译包部署

1. 解压预编译包到目标目录：
   ```bash
   tar xzf rkhunter-1.4.6-ohos-aarch64.tar.gz -C /usr/local
   ```

2. 验证安装：
   ```bash
   /usr/local/bin/rkhunter --version
   # 应输出: Rootkit Hunter 1.4.6
   ```

3. 以 root 身份运行安全扫描：
   ```bash
   rkhunter --check
   ```

### 注意事项

- `--check` 和 `--config-check` 需要 root 权限
- 运行前请先检查并修改 `/usr/local/etc/rkhunter.conf` 配置文件
- 定期使用 `rkhunter --update` 更新检测数据库

## 依赖

无特殊依赖。需要以下基础组件：
- Shell（sh/bash）
- Perl
- 常用 Unix 工具（grep, sed, awk, find 等）

## 文件清单

| 类别 | 文件 |
|------|------|
| 主程序 | `bin/rkhunter` |
| 配置文件 | `etc/rkhunter.conf` |
| 辅助脚本 | `lib/rkhunter/scripts/check_modules.pl`, `filehashsha.pl`, `stat.pl`, `readlink.sh` |
| 数据库 | `var/lib/rkhunter/db/backdoorports.dat`, `mirrors.dat`, `programs_bad.dat`, `suspscan.dat` |
| ClamAV签名 | `var/lib/rkhunter/db/signatures/RKH_*.ldb`（12个） |
| 多语言支持 | `var/lib/rkhunter/db/i18n/`（en, de, ja, zh, cn, tr 等） |
| 文档 | `share/doc/rkhunter-1.4.6/`（LICENSE, README, FAQ, CHANGELOG） |
| Man页面 | `share/man/man8/rkhunter.8` |

## 编译适配要点

- **构建系统**: `script`（非autotools/cmake）
- **DESTDIR替代**: 使用 `installer.sh --striproot` 选项
- **预创建目录**: 必须预先创建所有安装目录（避免umask导致的Permission denied）
- **无ELF签名**: 纯脚本项目不需要ELF二进制签名

## 源码信息

- **下载URL**: https://downloads.sourceforge.net/project/rkhunter/rkhunter/1.4.6/rkhunter-1.4.6.tar.gz
- **SHA256**: `f750aa3e22f839b637a073647510d7aa3adf7496e21f3c875b7a368c71d37487`
- **压缩格式**: tar.gz