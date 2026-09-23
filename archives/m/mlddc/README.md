# mlddc

Monolith (ml.org) 动态 DNS 服务命令行客户端（1997 年，纯 C）。

## 功能概述

- 通过 HTTP 向 Monolith 动态 DNS 服务（members.ml.org）提交主机名/IP 更新
- 支持激活（act）与停用（deact，命令行参数 `d`/`D`）两种操作
- 基础认证（Basic Auth）发送密码，base64 编码
- 纯 C + POSIX socket（gethostbyname/socket/connect），无外部库依赖

## 构建

- 构建系统：Makefile（上游 CFLAGS 含 x86 专用 flag `-m486`/`-malign-*`，aarch64 clang 不适用）
- 适配方式：直接 clang 编译 `mlddc.c`/`base64.c`/`netio.c`（Conan 配方 build()），
  CFLAGS 追加 `-fgnu89-inline`（netio.h 的 `inline extern Disconnect` 在 C99 下被
  两个 TU 实例化导致 `ld.lld: duplicate symbol: Disconnect`）
- 无 configure、无外部库依赖（非 SECURE 构建）

## OHOS 适配

- 运行验证：无输入时退出码 10（Invalid user data 预期错误路径，验证程序本体可运行）
- 产物：`bin/mlddc`（PIE + NX + FULL RELRO）

## 依赖关系

- 编译依赖：无（非 SECURE 构建）
- 运行依赖：无（仅 POSIX socket）

## 参考资料

- 上游源码：https://github.com/OS2World/APP-INTERNET-mlddc （MLDDC 3.2.0，master）
- 适配笔记：`1.0.1/notes.md`（含 1.0 与 1.0.1 版本差异说明）
