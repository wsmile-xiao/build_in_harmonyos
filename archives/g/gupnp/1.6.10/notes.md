# gupnp 1.6.10 适配笔记

## 编译环境
- 构建系统: meson (>= 0.54.0)
- 编译日期: 2026-09-06
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链）
- 状态: built
- 积分归类: 【依赖项】路径 A 正常适配

## 背景

gupnp 是 GUPnP 协议栈核心库（SSDP 之上的 UPnP 设备/服务控制点与根设备），
是 gssdp 的直接下游（gssdp 1.6.6 已于 2026-09-02 适配 built）。上游 1.6.10
依赖 glib-2.0/gio-2.0/gmodule-2.0/gobject-2.0/gio-unix-2.0（glib2）、
libsoup-3.0（libsoup3）、gssdp-1.6 >= 1.6.5（gssdp）、libxml-2.0（libxml2）。
构建系统为 meson，与 gssdp/libsoup3 同栈，交叉/原生处理复用其已验证方案。

## 编译步骤

```bash
# 源码（官方 GNOME 源 + NJU 镜像，两边 sha256 实测一致）
# https://download.gnome.org/sources/gupnp/1.6/gupnp-1.6.10.tar.xz
# sha256: a1ee07b7b12673c32d7fc73ca158a50c1a4dc69ab35b65e94d24d38ac875345e

# 设备 shell 默认 LD_LIBRARY_PATH 含空格（chipset-pub-sdk:   <空格>/system/lib64），
# musl 动态链接器解析失败 → ninja 加载 libc++_shared.so 报 rc=127（gssdp 铁证），
# 需重设为无空格路径。
export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64"

conan create archives/g/gupnp/1.6.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 默认配置必编译 `gupnp-linux-context-manager.c` 并编译失败：`linux/socket.h: redefinition of 'sockaddr_storage'`（与 sys/socket.h:377 冲突） | 上游探测 `cc.has_header('linux/rtnetlink.h')` 是**单头独立探测**，在 OHOS sysroot 上通过（实测 clang -fsyntax-only PASS）；而真实源文件把 `<sys/socket.h>` 与 `<linux/netlink.h>`/`<linux/rtnetlink.h>` 放同一翻译单元（实测 clang 报 redefinition）——探测假阳性 | 补丁 0001：把探测改成与真实翻译单元一致的 `cc.compiles`（sys/socket.h + linux/netlink.h + linux/rtnetlink.h 同 TU）。glibc 系通过、OHOS 失败 → `netlink_available=false` → 不编译 linux CM、不加 `-DUSE_NETLINK` → 回退上游 unix context manager（ifaddrs，BSD 等平台同款路径）。**无平台宏、无功能删减**（R8 合规：修探测逻辑本身）；设备实测 getifaddrs 正常（lo/wlan0 等 17 条，含 IPv4/IPv6） |
| 2 | 静态 glib 全量入链：首轮链接行出现 `libglib-2.0.a/libgobject-2.0.a/libgio-2.0.a/...` 绝对路径级联（3812 个定义符号） | 已发布 libsoup3 配方的 `cpp_info.libs` 内联了静态 glib 全家（glib-2.0/gobject/gio/gmodule/gthread/ffi/intl），PkgConfigDeps 把它写进 generators/libsoup-3.0.pc 的 **Libs 行**；仅清空 generators/glib-2.0.pc（gssdp 方案）不够 | generate() 里对 generators/*.pc 做 token 级剔除：从 libsoup-3.0.pc/gssdp-1.6.pc 的 Libs 行剔除 GLIB_STATIC_TOKENS（保留 -lsoup-3.0/-lgssdp-1.6 本体），Requires 行剔除 glib-2.0 |
| 3 | `ld.lld: error: unable to find library -lffi` | pc-fix 的 gobject-2.0.pc `Requires: libffi` → 解析到 glib2 包内 libffi.pc（prefix=/ → `-L//lib -lffi`），设备无系统 libffi，不可解析 | pc-fix 复制件同时从 Requires 行剔除 libffi（Libs 全空后无人需要链 libffi） |
| 4 | 静态 glib 剔除后剩 2 个未解析符号：`g_uuid_string_random`（gupnp-service.c SID 生成）、`g_zlib_compressor_new`（http-headers.c gzip 压缩体）——libsoup-3.0.so 只导出它自己用到的 glib 符号（实测 dynsym 无这两个） | meson 对 shared library 默认 `-Wl,--no-undefined`；这 2 个是核心功能路径（R8 禁止 stub/删功能） | 从 glib2 静态库用 `ar x` 提取**仅有的两个**定义翻译单元（guuid.c.o、gzlibcompressor.c.o）组成配方本地 libglib-min.a，经 glib-2.0.pc 的 Libs 注入链接。归档按需拉取；两成员全部 `g_type_*`/`g_object_*` 引用被 libsoup 导出表满足（nm 逐符号核对）→ **GObject 单副本保住**（readelf 实测 libgupnp-1.6.so 定义符号 257 个、g_* 仅 8 个＝guuid+GZlibCompressor 自身，无 g_type_/g_object_ 重复定义）。对照实验：直接 `-lglib-2.0 -lgio-2.0` 整档链接会级联拉入 3812 个符号（弃用） |
| 5 | meson gnome.mkenums() 查询 pkg-config 变量 `glib_mkenums` 失败：`Could not get pkg-config variable and no default provided` | PkgConfigDeps 生成的 glib-2.0.pc 无 glib_mkenums 变量（glib2 包自带 .pc 才有） | generate() 向 generators/glib-2.0.pc 追加 `glib_mkenums=/…/bin/glib-mkenums` 等工具变量（gssdp 的 tc.binaries 方案保留作双保险） |
| 6 | gio-unix-2.0.pc 解析链缺 libffi/pcre2 | pc-fix 副本沿用 glib2 原生 Requires 链 | PKG_CONFIG_PATH 同时含 pc-fix、glib2 包原生 pkgconfig 目录（pc-fix 在前）；libffi 从 Requires 剔除后不再需要 |
| 7 | 共享库 strip 会破坏 .codesign 哈希 | OHOS loader 校验 .so 内嵌哈希与内容一致 | tc.strip=None；meson install 清理 DT_RUNPATH 会改写 .so → 用 build 目录原始链接产物覆盖安装产物（gssdp 同款） |

## GObject 单副本方案（继承 gssdp 1.6.6）

```
消费者 (exe/test)
   │ UND g_* / gupnp_*
   ▼
libgupnp-1.6.so.0.106.10     ← gupnp 代码 + guuid.o/gzlibcompressor.o 最小成员
   │ NEEDED
   ▼
libsoup-3.0.so.0             ← 导出 4121 个 g_*/soup 符号（唯一 gobject 副本）
libgssdp-1.6.so.0  libxml2.so.16  libpsl/libidn2/libnghttp2
```

- GLib 系 .pc（pc-fix 复制件 + generators 生成件）的 Libs 全部为空或剔除了
  静态 glib token；静态 glib 不进入任何链接命令；
- libgupnp.so 与测试产物对 g_type_*/g_object_* 的引用全部是 UND，运行时统一
  解析到 libsoup-3.0.so 导出的唯一 gobject 副本；
- 产物画像（readelf 实测）：libgupnp-1.6.so.0.106.10 定义符号 257 个，其中
  g_* 8 个（g_uuid_string_random/is_valid + GZlibCompressor 类方法），无
  g_type_*/g_object_* 定义；NEEDED = libsoup-3.0.so.0、libgssdp-1.6.so.0、
  libxml2.so.16、libc.so；.codesign 段在。
- 上游 7 项 meson test（56 个 TAP 子用例）与 test_package 全部通过——若
  GObject 多副本撕裂（g_type_register_static assertion SIGABRT）会在测试中
  立即暴露（gssdp 历史铁证），实测未发生。

## 源码修改

- patches/0001-meson-build-harden-netlink-detection.patch：仅改 meson.build
  的 netlink 可用性探测（单头 has_header → 与真实翻译单元一致的 cc.compiles
  组合探测），附说明注释。无平台条件编译（无 __OHOS__），无空 stub，无功能
  删减：探测失败时走上游为非 netlink 平台维护的 unix context manager 路径。
- tools/gupnp-binding-tool-1.6：上游安装的纯 Python 3 脚本（无 gi 依赖），
  设备实测可用（python3 <script> 生成 C 绑定代码）；shebang 指向
  /usr/bin/python3（设备无该路径），经 commands.json 以 `python3` 前缀调用。

## 测试统计

上游测试（meson test，OHOS 设备原生，--timeout-multiplier=16）：
7 个测试程序，TAP 子用例 56/56 通过、0 失败、0 跳过（testlog.txt 实测）：

| 程序 | TAP 计划 | ok | not_ok | skip |
|------|---------|----|--------|------|
| context | 22 | 22 | 0 | 0 |
| bugs | 10 | 10 | 0 | 0 |
| service | 2 | 2 | 0 | 0 |
| acl | 2 | 2 | 0 | 0 |
| service-proxy | 13 | 13 | 0 | 0 |
| context-filter | 4 | 4 | 0 | 0 |
| context-manager | 3 | 3 | 0 | 0 |
| 合计 | 56 | 56 | 0 | 0 |

取数口径：glib TAP（`1..N` 计划行 + `^ok `/`^not ok ` 计数），统计单位为
TAP 子用例；命令与日志见 reports/。
