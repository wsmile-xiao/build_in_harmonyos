# libedataserverui4

Evolution-Data-Server 的 **GTK4 UI 便捷库**（安装产物
`libedataserverui4-1.0.so`，头文件
`include/evolution-data-server/libedataserverui4/`），提供
`ECredentialsPrompter`、`ECellRendererColor`、`ERemindersWidget`、
`ECertificateWidget`、`ETrustPrompt`、`EWebDAVDiscoverWidget`、
`EBufferTagger` 等 Evolution 客户端 UI 组件。

## 源码来源

`libedataserverui4` 没有独立的上游源码包：它是 evolution-data-server 源码树中
`src/libedataserverui` 目录构建出的 CMake target `edataserverui4`。本仓库因此
以官方 evolution-data-server release tarball 作为源码（见 `conandata.yml`），
版本号取上游 evolution-data-server 版本。

`src/libedataserverui` 链接同源码树内的内部库 `camel` / `ecal` /
`edataserver` / `edbus-private`；这些内部库在 ohpcd 未单独发布，所以本配方
构建整棵树并把 UI 库与其依赖的私有共享库一起打包。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.60.2 | built | 首次适配（仅 GTK4 形态） |

## 使用

```python
self.requires("libedataserverui4/3.60.2")
```

```c
#include <libedataserverui4/libedataserverui4.h>
```

pkg-config：`libedataserverui4-1.0`（`Requires:` 传递 gtk4/glib/libsoup3/
libsecret/libxml2/sqlite3/libical-glib/nss/nspr/uuid/icu/zlib）。

## 平台说明

仅支持 OpenHarmony PC aarch64（`settings.os in ("Linux", "OHOS")`）。
WebKitGTK OAuth2、libgweather 天气后端、libcanberra 声音、GTK3 形态在本平台
未提供依赖，全部关闭。详见 `3.60.2/notes.md`。
