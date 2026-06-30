# liblangtag

## 简介

liblangtag 是一个用于处理 BCP 47 语言标签的库，主要用于解析、匹配和处理语言标签。它常用于 LibreOffice 和其他需要处理国际化语言标签的应用程序。

## 功能特性

- 解析 BCP 47 语言标签
- 语言标签匹配和验证
- 支持语言子标签注册表数据
- 支持 Unicode LDML 数据

## 版本信息

- 当前版本: 0.6.4
- 源码地址: https://bitbucket.org/tagoh/liblangtag

## 编译依赖

- libxml2 >= 2.1.0
- glib >= 2.0 (可选，用于 GObject 绑定)

## 安装

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- liblangtag 0.6.4
```

## 使用示例

```c
#include <liblangtag/langtag.h>

lt_tag_t *tag = lt_tag_new();
lt_tag_parse(tag, "zh-Hans-CN", NULL);
// 使用标签...
lt_tag_unref(tag);
```

## 许可证

LGPL v3 或 MPL 1.1
