# libnm

NetworkManager 的 GObject 客户端库（封装 D-Bus API），可独立于 NetworkManager 守护进程使用：
网络状态查询、连接配置的解析/校验/序列化（keyfile、GVariant）等，也提供不依赖守护进程的
纯本地能力。本目录按版本交付，各版本的裁剪面与依赖差异见下表的版本级适配笔记。

本包**只打包客户端库本身**：`lib/libnm.so*`、`include/libnm/*.h`、`lib/pkgconfig/libnm.pc`；
不含 NetworkManager 守护进程、`nmcli`、`nmtui`、`nm-cloud-setup`、GObject Introspection / VAPI
绑定，也不含绝大多数设备插件（各版本裁剪的 meson 开关不同，见对应版本目录的 `notes.md`）。

## Versions

| 版本 | 说明 | 适配笔记 |
|---|---|---|
| `1.52.1` | 客户端库适配（crypto 走 gnutls 系） | [1.52.1/notes.md](1.52.1/notes.md) |
| `1.58.0` | 客户端库适配（`crypto=null`，不引入 gnutls/nss） | [1.58.0/notes.md](1.58.0/notes.md) |

## 1.52.1 版本说明（既有）

NetworkManager 的 GObject 客户端库（D-Bus API 的封装），可独立于 NetworkManager 守护进程使用。

### 简介

NetworkManager 是 Linux 上主流的网络配置守护进程，其客户端 API 由 **libnm** 提供：一组基于
GObject/GIO 的 C 类型（`NMClient`、`NMDevice`、`NMSetting*` 等），通过 D-Bus 与守护进程通信，
也提供连接配置的解析/校验/序列化（keyfile、GVariant）等不依赖守护进程的纯本地能力。

本包**只打包 libnm 库本身**：`lib/libnm.so*`、`include/libnm/*.h`、`lib/pkgconfig/libnm.pc`。
不含 NetworkManager 守护进程、`nmcli`、`nmtui`、`nm-cloud-setup`、GObject Introspection 与
VAPI 绑定，也不含绝大多数设备插件（wifi/ppp/ofono/modem-manager/ovs/teamdctl 等在本包中关闭）。

### OHOS 适配要点

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

### 排除与替代

| 上游组件 | 本包状态 | 说明 |
|---|---|---|
| NetworkManager 守护进程 | ❌ 不含 | 本包只出客户端库 |
| `nmcli` / `nmtui` | ❌ 不含 | 命令行工具，独立包 |
| `nm-cloud-setup` | ❌ 不含 | `-Dnm_cloud_setup=false` |
| GObject Introspection / VAPI | ❌ 不含 | `-Dintrospection=false -Dvapi=false` |
| 设备插件（wifi/ppp/ofono/modem-manager/ovs/teamdctl/bluez5_dun/concheck/iwd/wext） | ❌ 不含 | 服务守护进程侧组件 |

### 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | 链接 + 头文件传递（`libnm.pc` 只声明 `Requires: gio-2.0`） |
| libudev-zero | 1.0.4 | libnm 目标直接依赖 |
| uuid | 2.40.1 | 经 `link_whole` 的 `libnm_glib_aux` 进入 `libnm.so` |
| gnutls | 3.8.10 | crypto 后端（经 `libnm_crypto` 进入 `libnm.so`） |
| dbus / libndp / libpsl | 1.14.10 / 1.9 / 0.21.5.1 | 仅配置期（`visible=False`） |
| zlib | 1.3.1.1 | glib 与 curl 的版本冲突仲裁（`override=True`，仓库惯例） |

构建工具：`meson/1.11.0`、`pkgconf/3.0.5`（均为 `tool_requires`）。

### 功能验证

```bash
# 版本与连接配置 round-trip（纯本地 API，不需要 D-Bus 总线）
LD_LIBRARY_PATH=<实体化运行时目录>:$LD_LIBRARY_PATH ./test_libnm
# libnm 1.52.1 OK: version=78849 profile round-trip verified
#   (normalize+verify+D-Bus), NMClient GType=NMClient
```

### 参考

- [NetworkManager 官网](https://networkmanager.dev/)
- [源码仓库](https://gitlab.freedesktop.org/NetworkManager/NetworkManager)
- 本版本适配笔记：[1.52.1/notes.md](1.52.1/notes.md)

## 1.58.0 版本说明（本 PR 新增）

NetworkManager 客户端库 —— 面向 OHOS / HarmonyOS PC 的 conan 适配。

### Overview

`libnm` 是 NetworkManager 的 GObject 客户端 API：应用通过它在 D-Bus 上与
NetworkManager 守护进程交互，完成网络状态查询、连接配置、Wi-Fi 扫描、密钥
管理等。它是大量桌面网络面板与网络工具的底层依赖。

上游把客户端库与守护进程放在同一个 Meson 工程里（没有「只构建 libnm」的
开关），因此本仓按「整树构建、只打包客户端库」的方式交付：

| 交付内容 | 说明 |
|----------|------|
| `lib/libnm.so.0` | 运行时 SONAME（实体文件，OHOS 已自签名） |
| `lib/libnm.so` | 链接期别名（实体文件，非软链） |
| `include/libnm/*.h` | 公共头（`<libnm/NetworkManager.h>` 为入口） |
| `lib/pkgconfig/libnm.pc` | pkg-config 名 `libnm`，`Libs: -lnm` |
| `licenses/COPYING.LGPL` | 上游许可证 |

不交付 NetworkManager 守护进程、`nmcli`、`nmtui` 及设备插件 —— 它们需要
内核 netlink / D-Bus 系统总线与 systemd 集成，超出客户端库的适配面。

### Upstream

- 项目主页：<https://gitlab.freedesktop.org/NetworkManager/NetworkManager>
- 源码归档：`NetworkManager-1.58.0.tar.xz`（GitLab generic package，见版本级
  `conandata.yml` 的 `sources.url` 与 `sha256`）
- 构建系统：Meson

### OHOS 适配要点

1. **可选项大幅裁剪**：polkit、selinux、libaudit、systemd 系列、nss/gnutls
   （`crypto=null`）、libpsl/libcurl（concheck）、modem-manager、teamd、OVS、
   cloud-setup、CLAT、eBPF、NBFT、Qt、readline、nmcli、nmtui、bluez5-dun、
   iwd、ppp、docs/man/introspection/vapi 全部关闭；保留 `wifi=true` 与
   `tests=yes`。
2. **pkg-config 垫片**：`dbus-1.pc`、`libudev.pc`、`gio-unix-2.0.pc` 三个垫片
   由配方 `generate()` 生成，用来对上「Debian/conan 包名」与「上游
   `dependency()` 名」的差异。
3. **脚本显式解释器**：OHOS 无 `/bin/bash`，且本构建域禁止脚本按 shebang 做
   解释器域转移；构建期、测试期、安装期脚本统一改为显式解释器 + 脚本路径
   参数（详见 `notes.md`）。
4. **SONAME 实体化 + ELF 自签名**：OHOS musl 不能加载「SONAME 名是软链」的
   库，装包时把软链族物化为规则文件，并对包内 ELF 逐个签名。

### 消费者用法

```cmake
find_package(libnm REQUIRED CONFIG)          # CMakeDeps
target_link_libraries(app PRIVATE libnm::libnm)
```

```sh
pkg-config --cflags --libs libnm             # pkg-config 通道
```

- 头文件入口：`#include <libnm/NetworkManager.h>`
- 运行时需要 `LD_LIBRARY_PATH` 指向本包 `lib/`（OHOS musl 不解析 RUNPATH）。
- 链接 libnm 时请一并满足 `glib-2.0 / gio-2.0 / gobject-2.0 / gmodule-2.0`
  的头与库（`NetworkManager.h` 无条件包含 `gio/gio.h`）。

### Known limitations

- 本机沙箱（seccomp）拦截 netlink/socket 系统调用，上游 `platform/test-*-linux`
  一类用例无法在本机跑通（同族 `*-fake` 用例全部通过）。
- 本平台（HMDFS）不支持创建符号链接，依赖 `libnm.so` 开发软链的上游
  `check-local-tests-client` 用例无法执行；包内运行时不依赖软链。
