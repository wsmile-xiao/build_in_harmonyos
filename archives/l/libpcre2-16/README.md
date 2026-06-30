# libpcre2-16

## 简介

PCRE2 是 PCRE 的下一代版本，提供更强大的正则表达式功能。libpcre2-16 是 PCRE2 的 16 位字符版本，支持 UTF-16 编码。

## 功能概述

- 更强大的 Perl 风格正则表达式
- 16 位字符支持（UTF-16）
- 8 位字符支持（UTF-8）
- POSIX 兼容接口
- 提供 pcre2grep 和 pcre2test 工具
- 支持更长的模式和更复杂的表达式

## OHOS 适配要点

1. **旧版 config.guess**：PCRE2 使用旧版 GNU config.guess，需要使用 `echo/exit` 格式而非 `GUESS=` 格式
2. **config.sub**：需要手动添加 `| linux-ohos*` 到 kernel-os case block
3. **HMDFS 限制**：config.status 的临时目录创建受限，使用固定目录 `./confwork` 替代

## 依赖关系

- **编译依赖**：无外部依赖
- **运行依赖**：无外部依赖

## 参考资料

- 官网：https://www.pcre.org
- 源码：https://github.com/PCRE2Project/pcre2