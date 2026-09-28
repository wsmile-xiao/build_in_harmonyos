# libhbalinux

> SNIA HBA API 的 **FC 厂商库**：由 libHBAAPI 按 `hba.conf` 在运行时 dlopen，
> 数据来自 `scsi_transport_fc` 的 sysfs 树，缺失项回退到 libpciaccess。

## 简介

`libhbalinux` 实现 SNIA 主机总线适配器 API（FC-HBAAPI）的 Linux/OHOS 厂商侧：
它导出 `HBA_RegisterLibrary()` / `HBA_RegisterLibraryV2()`，把内部处理函数表
（`vendor_lib_entrypoints`）交回给通用库 libHBAAPI，后者再调用这些 handler 完成
版本查询、适配器枚举、端口/远端端口属性、SCSI 命令下发等操作。

适配器信息来源（`adapt_impl.h` 内的路径常量）：

- `/sys/class/fc_host` — 本地 FC 端口（`adapter_init()` 扫描）
- `/sys/class/fc_remote_ports` — 远端端口
- `/sys/class/scsi_device` — 发现的 LUN
- `/sys/class/net` — FCoE 网络设备
- sysfs 无法提供的信息（如厂商名）通过 **libpciaccess** 获取

## OHOS 适配要点

- 上游只发源码与 `configure.ac`/`Makefile.am`（**没有生成的 `configure`**；tarball 里名为
  `CONFIGURE` 的文件是通用 INSTALL 文本）→ `build()` 先 `autoreconf --install --force`。
- 环境（设备与 CI 同镜像）自带 autoconf/autoreconf/pkg-config/perl，但**没有**
  automake/aclocal/libtoolize → 用 `tool_requires automake/1.18 + libtool/2.5.4`
  （与 `libhbaapi/2.2.9` 一致）。
- `configure.ac` 探两个 pkg-config 模块：`pciaccess`（参与链接）与 `HBAAPI`（**只取 CFLAGS**，
  `AC_SUBST` 未导出 `HBAAPI_LIBS`）。`libpciaccess/0.19` 未声明 `pkg_config_name`，
  PkgConfigDeps 只产出 `libpciaccess.pc` → 在 generators 目录生成 `pciaccess.pc` 别名
  （`xf86-video-r128` 先例）。
- `libpciaccess` 钉死 `zlib/1.3.1`，其静态 `libz.a` 未使用 `-fPIC`，链入本库 DSO 时
  aarch64 报 `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`（**E541**）→
  `self.requires("zlib/1.3.1.2", override=True)`；zlib 保持静态以免与系统 `libz.so` 冲突（R26）。
- **E011**：autoreconf 生成的 `configure` 含 `umask 077 && mktemp -d`，HMDFS setgid 挂载下
  `config.status` 报 "could not setup config files machinery" → 程序化放宽为 `022`。
- **E007**：`config.guess` 在 HMDFS 上无法创建临时文件 → 显式传
  `--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos`。
- 上游 `install-data-hook` 会把 vendor 库路径追加进 `${sysconfdir}/hba.conf`；OHOS 上
  `/etc` 只读且无该文件，上游脚本自身容错：仅打印 `** WARNING: .../etc/hba.conf does not exist`。
- 本库**不安装头文件** → `package_info()` 置 `cpp_info.includedirs = []`，否则 CMakeDeps
  生成指向不存在目录的 `INTERFACE_INCLUDE_DIRECTORIES`。
- 上游 1.0.16 **无测试、无样例程序**（SNIA 样例属于 libHBAAPI 工程）；OHOS 专属验证在
  `test_package`：vendor 库可被 `dlopen("libhbalinux.so.2")` 且导出 `HBA_RegisterLibraryV2`，
  无 `/sys/class/fc_host` 时适配器计数为 0 且不崩溃。
- 产物：`lib/libhbalinux.so.2.0.2`（soname `libhbalinux.so.2`）、`lib/pkgconfig/libhbalinux.pc`、
  `licenses/COPYING`；DSO 的 `DT_NEEDED` 仅 `libc.so`（pciaccess/zlib 静态并入）。

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| libpciaccess | 0.19 | sysfs 缺失时的适配器信息（链接期） |
| libhbaapi | 2.2.9 | `hbaapi.h` / `vendorhbaapi.h`（编译期头文件，`transitive_headers`） |
| zlib | 1.3.1.2（override） | libpciaccess 的传递依赖；必须使用 PIC 静态库 |

构建工具（`tool_requires`）：automake/1.18、libtool/2.5.4。

## 使用

```cmake
find_package(libhbalinux CONFIG REQUIRED)
target_link_libraries(app PRIVATE libhbalinux::libhbalinux)
```

```c
#include <time.h>            /* 上游 hbaapi.h 使用 struct tm 但未包含 <time.h> */
#include <hbaapi.h>
#include <vendorhbaapi.h>

extern HBA_STATUS HBA_RegisterLibraryV2(HBA_ENTRYPOINTSV2 *ep);

HBA_ENTRYPOINTSV2 ep;
if (HBA_RegisterLibraryV2(&ep) == HBA_STATUS_OK) {
    ep.LoadLibraryHandler();
    HBA_UINT32 n = ep.GetNumberOfAdaptersHandler();   /* OHOS 无 FC 适配器时为 0 */
    ep.FreeLibraryHandler();
}
```

## 功能验证

```sh
conan create archives/l/libhbalinux/1.0.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=libhbalinux/1.0.16
# rc=0；消费者断言 11/11（含 OHOS dlopen 契约与 sysfs 事实 3 条）
```
