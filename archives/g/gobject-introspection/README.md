# gobject-introspection

GObject Introspection 是一个用于提供 GObject 库元数据的项目，使得其他语言可以绑定到 GObject 库。

## 版本信息

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|---------|------|
| 1.78.1 | built | 2026-05-26 | Python 扩展模块受限 |

## 平台限制

1. **Python 扩展模块无法加载** - HMDFS + SELinux 安全限制（E107）
2. **introspection 数据生成功能已禁用** - 依赖 Python 扩展模块
3. **运行时需设置 LD_LIBRARY_PATH**

## 功能说明

- `g-ir-compiler`: GIR 编译器 ✅ 可用
- `g-ir-generate`: GIR 生成器 ✅ 可用
- `g-ir-inspect`: GIR 查看器 ✅ 可用
- `g-ir-scanner`: GIR 扫描器 ⚠️ 功能受限

## 依赖

- glib >= 2.88.0
- libffi >= 3.4.6
- meson >= 1.11.1

## 参考

- [GObject Introspection 文档](https://gi.readthedocs.io/)
- [GNOME 项目主页](https://gitlab.gnome.org/GNOME/gobject-introspection)
