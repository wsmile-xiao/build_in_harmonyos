# polkit

polkit 是 D-Bus 权限认证框架，用于在非特权进程与特权服务之间仲裁授权。本适配以 `-Dlibs-only=true` 仅构建并发布 `libpolkit-gobject-1` 客户端库（跳过 polkitd/backend/agent/programs，适配 OHOS 无系统服务场景）。

**官网**: https://gitlab.freedesktop.org/polkit/polkit

**分类**: system/library

## 版本列表

- 124 (2026-09-03) - built（libpolkit-gobject-1 客户端库）

## 依赖

- glib
- libgobject
- meson >= 0.57
- ninja

## 编译说明

polkit 使用 meson 构建系统。推荐配置选项：

```bash
meson setup build --prefix=$DEFAULT_PREFIX \
  -Dlibs-only=true \
  -Dintrospection=false \
  -Dgtk_doc=false
```

`-Dlibs-only=true` 仅构建 libpolkit-gobject-1 客户端库，满足下游（如 accountsservice）对 `polkit-gobject-1.pc` 的链接需求。
