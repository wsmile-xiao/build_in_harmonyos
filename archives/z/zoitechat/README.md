# ZoiteChat

ZoiteChat 是一个基于 GTK3 的 IRC 客户端，源自 HexChat，面向 Windows 与类 UNIX 系统发布。

## 功能概述

- 多服务器 / 多频道窗口，IRC 会话与用户列表管理
- HexChat 兼容的 Python / Perl / Lua 脚本支持
- 可加载插件 API（共享模块形式）
- 多种认证方式（含 SASL）、拼写检查、可定制通知
- GTK3 主题系统与主题导入

## OHOS 适配

| 项 | 说明 |
|----|------|
| 构建系统 | meson（上游 `meson.build`，`c_std=c17`，meson ≥ 0.55） |
| 显示后端 | GTK3 走 broadway（HTML5）后端；OHOS 无 X11/Wayland 原生显示 |
| 工具链 | 原生构建（build = target = OHOS/aarch64），clang 15 + libc++ |
| 依赖 | 全部来自 ohpcd 制品仓预编译包 |

已知约束：

- `data/zoitechat.gresource.xml` 使用 `preprocess="to-pixdata"`，而制品仓 gdk-pixbuf 不带
  `gdk-pixbuf-pixdata` 构建期工具；配方在 configure 后剥除该属性，资源内嵌原始 PNG，
  运行时经标准 GdkPixbuf PNG loader 加载。
- `po/validate-textevent-translations` 需要 `msgmerge`，当前环境未提供该工具，因此该
  测试不在本环境运行；`data/misc` 的 appdata/desktop 校验测试由上游
  `find_program(required: false)` 在工具缺失时自动跳过。
- X11/Wayland 后端在 OHOS 上不可用，`gdk-x11-3.0` / `x11` 检测失败后自动降级。

## 依赖关系

编译依赖（均已在 ohpcd 制品仓发布预编译包）：

- `glib/2.84.0.1`（gio-2.0 / gmodule-2.0 / gobject-2.0 / glib-2.0）
- `gtk/3.24.43`（GTK3，broadway 后端）
- `openssl/3.5.6`（TLS）
- `libcanberra/0.30`（声音提示）
- `libarchive/3.8.7`（DCC 文件传输）
- `lua/5.4.8`、`perl/5.42.2`、`python/3.12.9`（脚本插件）

## 参考资料

- 官网：https://zoitechat.org
- 源码：https://github.com/ZoiteChat/zoitechat
- 文档：https://docs.zoitechat.org
