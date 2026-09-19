# libhbaapi 2.2.9 适配笔记

## 编译环境
- 构建系统: 上游 autotools（**只有源码与 `configure.ac`/`Makefile.am`，无生成的 configure**）
- 编译日期: 2026-09-18
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 依赖: 无
- 状态: built

## 版本与源码
- 平台版本 `2.2.9` == Debian `libhbaapi_2.2.9.orig.tar.gz`
- sha256 `6f8c3613410f48ea1065410d3a2bc69c4b2ec93a5c15e8764c13ec8fd8d01b36`

## 产物
- `lib/libHBAAPI.so.2.0.2`（soname `libHBAAPI.so.2`）+ 软链
- `include/hbaapi.h`、`include/vendorhbaapi.h`
- `lib/pkgconfig/HBAAPI.pc`
- `etc/hba.conf`（上游的示例配置，列出厂商库路径）
- `licenses/COPYING`
- 已删除 libtool `.la`

## 构建要素

```sh
autoreconf --install --force          # 生成 configure/Makefile.in/aclocal.m4
# 程序化放宽 autoreconf 产物里的 umask 077 -> 022（E011）
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos
make -j1
```

| # | 问题 | 原因 | 处理 |
|---|------|------|------|
| 1 | 无 `configure`/`Makefile.in`/`aclocal.m4` | 上游只发源码 | `autoreconf --install --force` |
| 2 | `Can't load .../perl5/.../Cwd.so ... Perl_newSVsv_flags: symbol not found` | 把 autoconf/automake/libtool 作为 `tool_requires` 会连带 Conan 的 perl，其 XS 模块与执行 `autoreconf` 脚本的解释器不匹配 | **不引入 tool_requires**，直接使用环境中的 autoconf/automake/libtool（设备与 CI 同镜像） |
| 3 | `configure.ac:7: warning: The macro 'AC_PROG_LIBTOOL' is obsolete` + automake `-Werror` → autoreconf 失败 | 上游钉死 `-Wall -Werror` | `patches/0001-configure-ac-drop-Werror.patch` 只保留 `-Wall` |
| 4 | `config.status: error: could not setup config files machinery` | autoreconf 生成的 `configure` 同样用 `umask 077 && mktemp -d`；HMDFS setgid 挂载下 0700 目录不可写（**E011**） | `build()` 在 autoreconf 之后程序化把生成 `configure` 的 `umask 077` 改成 `022`（`archives/i/icoutils` 先例） |
| 5 | `configure: error: cannot guess build type` | `config.guess` 在 HMDFS 上无法创建临时文件（**E007**） | `generate()` 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos` |
| 6 | 消费者编译报 `field has incomplete type 'struct tm'` | 上游 `hbaapi.h` 使用 `struct tm` 但未 `#include <time.h>` | 消费者程序先包含 `<time.h>`（在 notes 中记录该上游怪癖） |
| 7 | 包内 `HBAAPI.pc` 的 `prefix=/` | Conan `--prefix=/` + `DESTDIR` | `package()` 重写 `.pc` 前缀 |

## 上游行为要点（消费者测试依据）

- `HBA_GetVersion()` 返回 `HBA_LIBVERSION`（实测 2）。
- 库启动时读取**硬编码的 `/etc/hba.conf`**；OHOS 的 `/etc` → `/system/etc` 只读且无该文件 ⇒
  `HBA_LoadLibrary()` 返回错误（`Cannot open /etc/hba.conf`），`HBA_GetNumberOfAdapters()` 为 0，
  `HBA_GetAdapterName(0, ...)` 被拒绝，`HBA_FreeLibrary()` 返回定义内的状态。
- 上游 demo `hbaapitest`（SNIA 样例程序，未接入 Makefile）在 `HBA_LoadLibrary()` 失败或
  适配器数为 0 时 **按设计 `exit(1)`**；本仓库在 `build()` 中编译并运行它、保留日志：
  输出 `HBA API Library version is 2`（证明封装库可用）+ `Cannot open /etc/hba.conf`（环境限制）。
  因此 R51 上游步骤如实申报为"执行但有环境限制"，不作为通过判据。

## 消费者测试（6 项断言）

`test_package/test_hbaapi.c`（仅用安装后的头与库）：

1. `HBA_GetVersion() == HBA_LIBVERSION`
2. `HBA_LoadLibrary()` 返回定义内状态
3. 无厂商库时适配器数为 0
4. 适配器 0 的名字查询被拒绝
5. `HBA_RefreshAdapterConfiguration()` 后适配器数仍为 0
6. `HBA_FreeLibrary()` 返回定义内状态

## 验证结果

```sh
conan create archives/l/libhbaapi/2.2.9 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；消费者 6/6；上游 demo 执行留证（见上）
```
