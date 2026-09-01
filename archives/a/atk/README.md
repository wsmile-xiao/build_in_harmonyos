# ATK (Accessibility Toolkit)

ATK 是 GNOME 无障碍工具包，为辅助技术（如屏幕阅读器）提供标准接口。

## 基本信息

- **名称**: ATK
- **版本**: 2.38.0
- **许可证**: LGPL-2.1
- **官方网站**: https://wiki.gnome.org/Accessibility

## HarmonyOS 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.38.0 | ✅ published | 2026-05-26 | meson 构建 |
| 2.38.0.1 | ✅ published | 2026-08-05 | meson 构建 + harmonyos 链接器标志补丁，5/5 上游测试通过 |
| 2.38.0.1.1 | ✅ published | 2026-08-22 | R37 递增 |

## 构建配置

- **构建系统**: meson
- **编译器**: clang
- **配置选项**: `--wrap-mode=nofallback -Dintrospection=false`

## 依赖

- glib-2.0 (2.88.0)
- gobject-2.0 (2.88.0)
- libintl

## 安装

```bash
# 使用预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- atk 2.38.0
```

## 编译笔记

详见 [2.38.0/notes.md](2.38.0/notes.md)。

## 补丁

本版本使用的补丁：
- `0001-atk-intl-wrapper.c.patch` - 解决 g_libintl_* 符号问题
- `0002-atk-meson.build.patch` - atk meson.build 修改
- `0003-meson.build.patch` - E090 平台检测问题

## 知识沉淀

1. **E090**: Meson `host_system == 'linux'` 不匹配 HarmonyOS
2. **g_libintl_* 符号问题**: glib 静态库与 libintl 符号不匹配，需要 intl-wrapper.c

## 注意事项

1. 必须设置 `PKG_CONFIG_PATH` 包含 `~/usr/local/lib/pkgconfig`
2. 必须禁用 introspection（g-ir-scanner 的 Python 扩展需要 ELF 签名）
3. g_libintl_* 符号问题需要 wrapper 库解决