# extract-dtb

> Tool to extract device tree blobs from Android kernel images

## 简介

extract-dtb 是一个用于从 Android 内核映像中提取设备树 blob（DTB）的 Python 工具。它可以解析内核映像中的嵌入式 DTB，将其分离为独立的 .dtb 文件，便于嵌入式系统开发和调试。

## OHOS 适配要点

- Pure Python 包，无需编译
- 通过 setuptools 安装
- `extract-dtb --version` 返回 `1.2`
- `extract-dtb --help` 显示正常

## 参考

- [源码仓库](https://github.com/PabloLec/extract-dtb)