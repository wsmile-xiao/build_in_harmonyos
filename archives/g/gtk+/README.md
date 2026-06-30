# GTK+ (GNU 图形工具包)

GTK+ 是一个用于创建图形用户界面的多平台工具包，广泛用于 GNOME 桌面环境。

## 基本信息

- **名称**: GTK+
- **版本**: 3.24.38
- **许可证**: LGPL-2.1
- **官方网站**: https://www.gtk.org/

## HarmonyOS 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 3.24.38 | ✅ published | 2026-05-27 | broadway 后端 |

## 构建配置

- **构建系统**: meson
- **编译器**: clang
- **后端**: broadway (HTML5)
- **禁用**: X11, Wayland (HarmonyOS 无原生图形系统)

## 依赖

编译 GTK+ 需要以下依赖：

- glib-2.0 (2.88.0)
- cairo (1.18.2)
- cairo-gobject (1.18.2)
- pango (1.50.14)
- gdk-pixbuf (2.42.12)
- atk (2.38.0)
- fribidi (1.0.12)
- libepoxy (1.5.10)
- libpng (1.6.43)
- fontconfig (2.16.0)
- freetype (2.14.3)
- harfbuzz (14.2.0)

## 安装

```bash
# 使用预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gtk+ 3.24.38
```

## 使用说明

GTK+ 在 HarmonyOS 上使用 broadway 后端，可以通过 HTML5 在浏览器中显示 GUI。

启动 broadway 服务：
```bash
broadwayd :0
```

然后运行 GTK+ 程序：
```bash
export GDK_BACKEND=broadway
./your-gtk-app
```

访问 http://localhost:8080 查看 GUI。

## 编译笔记

详见 [3.24.38/notes.md](3.24.38/notes.md)。

## 补丁

本版本使用的补丁：
- 无（直接使用 meson 配置）

## 知识沉淀

1. **Meson 平台检测**: HarmonyOS 需要修改 `host_machine.system() == 'linux'` 为包含 `'harmonyos'`
2. **动态库签名**: OpenHarmony 要求共享库必须签名
3. **Broadway 后端**: 可在没有 X11/Wayland 的系统上使用 HTML5 渲染 GUI