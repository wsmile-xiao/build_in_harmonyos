# glibmm

> GLib 与 GIO 的 C++ 绑定。

## 简介

glibmm 为 GLib 提供类型安全的 C++ 接口，并通过 giomm 提供 GIO 绑定。2.66.x
发布线提供 `glibmm-2.4` 与 `giomm-2.4` 组件。

## OHOS 适配要点

使用 GNOME 官方 release tarball 中的预生成绑定，以 Conan 2 和 Meson 构建。
原生 OHOS 安装 shared 库后对 ELF 重新签名。上游 Meson 测试只在目标程序可执行
的环境运行，HarmonyOS 上需要外部网络的 TLS client 测试单独归入 failing suite。

## 依赖

| 依赖 | 归档版本 | 说明 |
|------|----------|------|
| glib | 2.84.0.1 | GLib、GObject 与 GIO C API |
| libsigc | 2.10.8 | sigc++-2.0 信号与槽 |

## 功能验证

归档包含上游 `meson.test()` 集成和 Conan `test_package` 消费者测试。上游发现
34 项，真实执行并通过 33/33，排除 1 项外部 TLS 网络测试；消费者断言 9/9 通过。

## 参考
