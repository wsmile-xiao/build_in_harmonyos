# libimobiledevice-glue

## 简介

libimobiledevice-glue 是 libimobiledevice 系列库的公共基础代码库，提供了日志、线程、socket 等通用功能。

## OHOS 适配

- **autotools 适配**：需要移除 config.status 中的 `umask 077`（HarmonyOS TMPDIR 权限限制）
- **中间依赖**：libusbmuxd 2.x 和 libimobiledevice 1.x 都依赖此库

## 依赖

- libplist >= 2.3.0

## 功能验证

```bash
pkg-config --modversion libimobiledevice-glue-1.0
# 输出: 1.3.0
```

## 参考

- 官网: https://libimobiledevice.org/
- 源码: https://github.com/libimobiledevice/libimobiledevice-glue