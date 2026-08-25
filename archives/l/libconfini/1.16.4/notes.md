# libconfini 1.16.4 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 `libconfini.so` / `libconfini.a` 与 `confini.h`，供 INI/.conf 解析。

## 上游核实（以源码为准，非 Homebrew/ConanCenter）
- 仓库：https://github.com/madmurphy/libconfini （tag `1.16.4`，commit 6072416）
- 源码 tarball：`libconfini-1.16.4-with-configure.tar.gz`（release 自带 configure）
- SHA256（本机实测）：`f4ba881e68d0d14f4f11f27c7dd9a9567c549f1bf155f4f8158119fb9bc9efd6`
- License：GPL-3.0-or-later（`COPYING` 为 GPL v3；`confini.h`/`confini.c` 头注 "version 3 or any later version"）
- 构建系统：GNU autotools（`configure.ac` + `Makefile.am`，tarball 含预生成 `configure`）
- 语言：纯 C99，仅依赖 C 标准头 `stdio.h`/`stdlib.h`/`stdbool.h`/`stdint.h`，无任何外部库依赖
- shared/static：`LT_INIT([win32-dll])`，默认同时构建 shared 与 static
- 安装产物：`lib/libconfini.so*`、`lib/libconfini.a`、`include/confini.h`、`lib/pkgconfig/libconfini.pc`、`share/man/man3/*`
- pkg-config 名称：`libconfini`（`src/libconfini.pc.in` → `Name: @PACKAGE_CONFNAME@` = `libconfini`）
- 库名：`libconfini`（`-lconfini`，PROJECT_LOCALNAME = `libconfini`）
- 公开头：`confini.h`

## 关键适配
- **无 patch**：源码本身不需要任何补丁。
- **config.sub 不识别 `*-linux-ohos`**：bundled `config.sub` 为 2021 版本，无 ohos 三元组。
  采用与已验证通过的 `libdatrie/0.2.13` 相同的做法：传 `--build/--host=aarch64-unknown-linux-musl`。
  libconfini 的 configure 不做任何 OHOS 特定探测，musl 三元组被接受且构建结果一致，
  从而**完全避免** config.sub/config.guess 补丁。
- **修 configure 的 `umask 077` → `umask 022`**（HMDFS E011）：config.status 在 HMDFS 上
  无法在 077 umask 下创建临时文件，构建会死。同 libdatrie/0.2.13 记录的坑。
- **删 `lib/*.la`**：libtool `.la` 烤死绝对 libdir（`prefix=/` 下为 `/lib`），会把下游
  libtool 引到 `//lib/libconfini.la` 死路。链接信息已由 `.pc` 与 cpp_info 提供。

## 上游正式测试
- `tests/autotest.c` — 唯一正式测试源文件；`check_PROGRAMS = autotest`；`TESTS = $(check_PROGRAMS)`。
- 1 个测试程序、1 个测试用例：解析 `testkey=testvalue`，校验 `strip_ini_cache()` 返回 0。
- `examples/`（cplusplus/ini_files/miscellanea/topics/utilities）与 `dev/tests/`（performance/playground/null-byte_injection）为 demo/性能/安全演示，**非**正式 `make check` 目标，不计入。

## 状态
built（OHOS aarch64 conan create + test_package 通过）
