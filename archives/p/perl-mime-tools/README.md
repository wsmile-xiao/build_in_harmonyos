# perl-mime-tools (MIME::Tools)

MIME-tools 是一组功能强大的 Perl 模块，用于创建、解析和操作 MIME 格式的邮件消息。

## 主要组件

| 模块 | 功能 |
|------|------|
| MIME::Tools | 主模块，版本信息和工具函数 |
| MIME::Parser | 解析 MIME 邮件消息，提取部件和附件 |
| MIME::Entity | 表示邮件实体（整体或部分），支持构建和序列化 |
| MIME::Head | 邮件头操作（From/To/Subject/Content-Type 等） |
| MIME::Body | 邮件正文存储（内存或文件） |
| MIME::Decoder | 编码转换（Base64、QuotedPrint、BinHex 等） |
| MIME::Words | RFC 2047 编码/解码头字段中的非 ASCII 文本 |
| MIME::WordDecoder | 解码 MIME 编码的词 |

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 5.515 | 2026-06-17 | built | 支持 OpenHarmony (aarch64) |

## 运行时依赖

- Mail::Header >= 1.01
- Mail::Internet >= 1.0203
- Mail::Field >= 1.05
- MIME::Base64 >= 2.20
- IO::File >= 1.13
- File::Spec >= 0.6
- File::Path >= 1
- File::Temp >= 0.18

## OpenHarmony 适配说明

此模块为纯 Perl 实现，不包含 XS/C 代码，在 OpenHarmony 平台上运行无需特殊权限。
所有功能测试（15 项）通过，包括 MIME 邮件创建、解析、序列化、Base64/QuotedPrint 编解码等。
