# libnm

NetworkManager 的 GObject 客户端库（D-Bus API 的封装），可独立于 NetworkManager 守护进程使用。

## 简介

NetworkManager 是 Linux 上主流的网络配置守护进程，其客户端 API 由 **libnm** 提供：一组基于
GObject/GIO 的 C 类型（`NMClient`、`NMDevice`、`NMSetting*` 等），通过 D-Bus 与守护进程通信，
也提供连接配置的解析/校验/序列化（keyfile、GVariant）等不依赖守护进程的纯本地能力。

本包**只打包 libnm 库本身**：`lib/libnm.so*`、`include/libnm/*.h`、`lib/pkgconfig/libnm.pc`。
不含 NetworkManager 守护进程、`nmcli`、`nmtui`、`nm-cloud-setup`、GObject Introspection 与
VAPI 绑定，也不含绝大多数设备插件（wifi/ppp/ofono/modem-manager/ovs/teamdctl 等在本包中关闭）。

## OHOS 适配要点

1. **产物中的三个 `libnm.so*` 都是实体文件。** OHOS 动态加载器不解析符号链接形式的
   `DT_NEEDED`（musl 报 `Error loading shared library libX.so.N: (needed by ...)`，括号内为空，
   进程 exit 127）。打包时对 `lib/` 下的 `.so*` 逐个原地签名
   （`binary-sign-tool sign -inFile X -outFile X -selfSign 1`），该步骤会把 soname 链解引用成实体。
2. **运行时依赖的 soname 必须实体化。** 依赖包（gnutls / libtasn1 / libgcrypt / libgpg-error /
   libidn2 / libpsl）的 libdir 里保存的是符号链接，消费者需要在 `LD_LIBRARY_PATH` 前面放一个
   把所有符号链接复制成实体文件的目录。
3. **头文件包含写法是 `#include <NetworkManager.h>`**，不是 `<libnm/NetworkManager.h>`——
   上游装到 `include/libnm`，`libnm.pc` 的 `Cflags` 已经指向该目录本身。
4. **本仓库内运行时无 D-Bus session bus、且沙箱 seccomp 拦截 `NETLINK_ROUTE`**，因此
   `NMClient` / `NMRemoteSettings` 这类需要总线或内核 netlink 的能力在构建环境的测试中不可用；
   仅使用纯本地 API（版本/连接配置解析校验、GType 等）不受影响。
5. 上游 `meson.build` 默认需要 `mm-glib` 与 `mobile-broadband-provider-info`，本包关闭
   `modem_manager` 以避免引入未发布的依赖。

## 排除与替代

| 上游组件 | 本包状态 | 说明 |
|---|---|---|
| NetworkManager 守护进程 | ❌ 不含 | 本包只出客户端库 |
| `nmcli` / `nmtui` | ❌ 不含 | 命令行工具，独立包 |
| `nm-cloud-setup` | ❌ 不含 | `-Dnm_cloud_setup=false` |
| GObject Introspection / VAPI | ❌ 不含 | `-Dintrospection=false -Dvapi=false` |
| 设备插件（wifi/ppp/ofono/modem-manager/ovs/teamdctl/bluez5_dun/concheck/iwd/wext） | ❌ 不含 | 服务守护进程侧组件 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | 链接 + 头文件传递（`libnm.pc` 只声明 `Requires: gio-2.0`） |
| libudev-zero | 1.0.4 | libnm 目标直接依赖 |
| uuid | 2.40.1 | 经 `link_whole` 的 `libnm_glib_aux` 进入 `libnm.so` |
| gnutls | 3.8.10 | crypto 后端（经 `libnm_crypto` 进入 `libnm.so`） |
| dbus / libndp / libpsl | 1.14.10 / 1.9 / 0.21.5.1 | 仅配置期（`visible=False`） |
| zlib | 1.3.1.1 | glib 与 curl 的版本冲突仲裁（`override=True`，仓库惯例） |

构建工具：`meson/1.11.0`、`pkgconf/3.0.5`（均为 `tool_requires`）。

## 功能验证

```bash
# 版本与连接配置 round-trip（纯本地 API，不需要 D-Bus 总线）
LD_LIBRARY_PATH=<实体化运行时目录>:$LD_LIBRARY_PATH ./test_libnm
# libnm 1.52.1 OK: version=78849 profile round-trip verified
#   (normalize+verify+D-Bus), NMClient GType=NMClient
```

## 参考

- [NetworkManager 官网](https://networkmanager.dev/)
- [源码仓库](https://gitlab.freedesktop.org/NetworkManager/NetworkManager)
- 本版本适配笔记：[1.52.1/notes.md](1.52.1/notes.md)
