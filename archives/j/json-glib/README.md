# JSON-GLib

## 简介

JSON-GLib 是一个提供 JSON 序列化和反序列化支持的 GLib 库。它允许在 GLib 和 GObject 的数据类型与 JSON 数据类型之间进行转换。

## 官方资源

- **官方网站**: https://wiki.gnome.org/Projects/JsonGlib
- **源码下载**: https://download.gnome.org/sources/json-glib/
- **API文档**: https://gnome.pages.gitlab.gnome.org/json-glib/

## 编译状态

### 1.6.6 (2026-05-22)

**状态**: ✅ 静态库编译成功

**产物**:
- 静态库: libjson-glib-1.0.a
- 头文件: 18个头文件
- pkg-config: json-glib-1.0.pc

**说明**:
- 核心库功能完整，可用于JSON解析和生成
- 工具程序(json-glib-validate/json-glib-format)因依赖缺失未编译
- 使用静态库方式编译，避免动态库权限问题

**依赖**:
- 构建依赖: meson, ninja, pkg-config, glib
- 运行时依赖: glib

## 使用方法

### 编译链接

```bash
# 获取编译参数
pkg-config --cflags json-glib-1.0
pkg-config --libs json-glib-1.0

# 编译示例
gcc myapp.c -o myapp $(pkg-config --cflags --libs json-glib-1.0)
```

### API示例

```c
#include <json-glib/json-glib.h>

// 解析JSON
JsonParser *parser = json_parser_new();
json_parser_load_from_file(parser, "data.json", NULL);
JsonNode *root = json_parser_get_root(parser);

// 生成JSON
JsonBuilder *builder = json_builder_new();
json_builder_begin_object(builder);
json_builder_set_member_name(builder, "name");
json_builder_add_string_value(builder, "value");
json_builder_end_object(builder);
```

## 补丁说明

### 0001-meson-enum-types.patch

修复Meson构建系统在OpenHarmony上的兼容性问题：
- 手动生成enum文件，绕过subprocess权限限制
- 修改meson.build使用预生成文件

## 已知问题

1. **工具程序未编译**: 缺少libintl、libffi、libz等依赖
2. **Meson权限限制**: gnome.mkenums调用glib-mkenums时subprocess权限失败

## 后续工作

- [ ] 编译libintl依赖
- [ ] 编译libffi依赖
- [ ] 完成工具程序编译