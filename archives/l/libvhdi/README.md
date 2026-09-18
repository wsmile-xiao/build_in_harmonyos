# libvhdi

libvhdi 是 Joachim Metz（libyal 项目）提供的 C 语言库，用于访问 Virtual Hard
Disk（VHD，虚拟硬盘）镜像格式，支持固定大小与动态/differencing 磁盘。

## 功能概述

- 读取 VHD（VHD version 1）镜像的 footer、dynamic disk header、block allocation
  table、metadata table 等结构；
- 识别 VHDX（VHD version 2）文件签名；
- 提供 file 抽象（`libvhdi_file_*`）读取扇区数据、查询磁盘类型、介质大小、
  标识符（identifier）与父镜像信息；
- 随包提供 `vhdiinfo`（镜像信息）与 `vhdimount`（FUSE 挂载）命令行工具。

## OHOS 适配

- 构建系统：Autotools（发布包已自包含 `configure`、`aclocal.m4`、
  `config.guess`、`config.sub`、`Makefile.in`，不依赖 autoreconf）。
- 平台三元组：发布包自带的 `config.guess`（2024-07-27）无法识别 HarmonyOS
  （`uname -s = HarmonyOS`），配方显式传 `--build/--host=aarch64-unknown-linux-ohos`。
- HMDFS：Autoconf 默认创建 `0700` 临时目录，在 HMDFS 上不可写；配方在构建期把
  `configure` 中的 `umask 077` 改为 `022`，并用 `CONFIG_SHELL` 显式解释
  `configure` 与 upstream test runner（HMDFS 禁止直接执行源码树脚本）。
- libtool：`check_PROGRAMS` 生成的是包装脚本，真实 ELF 位于 `.libs/`；配方在
  OHOS 构建期给 `tests/test_runner.sh` 打运行期适配并把 `libvhdi/.libs` 注入
  `LD_LIBRARY_PATH`。该适配只改测试**运行方式**，不改任何上游测试用例语义。
- 可选特性：关闭 Python 绑定（`--disable-python`）与 libfuse
  （`--with-libfuse=no`），因此 `vhdimount` 构建但不具备挂载能力；`vhdiinfo`
  正常工作。
- 已知差异：上游 release archive 不含 `input/` 测试夹具，`test_vhdiinfo.sh`
  按上游规则 skip（退出码 77），不是适配失败。

## 依赖关系

- 编译依赖：无外部 Conan 依赖。13 个本地 libyal 组件（libcerror、libcthreads、
  libcdata、libclocale、libcnotify、libcsplit、libuna、libcfile、libcpath、
  libbfio、libfcache、libfdata、libfguid）随发布包一起提供，以 libtool
  `noinst_LTLIBRARIES` 形式静态并入 `libvhdi`。
- 运行依赖：libc（musl）；`vhdimount` 需要 libfuse 时才具备挂载能力（本包关闭）。

## 参考资料

- 上游仓库：https://github.com/libyal/libvhdi
- 版本 20251119 release：https://github.com/libyal/libvhdi/releases/tag/20251119
