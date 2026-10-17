# mailio

mailio 是一个跨平台 C++ 库，用于 MIME 格式以及 SMTP、POP3、IMAP 协议。
基于 C++17 标准和 Boost 库构建。

## 功能特性

- 递归的 MIME 消息格式化器与解析器
- MIME 消息识别最常见的头部字段（Subject、Recipients、Content-Type 等）
- 消息体编码：Seven bit、Eight bit、Binary、Base64、Quoted Printable
- 头部编码：ASCII、UTF-8、Base64、Quoted Printable
- 头部属性编码：ASCII、Base64、Quoted Printable、Percent
- 识别所有媒体类型，包括嵌套在其他消息中的 MIME 消息
- 可配置的行长度策略和严格解析模式
- SMTP 实现：消息发送，支持明文和 SSL（含 STARTTLS）
- POP3 实现：消息接收和删除、邮箱统计，支持明文和 SSL（含 STARTTLS）
- IMAP 实现：消息接收、删除、搜索、邮箱统计、文件夹管理、消息标志，
  支持明文和 SSL（含 STARTTLS）

## 依赖

- **Boost**（>= 1.81）：`date_time`、`regex` 组件
- **OpenSSL**：`SSL` 组件
- **CMake** >= 3.30
- C++17 编译器

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.26.0 | 已构建 | 首次适配到 HarmonyOS PC（aarch64） |

## 链接

- 仓库地址：https://github.com/karastojko/mailio
- 官方网站：https://www.mailio.dev
- 许可证：BSL-1.0（Boost 软件许可证）
