# libplist

当前适配版本：2.7.0

## 简介

libplist 是一个用于处理 Apple Property List (plist) 文件的库，支持二进制和 XML 格式的 plist 文件读写。

## OHOS 适配

- **autotools 适配**：需要移除 config.status 中的 `umask 077`（HarmonyOS TMPDIR 权限限制）
- **pkg-config 名称**：使用 `libplist-2.0`（不是 `libplist`）
- **Python bindings**：可通过 `PYTHON=/bin/false PYTHON_NOVERSIONCHECK=yes` 禁用
- **HarmonyOS 专项验证**：覆盖 2.7.0 的 Unix 时间 API，以及 HarmonyOS 临时目录文件读写

## 依赖

无外部依赖，为基础库。

## 功能验证

```bash
pkg-config --modversion libplist-2.0
# 输出: 2.7.0
```

## 参考

- 官网: https://libimobiledevice.org/
- 源码: https://github.com/libimobiledevice/libplist
