# libquvi-scripts

## 简介

libquvi-scripts 是 libquvi 的 Lua 脚本集合，用于解析各种视频网站的链接。

## OHOS 适配

### 关键问题

1. **HMDFS 文件系统限制**：configure 在创建临时文件时遇到 HMDFS 限制，需要使用预创建的固定临时目录。

2. **config.guess/config.sub 版本过旧**：2012 版本不支持 HarmonyOS，需要更新到 2022+ 版本。

### 与 Linux 的差异

- Linux：标准 autotools 流程正常工作
- OHOS：需要处理 HMDFS 临时目录限制

## 依赖

无外部依赖（纯 Lua 脚本）。

## 功能验证

```bash
pkg-config --modversion libquvi-scripts-0.9
```

## 参考

- 源码仓库：https://repo.or.cz/libquvi-scripts.git