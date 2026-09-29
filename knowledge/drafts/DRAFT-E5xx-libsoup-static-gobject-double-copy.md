# DRAFT-E5xx-libsoup-static-gobject-double-copy

## 现象

下游包（libshumate 等 gtk4 共享栈 + libsoup3）的任何 g_test 二进制一启动就
SIGABRT：

```
(process:63531): GLib-GObject-CRITICAL **: cannot register existing type 'gchar'
**
GLib-GObject:ERROR:../gobject/gvaluetypes.c:453:_g_value_types_init: assertion failed: (type == G_TYPE_CHAR)
Bail out! GLib-GObject:ERROR:...
```

编译链接全过，test_package 也可能过（不触发类型注册的路径），上游测试
16/16 全崩。

## 根因

libsoup3/3.6.5-r1（-r2 同）静态链入 glib2：`nm -D libsoup-3.0.so` 导出
**4110 个 g_\* 定义符号**（g_type_register_static 等），NEEDED 无
libglib-2.0.so.0。当图里同时有共享 glib/2.84.0.1.1（gtk4 链 override）时：

- loader 加载共享 libglib-2.0.so.0（第一份 GObject）
- libsoup-3.0.so 的静态 glib 代码也参与全局符号解析（第二份 GObject）
- 两份各自执行 `_g_value_types_init` → gchar 二次注册断言 → SIGABRT

## 修复

requirements 换 `libsoup3/3.6.5-r3`：

```python
self.requires("libsoup3/3.6.5-r3")
self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
```

-r3 链接共享 glib（NEEDED libglib-2.0.so.0，不再导出 g_*），与 gtk4 链
共用同一份共享 glib —— 单 GObject 副本。

验证方法：`nm -D libsoup-3.0.so.0* | grep -cE " T (g_|_g_value)"`
（-r1 = 4110；-r3 = 0）

## 验证

libshumate 1.7.0 本地 conan create RC=0：
- -r1 时：16 上游测试 0/16（全部 gchar SIGABRT）
- -r3 时：16 上游测试 13 项实跑 49 断言全 PASS

## 适用范围

任何 "gtk4 共享栈 + libsoup3" 的混合依赖图（地图/网络类 GTK4 应用）。
全静态图（gupnp 模式）不适用本条——那边靠"自己静态链入 glib2，g_* 保持
UND"实现单副本。
