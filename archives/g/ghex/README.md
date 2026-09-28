# ghex

> GNOME Hex Editor — 十六进制编辑器，用于查看和编辑二进制文件

## 基本信息

| 项 | 值 |
|---|---|
| 软件名 | ghex |
| 上游 | https://gitlab.gnome.org/GNOME/ghex |
| 主页 | https://wiki.gnome.org/Apps/Ghex |
| 许可证 | GPL-2.0-or-later |
| 类型 | GNOME 应用（GTK4 + libadwaita） |
| 构建系统 | Meson |

## 已适配版本

| 版本 | 状态 | 适配日期 | 说明 |
|------|------|---------|------|
| 46.0 | built | 2026-09-23 | 首次适配，依赖 glib/gtk4/libadwaita |

## 依赖

- glib/2.84.0.1
- gtk4/4.22.4
- libadwaita/1.2.0
- xz/5.6.2（显式，补 gtk4 未声明的 liblzma）

## 已知限制

- GTK4 图形应用，HMDFS/SELinux 下缓存二进制无法直接执行
- test_package 采用文件检查方式验证安装完整性

## 相关文档

- [notes.md](46.0/notes.md) — 适配笔记（含关键坑与解法）
- [test-report.md](46.0/reports/test-report.md) — 测试报告
- [conan-verify-report.md](46.0/reports/conan-verify-report.md) — 8 道门禁报告
