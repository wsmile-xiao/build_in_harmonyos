# libngf

Sailfish NGF 非图形反馈（Non-graphical feedback）C 客户端库。

## 描述

libngf 是 Nokia / Sailfish OS 非图形反馈框架的 C 客户端库，提供事件播放（`ngf_client_play_event`）与属性表（`NgfProplist`）API，覆盖铃声、时钟、日历、短信、聊天、邮件等事件。0.28 为上游正式 tag。

## 已适配版本

- 0.28（2026-09-19，autotools）

## 依赖

- dbus/1.14.10
- glib/2.88.0
- dbus-glib/0.114
- check/0.15.2（上游 libcheck 测试框架）

## 使用方法

```c
#include <libngf/ngf.h>

NgfProplist *p = ngf_proplist_new();
ngf_proplist_sets(p, "audio", "/usr/share/sounds/beep.wav");
/* NgfClient 需要 D-Bus system bus，仅在有总线守护的设备上创建 */
ngf_proplist_free(p);
```

pkg-config 模块名为 `libngf0`。
