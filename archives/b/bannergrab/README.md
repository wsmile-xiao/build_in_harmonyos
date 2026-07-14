# bannergrab

## 概述
bannergrab 是一个网络服务 banner 抓取工具，用于执行连接、触发和基本服务信息收集。
它支持 TCP/UDP 协议，内置 30 种服务触发器（HTTP、FTP、SSH、SMTP、MySQL 等），
可以自动识别服务类型并抓取响应 banner。

## 版本
- 3.5 (2008-04-18)

## 来源
- https://github.com/CiscoCXSecurity/bannergrab

## 构建依赖
- OpenSSL 1.1.1w
- clang (鸿蒙平台)

## 构建说明
bannergrab 使用简单 Makefile 构建（非 autotools）。需要修改 Makefile 适配鸿蒙平台：
- 编译器从 gcc 改为 clang
- 添加 -lcrypto 链接选项
- 添加 -fuse-ld 指定 GNU ld 链接器（绕过 lld 的 libxml2 依赖问题）
- 支持 prefix 和 DESTDIR 变量

## 功能
- TCP/UDP banner 抓取
- 30 种内置服务触发器（自动按端口号匹配）
- SSL/TLS 支持
- 连接超时和读取超时配置
- 十六进制输出模式
- 详细输出模式
