# mime-construct

命令行 MIME 消息构造工具，用于构造并通过邮件发送 MIME 格式消息。纯 Perl 实现，设计为被其他程序或脚本调用。

核心功能：
- 构造纯文本/HTML 邮件
- 构造 multipart/mixed 邮件（带附件）
- 构造 multipart/alternative 邮件
- 支持 Base64、Quoted-Printable 编码
- 支持自动 MIME 类型检测（通过 MIME::Types）
- 支持 `--output` 模式输出到 stdout（不发送邮件）

## 运行时依赖

| 依赖 | 说明 |
|------|------|
| MIME::Base64 | MIME Base64 编解码 |
| MIME::QuotedPrint | QP 编码（Perl 核心模块） |
| MIME::Types | 文件扩展名→MIME 类型映射 |
| Proc::WaitStat | 进程状态处理 |

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.11](./1.11/) | built | 2026-06-18 |
