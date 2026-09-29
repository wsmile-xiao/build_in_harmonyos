# loudmouth

[loudmouth](https://mcabber.com) 是一个轻量、易用的 C 语言 Jabber/XMPP 协议异步
客户端库，构建在 GLib 之上。用于连接 XMPP 服务器、收发消息与 presence、
解析 XML stanza。本项目采用社区维护中的 MCabber fork
（`https://github.com/mcabber/loudmouth`），版本 1.5.4。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.5.4 | built | HarmonyOS PC (aarch64) 基础适配（路径 A） |

## 构建

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=~/.conan2/profiles/ohos-aarch64 \
  -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```

产物：`lib/libloudmouth-1.a`，头文件位于 `include/loudmouth-1.0/loudmouth/`，
pkg-config 文件 `lib/pkgconfig/loudmouth-1.0.pc`（Conan 的 `pkg_config_name`
为 `loudmouth-1`，仅用于依赖侧生成的消费者 .pc，不重命名包内已安装文件）。

## 依赖

- glib/2.84.0.1（REQUIRED，glib-2.0 + gobject-2.0）
- SSL（可选，本适配关闭 `--with-ssl=no`）、libidn、libasyncns（可选，均关闭）

## 适配说明

见 [1.5.4/notes.md](1.5.4/notes.md)。上游 GLib 测试套件共 4 个 g_test 用例
（test-parser 2 + test-data-objects 2），随 conan create 在 HarmonyOS aarch64
环境真实执行。
