# cmigemo

Migemo 是一个支持日语罗马字增量搜索的工具。C/Migemo 是 Migemo 的 C 语言实现。

- 版本: 20110227
- 许可证: MIT
- 语言: C
- 构建系统: custom（Make_gcc.mak）

## 描述

C/Migemo 提供库 (`libmigemo`) 和命令行工具 (`cmigemo`)，用于日语增量搜索。
它将罗马字输入转换为正则表达式模式，可以匹配多种编码（CP932、EUC-JP、UTF-8）的日文文本。

支持的正则模式:
- Vim 模式 (`-v`): 使用 `\%(` `\)` 分组，`\_s` 跨行匹配
- Emacs 模式 (`-e`): 使用 `\(` `\)` 分组

## 构建注意事项

- 使用自定义构建系统（非标准 autotools），Linux/OHOS 使用 `gcc` 目标
- 需要编码转换工具（qkc/nkf/iconv）用于字典生成
- 需要 curl/wget 下载 SKK 字典源文件
- DESTDIR 支持已通过补丁添加到安装目标
- cmigemo 不支持 `--version`，使用 `-h` 验证

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20110227 | published | 2026-06-12 |
