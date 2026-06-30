# colortail

Like tail(1), but with various colors for specified output. colortail 是一个类似于 tail 命令的工具，但它可以为指定的输出添加颜色，使得在日志文件中更容易区分错误、警告和信息等不同类型的消息。

## 版本
- 0.3.5

## 许可证
- GPL-2.0-or-later

## 描述
colortail 可以读取配置文件（如 conf.kernel, conf.messages 等），根据文件内容的正则表达式匹配，为不同类型的行添加 ANSI 颜色。 典型用途是为 syslog、kernel log、邮件日志等添加颜色高亮。

## 主要功能
- 显示文件的最后 N 行（默认 10 行）
- 支持多文件同时显示（带文件头标识）
- 支持颜色配置文件（通过正则表达式匹配）
- 支持 -f（follow）模式，持续追踪文件增长
- 支持 stdin 读取（用 `-` 作为文件名）
- 支持 -q（quiet）模式（无文件头）

## OpenHarmony 编译状态
- 状态: published
- 编译日期: 2026-06-11
- 构建系统: autotools
- 编译器: clang/clang++
- 平台: HarmonyOS 1.12.0 (aarch64)

## 依赖
无外部依赖（仅使用标准 C 库和 POSIX regex）

## 已知问题
- HMDFS 文件系统上 autotools 的 config.status 创建临时目录需要移除 `umask 077`（平台级 L1 问题）