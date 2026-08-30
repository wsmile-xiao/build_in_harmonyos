# avahi-tools

avahi-tools 是 Avahi（mDNS/DNS-SD，即 Zeroconf 网络发现）项目的客户端命令行工具集，
取自 avahi 源码树的 `avahi-utils/` 子目录。工具通过 libavahi-client 经 D-Bus 与
avahi-daemon 通信，完成 mDNS 服务浏览、解析、发布与主机名管理。

## 包含的工具

| 命令 | 功能 |
|------|------|
| `avahi-browse` | 浏览网络上的 mDNS 服务与域（`-a` 全部服务、`-D` 浏览域、`-r` 解析） |
| `avahi-resolve` | mDNS 主机名 ↔ IPv4/IPv6 地址互相解析（`-n` 按名、`-a` 按地址） |
| `avahi-publish` | 发布 mDNS 服务或地址（`-s` 服务模式、`-a` 地址模式） |
| `avahi-set-host-name` | 请求 avahi-daemon 更改机器的 mDNS 主机名 |

`make install` 时上游还会创建便捷别名：`avahi-browse-domains`、
`avahi-resolve-host-name`、`avahi-resolve-address`、`avahi-publish-address`、
`avahi-publish-service`。

## OHOS 适配

- 同源拆包：与已合入的 `avahi-glib`、`avahi-compat-libdns_sd` 使用同一份上游归档
  （tag v0.9-rc5），只构建 `avahi-common` → `avahi-client` → `avahi-utils` 三个子目录。
- 归档不含生成的 configure，配方经 autogen.sh 引导；automake/libtool/gettext 走
  tool_requires，并按 knowledge E337 方案搭建任务级启动器闭包（HMFS 拒绝直接执行
  跨 UID Conan 缓存中的脚本）。
- 生成的 configure 在运行前文本移除 AS_TMPDIR 的 `umask 077 && mktemp -d` 前缀
  （E011/E112/E118，HMFS 无法写入 2700+setgid 临时目录）。
- 应用包不跑 make install：构建后按 ELF 魔数从 libtool 输出中收集 4 个程序二进制到
  `bin/`，别名优先符号链接、失败退化为独立副本（abbtr/git-who 工具包先例）。
- 上游测试：接入内置依赖 avahi-common 的 7 个 automake TESTS（无需守护进程）。

## 依赖关系

- 编译依赖：dbus/1.14.10（libavahi-client 需要）、expat/2.8.2.1（override，规避
  conancenter cmake/4.4.2 在 OHOS 的 KeyError）
- 构建工具：automake/1.18、libtool/2.5.4、gettext/0.22.5.1（autoconf/m4 由 SDK 提供）
- 运行依赖：D-Bus system bus 上的 avahi-daemon（实际浏览/发布功能需要；HarmonyOS PC
  默认没有该服务，`--help`/`--version` 等离线路径不受影响）

## 参考资料

- 上游仓库: https://github.com/avahi/avahi
- 版本: tag v0.9-rc5（PACKAGE_VERSION "0.9-rc5"）
- License: LGPL-2.1-or-later
