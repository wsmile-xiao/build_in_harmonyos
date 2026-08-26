# E336-draft: GTK 系 GUI 库 OHOS 无原生显示后端 —— broadway(HTML5) 后端适配模式

> **结构化数据**: [drafts/E336-draft-gtk-broadway-display-backend.kv](E336-draft-gtk-broadway-display-backend.kv)
> **严重度**: 🔴 blocking | **分类**: platform|display|meson|pkg-config|gnome | **自动修复**: ❌ manual
> **实例**: gtk+ 3.24.43（archives/g/gtk/3.24.43）| **可复用**: gtksourceview3 / klavaro / goocanvas 等 GNOME 生态

---

## 错误特征

```
meson:   Neither x11_backend nor wayland_backend nor broadway_backend is true
meson:   Dependency "epoxy" not found / xinerama not found
runtime: Cannot open display / cannot connect to X server / gtk_init failed
pkg-config: No package 'gtk+-3.0' found        （消费方检测失败，同 E321 族）
```

## 根因

OHOS PC 没有 X11/Wayland/Quartz/Win32 任何一种原生显示后端，而 GTK3 的
`meson.build` 强制要求至少启用一个后端——三个开关全 false 时 configuration
直接失败；默认 x11/wayland 后端还连带依赖 epoxy(GL)、xinerama、cloudproviders
等平台组件，在 OHOS 上同样缺失。

伴生问题两类：

1. **构建时工具交叉陷阱**：`glib-mkenums`/`glib-genmarshal` 是构建期 Python
   脚本，交叉编译时必须在 build machine 执行；直接把 host 的 conan 缓存路径
   写死进配方会在其他环境随机失败。
2. **.pc 多文件体系落差**：上游 GNOME 家族是每模块一个 `.pc`
   （gtk+-3.0 / gdk-3.0 / pango…），Conan PkgConfigDeps 只生成配方声明的主
   `.pc`，消费方 `dependency('gtk+-3.0')` 找不到文件（机理同 E321）。

另注意：编译通过 ≠ 可运行。运行期 `gtk_init()` 需要显示服务连接，
GUI 行为属 R40 深度适配边界，须如实标注 partial。

## 受影响范围

所有 GTK/GDK 系 GUI 库与应用在 OHOS PC 的适配：gtk+、gtksourceview3、
klavaro、goocanvas 及其他依赖 GTK3 的 GNOME 生态软件。

## 解决方案（三件套）

### ① meson 选项切 broadway HTML5 后端

broadway 是 GTK 内置的 HTML5 后端（HTTP/WebSocket 输出），不依赖任何原生
显示服务，是 OHOS 上唯一零外部依赖的后端选择：

```ini
-Dx11_backend=false -Dwayland_backend=false -Dbroadway_backend=true
-Dxinerama=no -Dcloudproviders=disabled -Dintrospection=disabled
-Dgtk_doc=false -Ddemos=false -Dexamples=false -Dtests=false
```

### ② glib 构建时工具 native wrapper

在配方 `generate()` 里把 `glib-mkenums`/`glib-genmarshal` 包装为 native
可执行脚本（shebang 指向 build machine 解释器），并注入 pkg-config 变量让
meson 能找到构建时工具。参考实现：
`archives/g/gtk/3.24.43/conanfile.py::_build_python_tool_wrapper`
（gdk-pixbuf 配方有同款先例）。

### ③ 转发型别名 .pc

`PkgConfigDeps.generate()` 之后补写别名 `.pc`：Version 从主 `.pc` 动态继承
（禁止写死），`Requires:` 主 `.pc`，路径/Cflags/Libs 全部由被转发者提供。
参考 `_create_pkg_config_alias`（gdk-pixbuf 同名函数 / pango 配方 --alias-pc），
机理详见 E321。

## 运行期边界（R40）

- 需要 GUI 行为时：设备上启动 `broadwayd` 服务，浏览器访问 HTML5 画布；
- CI/test_package 只断言二进制存在性、ELF magic、NEEDED 依赖与 API 冒烟
  （R34），不断言窗口行为；
- manifest/notes 显式标注 R40 partial，禁止 stub 假装后端存在。

## 禁止策略

| 禁止 | 原因 |
|------|------|
| stub libX11/libwayland 或 LD_PRELOAD 空实现 | 运行期 gtk_init() 仍失败且崩溃点远离根因，R40 审计 fail |
| 写死 host 的 glib-mkenums/genmarshal 路径 | conan 缓存目录随环境漂移，换机必炸 |
| 别名 .pc 写死 Version | 与主 .pc 脱节，版本约束拒绝（E321 forbid_1） |

## 关联条目

- **E318**：GNOME 生态 glib 静态链接 g_libintl_* 符号缺失 + meson host_machine 平台判断
- **E321**：PkgConfigDeps 单 .pc 输出与上游多 .pc 体系的落差（forwarding pc 手法）
