# libgtop2

## 简介

libgtop（对外库名 **libgtop-2.0**）是 GNOME 的可移植系统信息采集库：CPU/内存/交换区/负载/运行时间/
进程列表/进程内存映射/网络设备与负载/磁盘 I/O 等，全部通过宿主的 `/proc` 等系统接口获取，
是 gnome-system-monitor 等程序的数据来源。

- 上游仓库：https://gitlab.gnome.org/GNOME/libgtop
- 本仓归档版本：**2.41.3**（tag `2.41.3` = commit `526a51698173535312f6cab1408ac9a225063c9d`）
- 许可证：GPL-2.0-or-later
- 构建系统：autotools

产物：`libgtop-2.0`（默认静态 `.a`）、`include/libgtop-2.0/`（43 个头文件）、
`lib/pkgconfig/libgtop-2.0.pc`、`libexec/libgtop_daemon2`、`libexec/libgtop_server2`。

## OHOS 适配

- 平台三元组（E007/E072）：`config.guess` 增 HarmonyOS 识别 → `aarch64-unknown-linux-ohos`；
  `config.sub` 接受 `ohos` 作 OS 并放行 `linux-ohos` 内核组合（kernel-os 白名单）
- HMDFS 权限（E011）：`configure` 内 `config.status` 模板的 `umask 077` → `022`，
  规避 `mktemp -d ./confXXXXXX` 在 HMDFS 上产出不可写目录
- 无 texinfo 的处理：补丁刷新 `configure` 的 mtime 会连带 `doc/stamp-vti` → `version.texi`
  → `libgtop2.info` 走 texinfo 链；配方在打补丁前后记录/还原 `configure` 的 mtime，
  复用上游随包发布的 `doc/libgtop2.info`（同时避免 `mdate-sh` 解析失败把 `version.texi`
  写成 `set` 的环境变量转储）
- ngettext（intl）：源码经 glib 的 `gi18n-lib.h` 无条件 `#include <libintl.h>` 使用 `ngettext()`，
  而 OHOS SDK sysroot 的 `libintl.h` 是空壳；配方直接依赖 `proxy-libintl`，
  使 Conan 生成的 `glib-2.0.pc` 带 `Requires: intl`，其 `libintl.h` 进入编译行
- 关闭 OHOS 上不可用的可选件：`--without-x`（无 X11/Xauth）、
  `--enable-introspection=no`（g-ir-scanner 依赖闭包不完整，E212）

## 依赖

- `glib/2.88.3`（`glib-2.0` / `gobject-2.0`；`configure.ac:107` PKG_CHECK_MODULES，公共头文件传染）
- `proxy-libintl/0.5`（ngettext / libintl.h 提供者）
- `pkgconf/3.0.6`（构建期 pkg-config）

## 上游测试

上游**无自动化测试套件**（无 `tests/`、无 `check_PROGRAMS/TESTS`）。唯一可运行入口为
`examples/` 的 20 个样例，已逐个真实执行：**19 通过 / 1 平台受限失败**（`disk` 读
`/proc/diskstats` 在 OHOS 上对非 root 返回 EACCES —— 平台限制，非适配缺陷）。
逐项清单见 `2.41.3/test_package/MANIFEST.yml`，日志见 `2.41.3/reports/`。

## 功能验证

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd   # exit 0
# test_package：2/2 通过（test_libgtop2_api + test_libgtop2_ohos，共 7 条断言）
#   其中 test_ohos.c 为鸿蒙特有用例（/proc/stat 每 CPU ticks、/proc 进程表、sysinfo ncpu>=1）
```

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.41.3 | built | 首次适配；`shared=False`（静态），3 个平台补丁（config.guess/config.sub/configure） |
