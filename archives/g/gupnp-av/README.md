# gupnp-av

## 简介

GUPnP A/V 是 GNOME 生态的 UPnP A/V 工具库：DIDL-Lite XML 的解析与生成
（MediaServer/MediaRenderer 内容描述格式）、MediaServer 搜索条件
（SearchCriteria）解析、协议信息（ProtocolInfo）处理与 CDS LastChange
事件解析。纯 C，LGPL-2.1-or-later，GObject 风格 API。

注意：虽然名字带 "gupnp"，本库**不依赖** gupnp/gssdp——它是独立的
DIDL-Lite XML 解析库，依赖仅 glib-2.0/gobject-2.0 (>= 2.58) 与
libxml-2.0。下游 gupnp（UPnP 栈本体）消费它，但构建它无需 gupnp。

## OHOS 适配

- 构建系统：meson（`default_library=static`，`introspection=false`，
  `vapi=false`，`gtk_doc=false`，`wrap_mode=nodownload`）
- 依赖：glib2/2.88.0 + libxml2/2.15.3.1（制品仓，R36 已验证）
- 无源码补丁（首轮适配零 patch）
- XSD 运行时寻址：`GUPNP_AV_DATADIR` 需指向包内 `share/gupnp-av/`
  （配方 runenv_info 自动注入，详见 0.14.5/notes.md）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.14.5 | published | 2026-09-03 首轮适配，上游测试 8/8 |
