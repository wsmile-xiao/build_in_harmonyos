# libcdio-tools

## 简介

libcdio-tools 提供 libcdio 2.3.0 的六个命令行工具：

- `cd-drive`：枚举 CD-ROM 驱动能力
- `cd-info`：分析光盘、CUE/BIN 和 TOC 镜像
- `cd-read`：读取 CD 扇区
- `iso-info`：查看 ISO-9660 文件系统
- `iso-read`：从 ISO-9660 镜像提取文件
- `mmc-tool`：执行 MMC 命令

本包只打包命令行工具，依赖已适配的 `libcdio/2.3.0`，不重复打包 libcdio 库文件。

## 版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 2.3.0 | verified | autotools + direct clang |

## OHOS 适配说明

- 复用 `libcdio/2.3.0` 的 OHOS aarch64 静态库。
- 补齐 `config.guess` 和 `config.sub` 的 HarmonyOS 平台识别。
- 修正 HMDFS 上 `configure` 临时目录权限导致的写入失败。
- 打包阶段使用 HarmonyOS `binary-sign-tool` 对工具 ELF 签名。

## 验证

OpenDesk HarmonyOS aarch64 真机任务 `20260924-154132-7dfcec-libcdio-tools-2.3.0-v4`：

- `CREATE_EXIT=0`
- 六个工具均执行 `--version`
- `cd-drive` 驱动枚举、`cd-info` CUE 分析、`cd-read` MODE1 读取、
  `iso-info` ISO-9660 列表和 `iso-read` 文件提取均与上游 2.3.0
  固定数据输出一致
- 共 12 条消费端断言通过

需要真实 MMC 光驱的操作未验证，本包不对此作通过声明。
