# libplist-util

当前适配版本：2.7.0

## 简介

`libplist-util` 提供上游 libplist 的 `plistutil` 命令行工具，用于在 XML、二进制、JSON 和 OpenStep Property List 格式之间转换文件。

## HarmonyOS PC 适配

- 使用 Autotools 构建，并通过 `--build=aarch64-unknown-linux-gnu` 绕过 OHOS 配置识别缺口。
- 禁用 Cython，仅启用 `plistutil` 工具和上游测试。
- 采用静态内部链接，最终 Conan 包只发布 `bin/plistutil`、手册和许可证，不暴露 libplist 库文件。
- HarmonyOS 专项测试覆盖 `/data/local/tmp`（或 `TMPDIR`）中的文件转换和实际工具执行。

## 来源

- 上游项目：https://github.com/libimobiledevice/libplist
- 发布版本：2.7.0
- Conan 引用：`libplist-util/2.7.0`
