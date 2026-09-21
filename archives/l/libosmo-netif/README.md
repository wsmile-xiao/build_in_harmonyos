# libosmo-netif

## 简介

libosmo-netif 是 Osmocom 项目族的网络接口库，提供流式客户端/服务端
（osmo_stream_cli/srv，TCP 与可选 SCTP）、IPA、Osmux、抖动缓冲、RTP、
RS232 与数据报传输接口，是 libosmo-sigtran 等上层信令库的直接依赖。

## 主要功能

- osmo_stream_cli / osmo_stream_srv_link 流式传输（TCP；SCTP 需平台支持）
- IPA（IP Access）协议辅助
- Osmux（语音复用）与抖动缓冲
- RTP / RS232 / 数据报接口

## 版本信息

- 当前编译版本：1.6.0
- 许可证：GPL-2.0-or-later

## 依赖

- libosmocore/1.11.0（含 osmocore/osmogsm/osmovty/osmocodec）

## 编译选项

- `--disable-libsctp`：平台无 SCTP（内核 EPROTONOSUPPORT）
- `--disable-doxygen`：无 doxygen 工具

## 归档版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.6.0 | built | 2026-09-19 |

## 相关链接

- 源码：https://osmocom.org/projects/libosmo-netif
