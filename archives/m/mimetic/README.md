# mimetic

mimetic 是一个用 C++ 编写的免费 MIME（电子邮件）库，提供 RFC822/MIME 消息的
构建、解析、序列化以及 Base64、Quoted-Printable 等编解码能力。上游版本 0.9.6
起采用 MIT 许可证。

## 功能特性

- MIME 消息的递归解析与构建（`MimeEntity`、`Header`、`Body`、多部分实体列表）
- RFC822 头部字段：From/To/Subject/Date/Message-ID、地址与地址组列表
- 内容类型、内容描述、内容处置及其参数解析
- 传输编码：Base64、Quoted-Printable、7bit/8bit/binary
- 编解码器可链式组合（codec chain）
- 内存映射文件与普通文件两种输入路径
- 附带 examples/（mm、structure、b64、qp 等示例程序，默认不构建）

## 上游信息

- 官网/下载：https://www.codesink.org/mimetic_mime_library.html
- 许可证：MIT
- 构建系统：autotools（configure + make）

## OHOS 适配要点

- 上游 `config.sub`（2007 版）不含 `aarch64` 与 `linux-ohos`，需补丁后再以
  `--build/--host=aarch64-linux-ohos` 显式配置。
- `configure` 中的 `umask 077` 在 HMDFS 上会创建不可写临时目录（E011），需改为 022。
- aarch64 上 `char` 为无符号：Base64 解码表的 `-1` 哨兵必须显式声明为 `signed char`。
- 现代 clang 的 C++17 模式要求：移除 `register`、避免指针与 0 的有序比较、
  字面量与宏名之间留空格。
- 上游测试挂在 `make`（`test/all-local`）而不是 `make check` 上，构建期自动执行。

## 版本索引

见 [manifest.yaml](manifest.yaml)。
