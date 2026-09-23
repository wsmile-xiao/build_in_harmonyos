# libhbaapi

> SNIA HBA API 的通用封装库：运行时把 `HBA_*` 调用转发给厂商库。

## 简介

libHBAAPI 是 SNIA 主机总线适配器（HBA）API 的平台无关封装：它按 `hba.conf` 列出
厂商库并在运行时加载，把 `HBA_GetVersion`、`HBA_LoadLibrary`、`HBA_GetAdapterName`、
`HBA_SendCTPassThru*` 等入口转发给具体厂商实现，使应用程序无需直接链接厂商代码即可
访问光纤通道（FC）适配器。

## OHOS 适配要点

- 上游只发源码与 `configure.ac`/`Makefile.am`（**没有生成的 `configure`**）：`build()` 先
  `autoreconf --install --force`。
- **不要**把 autoconf/automake/libtool 作为 `tool_requires`：它们会连带一个 Conan `perl`，
  其 XS 模块与执行 `autoreconf` 脚本的 perl 解释器不匹配（`Cwd.so` 无法 relocate）。
  直接使用环境中的工具即可（CI 与设备同镜像）。
- 上游 `configure.ac` 钉死 automake `-Wall -Werror`，现代 autoconf 的
  `AC_PROG_LIBTOOL` 弃用告警会变成错误 → 打补丁只保留 `-Wall`（**E007/E011** 见 `notes.md`：
  生成的 `configure` 里 `umask 077` 需放宽为 `022`，并显式传 `--build/--host` 避开
  `config.guess`）。
- 消费者注意：上游 `hbaapi.h` 使用 `struct tm` 但未包含 `<time.h>`，需先包含 `<time.h>`。
- 运行期 `hba.conf` 的路径在库内**硬编码为 `/etc/hba.conf`**（OHOS 只读），无厂商库时
  适配器数为 0；上游 demo `hbaapitest` 因此按设计 `exit 1`（本仓库执行并留证）。
- 产物：`lib/libHBAAPI.so.2`、`include/{hbaapi.h,vendorhbaapi.h}`、`lib/pkgconfig/HBAAPI.pc`、
  `etc/hba.conf`。

## 依赖

无。

## 使用

```cmake
find_package(HBAAPI CONFIG REQUIRED)
target_link_libraries(app PRIVATE HBAAPI::HBAAPI)
```

```c
#include <time.h>   /* hbaapi.h uses struct tm */
#include <hbaapi.h>

printf("%u\n", HBA_GetVersion());
if (HBA_LoadLibrary() == HBA_STATUS_OK) {
    HBA_UINT32 n = HBA_GetNumberOfAdapters();
    /* ... */
    HBA_FreeLibrary();
}
```

## 功能验证

```sh
conan create archives/l/libhbaapi/2.2.9 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；消费者 6/6（版本/加载释放/零适配器/查询拒绝/刷新）
```
