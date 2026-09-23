# bluefish

Bluefish 是一个面向有经验的网页设计师与程序员的 GTK3 编辑器（C，GPL-3.0），
支持 HTML/CSS/PHP/JS/Python/C 等语法高亮、Zen Coding、多文档、搜索替换、
代码片段与外部工具集成。

## OHOS 适配

- 使用官方发行 tarball 自带 autotools 产物直接构建（无需 autoreconf）。
- **GTK 决策**：2.2.16 的 configure 默认探测 `gtk+-3.0 >= 3.2.2`（GTK3 主路径），
  GTK2 仅在显式 `--with-gtk2` 或 GTK3 缺失时回退——制品仓已有 GTK3 依赖链
  （gtk/3.24.43 等），无需 GTK2 包。
- 依赖全部来自制品仓：gtk/glib/pango/gdk-pixbuf 链 + libxml2。
- 裁剪不可用的桌面集成/可选件：nls、拼写（enchant）、python、
  freedesktop menu/mime/appdata、主题图标。
- HarmonyOS PC 无 X server，GUI 无法运行级验证：
  - 交付完整编译/链接产物（bin/bluefish + share 数据），ELF 自签名；
  - 构建期图标嵌入依赖 gdk-pixbuf-csource（Conan 包内未签名 ELF），
    复制 + 自签名后通过 `GDK_PIXBUF_CSOURCE` 注入 Makefile；
  - 新增无头 `--selftest`（14 项生产代码检查）供 CI 自动化验证；
  - `--version`/`--help` 与 plain 启动的 fail-closed 路径均可无头断言。
- 4 个补丁：config.guess/config.sub（OHOS 三元组）、configure（HMDFS
  umask）、bluefish.c（无头 selftest）。

## 依赖

- gtk/3.24.43、glib/2.84.0.1、pango/1.50.14.1.1、gdk-pixbuf/2.44.6.1、
  libxml2/2.15.3.1

## 参考

- 官方站: https://bluefish.openoffice.nl/
- 源码镜像: https://www.bennewitz.com/bluefish/stable/source/
