# dnstap-ldns

## 简介

dnstap-ldns 是 dnstap 项目提供的参考工具，用于解码 dnstap 编码的 DNS 流量文件。
它基于 ldns（DNS 报文解析）、fstrm（Frame Streams 传输）和 protobuf-c 三个库完成解码。

## 功能概述

- `-r <FILE>`：从 Frame Streams 文件读取并解码 dnstap 消息
- `-x`：读取裸 hex 编码的 dnstap protobuf（自动识别纯 hex 或 RFC 3597 格式）
- `-q`：quiet text 输出（每条 dnstap 帧一行，含时间、类型、地址、端口、DNS 问题）
- `-y`：多文档 YAML 输出（含 ldns 解析出的完整 DNS 报文细节）

## OHOS 适配

- 版本 0.2.1 为 CLI 工具，`package_type = application`，产物为 `bin/dnstap-ldns`
- 依赖 ohpcd 已发布的 `ldns/1.9.0`、`libfstrm/0.6.1`、`protobuf-c/1.5.1`
- 构建要点见 `0.2.1/notes.md` 与版本级 `manifest.yaml`

## 依赖关系

- 编译依赖：ldns/1.9.0（openssl/3.5.6）、libfstrm/0.6.1、protobuf-c/1.5.1
- 运行依赖：同一组静态库链接进单个 CLI 可执行文件

## 参考资料

- 上游源码：https://github.com/dnstap/dnstap-ldns
- dnstap 协议：http://dnstap.info/