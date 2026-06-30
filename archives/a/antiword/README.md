# antiword

MS Word 文档转文本转换器

## 简介

Antiword 是一个免费的 MS-Word 阅读器，支持 Linux、RISC OS 和 DOS。它将 MS-Word 文档转换为纯文本或 PostScript 格式。

## 功能特性

- 将 MS-Word 文件 (.doc) 转换为纯文本
- 支持 PostScript 输出
- 支持 PDF 输出
- 支持 XML 输出 (DocBook)
- 包含多种字符映射文件

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- antiword 0.37
```

## 使用方法

```bash
antiword document.doc              # 输出纯文本
antiword -p a4 document.doc        # PostScript 输出
antiword -a a4 document.doc        # PDF 输出
antiword -x db document.doc        # XML (DocBook) 输出
```

## 版本信息

- 版本: 0.37 (2005年10月21日)

## 许可证

GNU General Public License (GPL)
