# DRAFT-PLAYERCTL-2.4.1-GLIB-HEADERS-CPP-INFO-LAYOUT: glib 公开头布局与消费者 -I 补齐

- **草稿 ID**: DRAFT-PLAYERCTL-2.4.1-GLIB-HEADERS-CPP-INFO-LAYOUT
- **严重度**: 2
- **类别**: conan, glib, consumer, include-path
- **来源**: playerctl 2.4.1 适配（HarmonyOS PC aarch64）

## 错误特征

```
test_playerctl.c:1:10: fatal error: 'glib.h' file not found
```

## 根因分析

glib 公开头布局沿袭其自身 `.pc` 的 Cflags：

- `glib/gobject/gio` 头 → `<prefix>/include/glib-2.0`
- 平台生成的 `glibconfig.h` → `<prefix>/lib/glib-2.0/include`
- `gio-unix` 头 → `<prefix>/include/gio-unix-2.0`

conan 组件化 glib 包把这些目录挂在各 component 的 cpp_info 上，根 `cpp_info.includedirs`
不暴露；消费者只用根 cpp_info 时找不到 `glib.h`/`glibconfig.h`。

## 推荐方案

**方法**: cpp-info-union-with-glib-layout

test_package 生成 `-I` 时取「依赖 cpp_info 通用路径 ∪ glib 布局兜底」并集。多余 `-I`
无副作用，缺一个即编译失败。

## 禁止事项

- 修改 glib 包自身的 cpp_info（依赖文件属主编权限）
- 只加 `include/glib-2.0` 不加 `lib/glib-2.0/include`（glibconfig.h 在 lib 侧）
