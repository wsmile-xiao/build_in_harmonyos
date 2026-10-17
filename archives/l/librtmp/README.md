# librtmp

## 简介

libRTMP 是 rtmpdump 工具集的 RTMP 客户端库,实现 Adobe RTMP 流媒体协议族:
RTMP、RTMPT(HTTP 封装)、RTMPE(加密)、RTMPTE、RTMPS(TLS)与 RTMFP 常量,
提供 URL 解析、AMF 编解码、握手加密(SHA256 HMAC + DH 密钥交换 + RC4)与
流读写等能力。上游源码托管于 git.ffmpeg.org/rtmpdump.git,本归档基于
2019-03-30 master 快照(c5f04a58,上游 VERSION=v2.4)。

## 功能概述

- RTMP/RTMPE/RTMPS/RTMPT 协议连接与流传输(`rtmp.h`)
- RTMP URL 解析与 playpath 提取(`parseurl.c`/`rtmp.h`)
- AMF0 编解码与对象属性操作(`amf.h`)
- SWF 校验哈希计算(SHA256 HMAC + zlib 解压,`hashswf.c`)
- 日志分级控制(`log.h`)

## OHOS 适配

### 适配要点

1. **纯 Makefile 构建**: 上游无 configure,CC/AR/SHARED 由 Conan 以 make
   命令行变量注入,依赖 include/lib 经预留的 XCFLAGS/XLDFLAGS 通道传入。
2. **OpenSSL 1.1+/3.x 兼容补丁**: 上游 2019 快照使用 OpenSSL 1.0 时代的
   HMAC_CTX 栈对象与 DH 结构体直接成员访问,对 OpenSSL 3.x 不可编译;
   补丁按版本宏分支改用 HMAC_CTX_new/free 与 DH_get0_pqg/DH_get0_key/
   DH_set0_pqg/DH_set_length 访问器。
3. **仅库交付**: 不含 rtmpdump/rtmpgw/rtmpsrv/rtmpsuck 命令行工具,
   纯库包无需 commands.json。

### 依赖

- openssl/3.5.6(RTMPE/RTMPS 握手加密与 SWF 哈希)
- zlib/1.3.1(SWF 解压)

### 已知问题

- OpenSSL 3.x 对 RC4/DH 低层 API 有 deprecated 编译警告(上游代码现状,
  不影响功能)。
- 上游无任何测试目标(tests/check 均无),质量验证依赖消费者测试
  (test_package 34 处断言实调公开 API)。

## 版本

| 版本 | 状态 | 说明 |
| --- | --- | --- |
| 2.4_git20190330 | built | master 快照 c5f04a58(2019-03-30) |
