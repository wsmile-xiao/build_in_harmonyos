# perl-protocol-irc

IRC 协议处理 Perl 模块 (Protocol::IRC)

## 版本

- 0.13 (published)

## 描述

Protocol::IRC 是一个纯 Perl 的 IRC 协议处理模块，提供 IRC 消息解析、构造、
分发和客户端协议处理功能。包含三个主要模块：

- **Protocol::IRC** — IRC 协议基础混入类，提供消息读取、分发和发送
- **Protocol::IRC::Message** — IRC 消息封装，支持 IRCv3 标签
- **Protocol::IRC::Client** — 面向客户端的 IRC 协议扩展

## 构建系统

- ExtUtils::MakeMaker (Makefile.PL)
- 原始源码使用 Module::Build，平台不支持，自动创建 Makefile.PL 后备

## 依赖

- perl 5.14+
- Scalar::Util (核心模块)

## 许可证

perl_5 (Artistic License 或 GPL)
