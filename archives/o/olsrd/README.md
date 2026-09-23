# olsrd

**OLSR（Optimized Link State Routing，RFC 3626）路由守护进程** — olsr.org 实现。

olsrd 是一个 C 语言实现的路由守护进程，实现 OLSR 协议，用于无线 Mesh 网络；附带 20+ 可动态加载插件（httpinfo/jsoninfo/txtinfo 信息展示、secure 安全签名、nameservice 名称服务、watchdog 看门狗等）。

## 用法

```bash
olsrd [-f <configfile>] [-i <interface> ...] [-ipv6] [-d <debug_level>] ...
```

- 守护进程：`olsrd -f /etc/olsrd/olsrd.conf`
- 插件通过配置文件 `LoadPlugin("<绝对路径>.so.<版本>")` 加载，插件位于安装目录 `lib/`。
- 上游默认 Linux 插件集全部构建（除 `pud`：依赖 gpsd≤3.18 客户端 API，gpsd≥3.20 破坏性变更，0.9.8 上游停更未适配 → OHOS 构建裁剪）。

## OHOS 适配要点

- 构建强制 `OS=linux`（`make/guess_os.sh` 对 OHOS 返回 UNKNOWN，会误入 win32 分支）
- 编译期注入 `-D__MUSL__`：解决 OHOS NDK musl `sys/socket.h` 与 bionic 风格 `linux/socket.h` 的 `sockaddr_storage` 重定义（sysroot 内建协调钩子，E091/E119）
- bison≥3.x 生成的头文件临时名改写补丁 + clang 严格初始化补丁（见 0.9.8/patches/）
- 产物为 musl 动态 ELF（仅依赖 libc.so）
