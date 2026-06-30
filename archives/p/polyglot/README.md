# polyglot

**Protocol adapter to run UCI engines under XBoard**

PolyGlot 是一个象棋引擎协议适配器，用于让 UCI（Universal Chess Interface）引擎在 XBoard/WinBoard 环境下运行。它将 XBoard 协议的消息翻译为 UCI 协议格式，使仅支持 UCI 的引擎能够与 XBoard 界面交互。

## 已编译版本

| 版本 | 状态 | 日期 | 平台 |
|------|------|------|------|
| 2.0.4 | published | 2026-06-10 | OpenHarmony aarch64 |

## 软件信息

- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools
- **依赖**: 无外部依赖（仅需 -lm 数学库）
- **主页**: http://hgm.nubati.net/code/polyglot/

## 主要功能

- XBoard ↔ UCI 协议转换（适配器模式）
- 开局库制作（make-book）
- 开局库合并（merge-book）
- 开局库信息查看（info-book / dump-book）
- EPD 测试（epd-test）
- Perft 测试（perft）

## OpenHarmony 适配说明

### 平台补丁

- **0001-configure.patch**: 修复 HMDFS 文件系统上 autotools configure 脚本中 `umask 077` 创建临时目录权限过严的问题。`umask 077 && mktemp -d` 改为 `mktemp -d`，`umask 077 && mkdir "$tmp"` 改为 `mkdir "$tmp" && chmod 755 "$tmp"`。

### 使用注意事项

- 运行 polyglot 需要配置文件 `polyglot.ini`，指定 UCI 引擎路径和参数
- polyglot 本身不包含测试套件（make check 不可用）