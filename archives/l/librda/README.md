# librda

## 简介

librda（Remote Desktop Awareness）是一个用于检测和识别远程桌面会话的库，主要用于 Arctica 项目。

## OHOS 适配

### 关键问题

1. **introspection.m4 缺失**：需要创建 minimal 版本禁用 GObject introspection。

2. **XML::Parser 缺失**：需要禁用 intltool/gettext 配置。

3. **alloca 宏重定义**：需要移除 -Werror 或添加 undef alloca。

4. **GTK3 测试依赖**：需要使用 --disable-tests 禁用。

### 与 Linux 的差异

- Linux：完整 introspection/gettext 支持
- OHOS：需要禁用多项功能

## 依赖

- glib-2.0

## 功能验证

```bash
rdacheck
pkg-config --modversion rda
```

## 参考

- 源码仓库：https://cgit.arctica-project.org/librda/