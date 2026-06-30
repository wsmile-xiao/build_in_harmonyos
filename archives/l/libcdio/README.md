# libcdio — 光盘输入与控制库

## 简介

libcdio 是一个用于 CD-ROM 和光盘镜像文件访问的库。应用程序如果希望忽略 CD-ROM 的操作系统和设备依赖属性，或者忽略各种光盘镜像格式的特定细节，可以使用此库获得统一的访问接口。

libcdio 包含以下子库：

- **libcdio** — 便携式 CD-ROM I/O 库（GPL-3.0）
- **libiso9660** — ISO-9660 文件系统库（GPL-3.0）
- **libudf** — UDF 文件系统库（GPL-3.0）
- **libcdio++** — libcdio 的 C++ 包装（GPL-3.0）
- **libiso9660++** — libiso9660 的 C++ 包装（GPL-3.0）

还包含来自 cdparanoia 的 CD-DA 错误/抖动校正库（GPL v2 许可）。

## 命令行工具

| 工具 | 功能 |
|------|------|
| `cd-info` | 显示光盘信息（轨道数、格式等） |
| `cd-read` | 低级别块读取 CD 或光盘镜像 |
| `cd-drive` | 显示驱动器信息 |
| `iso-info` | 显示 ISO-9660 文件系统信息 |
| `iso-read` | 从 ISO-9660 读取文件 |
| `mmc-tool` | MMC 多媒体命令工具 |

## 支持的镜像格式

- ISO-9660（含 Rock Ridge 和 Joliet 扩展）
- CDRWin BIN/CUE
- cdrdao TOC
- Nero NRG
- UDF

## 许可证

GPL-3.0

## 已编译版本

| 版本 | 日期 | 状态 | OHOS 适配补丁 |
|------|------|------|----------------|
| 2.3.0 | 2026-05-28 | built | 3 个（config.guess/config.sub/configure umask） |

## OHOS 适配说明

编译 libcdio 2.3.0 需要 3 个平台适配补丁：

1. **config.guess 补丁** — 让 autotools 识别 HarmonyOS 系统，输出三元组 `aarch64-unknown-linux-ohos`
2. **config.sub 补丁** — 在 OS 白名单中添加 `ohos-linux` 三元组支持
3. **configure 补丁** — 修复 HMDFS 上 `mktemp -d` 配合 `umask 077` 创建的临时目录无法写入文件的问题（`umask 077` → `umask 022`）

**可选功能缺失**（因缺少预编译包，不影响核心功能）：
- CDDB 支持（缺少 libcddb）
- cdda-player（缺少 ncurses）

## 依赖

无外部编译依赖（libcddb 和 ncurses 为可选依赖，缺失时自动禁用对应功能）。