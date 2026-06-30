# latex2rtf

LaTeX 到 RTF 格式转换器。

## 简介

latex2rtf 是一个将 LaTeX 文本翻译为 RTF 格式的程序，RTF 格式被多种文字处理器使用，特别是 Microsoft Word。

## 主要功能

- 将 LaTeX 文档转换为 RTF 格式
- 支持多种 LaTeX 命令和环境
- 支持 47 种语言配置文件
- 保留文档的字体、格式和结构信息

## 主页

https://latex2rtf.sourceforge.net/

## 许可证

GPL-2.0-or-later

## 已编译版本

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|----------|----------|
| 2.3.18a | published | makefile | 2026-06-12 |

## 使用说明

```bash
# 将 LaTeX 文件转换为 RTF
latex2rtf input.tex

# 输出文件为 input.rtf
```

注意：latex2rtf 不支持 `--version` 参数，需传入文件名执行。

## 预编译包依赖

仅依赖系统 libc.so（musl libc），无外部库依赖。