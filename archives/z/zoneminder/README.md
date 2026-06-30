# zoneminder

ZoneMinder 是开源视频监控和安全摄像头管理系统，支持实时监控、事件录制和分析。

## 功能概述

- 多摄像头管理和监控
- 事件触发录制（运动检测）
- Web 界面管理（PHP）
- 实时流查看和分析
- 支持 RTSP 和 V4L2 摄像头

## OHOS 适配

- **构建系统**: cmake
- **12个补丁**: 平台识别、可选依赖、指针修复、头文件补充等
- **数据库禁用**: ZM_NO_DB 模式（mysqlclient不可用）
- **MQTT/GSOAP/LIBVNC 禁用**: 相关依赖不可用

## 运行依赖

- ffmpeg（视频编解码）
- Web 服务器（PHP界面，OHOS上可能不可用）

## 参考资料

- 源码: https://github.com/ZoneMinder/ZoneMinder
- 版本: 1.38.3
