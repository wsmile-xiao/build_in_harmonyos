# libmms

MMS (Microsoft Media Services) 协议库，提供流媒体下载功能。

## 功能
- MMS 协议支持
- MMST 协议支持
- MMSH 协议支持

## 依赖
无外部依赖

## 适配状态
- 版本: 0.6.4
- 状态: published
- 构建系统: autotools
- 补丁: 3 个（config.guess, config.sub, configure umask）

## 关键修复
- HMDFS 权限问题：umask 077 → 022
- HarmonyOS 平台识别
