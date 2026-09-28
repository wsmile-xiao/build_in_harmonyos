# libmbim-tools

libmbim 项目的 MBIM（Mobile Broadband Interface Model）命令行工具集，用于与移动宽带
调制解调器（MBIM 设备）通信。

> 说明：libmbim-tools **不是**独立上游项目。libmbim 源码树同时构建 GLib 库与命令行工具；
> 本包是同名工具包（same-source tools-only），只交付工具、丢弃库产物
> （先例：`libimobiledevice-progs`、`libcpuid-tool`）。源码取自官方 libmbim 1.34.0。

## 功能概述

- `mbimcli`：MBIM 命令行客户端，查询/配置 MBIM 设备
- `mbim-proxy`：MBIM 代理守护进程（上游装到 libexec，本包置于 bin/）
- `mbim-network`：MBIM 网络的简单管理脚本（start/stop/status）

## OHOS 适配要点

1. **构建系统 = meson**（不是 autotools）。meson 经 `tool_requires("meson/1.11.0")` 提供，
   worker PATH 没有 meson。
2. **静态链入 libmbim-glib**：`-Ddefault_library=static`，交付的 bin/ 自含，不依赖被
   丢弃的 lib/。
3. **E091 sockaddr_storage 冲突**：OHOS 内核 UAPI `<linux/socket.h>`（经
   `<linux/netlink.h>`）与 libc `<sys/socket.h>` 都定义 `struct sockaddr_storage`。
   4 个补丁在包含内核头期间把 UAPI 结构体重命名（`__linux_uapi_sockaddr_storage`），
   不含平台宏。
4. **ELF 签名**：OHOS 拒绝执行未签名 ELF（Operation not permitted），打包时用
   `binary-sign-tool -selfSign 1` 签名 bin/ 下所有 ELF。
5. **可选特性禁用**：`-Dbash_completion=false -Dintrospection=false -Dman=false`。

## 依赖关系

- glib >= 2.56（提供 glib-2.0 / gio-2.0 / gio-unix-2.0 / gobject-2.0）
- meson >= 0.53（构建工具，tool_requires）

## 编译步骤

```bash
cd archives/l/libmbim-tools/1.34.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 补丁说明

- 0001-0004：E091 sockaddr_storage 重命名守卫（4 个 netlink/net-port-manager 源文件）

## 上游测试

meson 注册 9 个测试单元（libmbim-glib 8 个 + mbimcli quectel 1 个），
`build()` 内 `meson test` 实跑 9/9 通过。

## 参考资料

- 官网：https://www.freedesktop.org/wiki/Software/ModemManager/
- 源码：https://gitlab.freedesktop.org/mobile-broadband/libmbim
