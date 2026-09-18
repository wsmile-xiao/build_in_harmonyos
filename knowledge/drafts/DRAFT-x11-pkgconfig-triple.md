# DRAFT-x11-pkgconfig-triple:x11 后端 GUI 库的三件套硬依赖

> Contributor: codex | Status: Draft | Updated: 2026-09-12
> Source: gtk2 2.24.33 HarmonyOS PC 前置适配(archives/g/gtk2/2.24.33)

## 现象

GTK2 系 x11 后端的 configure(GTK_PACKAGES_FOR_X 探测块)在 x11 目标下:

1. 用 `$PKG_CONFIG --exists x11 xext xrender` 探测三件套;
   命中失败时回落 `AC_PATH_XTRA` 原生探测——交叉环境必败。
2. 两处 **无开关的 AC_MSG_ERROR** 硬检查:
   `XShapeCombineMask`(Shape 扩展)与 `XextFindDisplay`(Xext 合理性),
   都指向 **libXext**。
3. 其余扩展 xrandr/xcursor/XFixes/XSync 探测失败**静默降级**。

结论:这类包的成败几乎取决于一个库——libxext——而不取决于关闭了多少
可选 X 特性。

## 本仓现状(2026-09-12,ohpcd 制品仓实测)

| 库 | OHOS 二进制 | 备注 |
|---|---|---|
| libx11/6.4.0 | 有 | 另有 libx11/1.8.13(上游号命名),两套命名并存 |
| libxrender/0.9.12 | 有 | 唯一 pin libx11/1.8.13 的 X 库,需 force 收敛 |
| libxrandr/1.5.5、libxfixes/6.1.0 | 有 | 可选扩展,pin libx11/6.4.0 |
| **libxext/6.4.0** | **无** | 配方在仓且 status: built;`--build=missing` 真机自编;libxfixes/libxrandr 均 pin 此版本 |
| libxcursor | 未适配 | configure 自动降级,不阻塞 |

注意:X11 栈同时存在"上游版本号"(1.8.13)与"SONAME 版本号"(6.4.0)
两套命名,是图冲突的根源;新 x11 依赖包建议与多数派(6.4.0)对齐。

## 方案(建议)

1. 消费方配方显式 `requires` x11+xext+xrender(+GTK2 x11 后端还硬性
   需要 fontconfig),让 PkgConfigDeps 生成 configure 要探测的 .pc。
2. 可选扩展走降级/禁用路径,收敛依赖面。
3. libxext 这类"有配方、无二进制"的依赖:真机 `--build=missing` 自编;
   若自编失败,在 **libxext 自己的 PR** 里修,不得塞进消费方包。
4. 没有任何 configure 开关能在保留 x11 后端的同时绕开 XShape 硬检查;
   不能上 X 栈的库只能换后端(如 GTK3 的 broadway)或源码移植。

## 禁止

- `--without-x` 之类把后端悄悄换掉(下游 gdk-x11 探测会失败);
- 把 libXext 源码/补丁 vendor 进消费方包;
- 在强制依赖从未产出目标二进制时把包标成 built。

## 适用范围

gtk2 及后续一切 x11 目标的 GUI/工具链库移植;与 E348(pc 别名/转发)
互补:E348 解决"探测期缺 .pc",本稿解决"x11 后端的世代性 X 依赖面"。
