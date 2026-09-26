# ancient

ancient is a decompression library for a wide range of old file formats used on Amiga, DOS and
other retro/legacy platforms (RNC, ICE, StoneCracker, PackIce, DMS, LZX, PowerPacker, Bzip2,
gzip, and hundreds more). It exposes the `ancient::Decompressor` C++ API and ships the `ancient`
command-line tool for verification.

- 上游主页: https://github.com/temisu/ancient
- 版本: 2.3.0
- 构建系统: Autotools (C++17)

## 组件

| 组件 | 用途 |
|---|---|
| libancient | 静态库（libancient.a），公开头文件 `ancient/ancient.hpp`，pkgconfig `libancient.pc` |
| ancient | 命令行验证工具（`verify <packed> <raw>` 逐字节比对解压结果） |

## OHOS 适配要点

- 发布 tarball 不含预生成 configure（configure.ac/Makefile.am 需 autogen）；配方以
  libtoolize → aclocal → autoconf → automake --add-missing 完整生成 build-aux 与 configure
  （tool_requires: automake/1.18 + libtool/2.5.4，制品仓已发布）
- autoconf-archive/pkg m4 宏（AX_CXX_COMPILE_STDCXX/AX_CHECK_COMPILE_FLAG/…）随配方
  export_sources 携带（CI 沙箱无 $HOME/.local/share/aclocal）
- OHOS 不被 config.guess 识别（uname -s=HarmonyOS）：configure 显式
  `--build=aarch64-linux --host=aarch64-linux` 跳过猜测
- 上游测试 testing/ 位于 v2.3.0 tag 但被 .gitattributes `testing export-ignore` 从发布
  tarball 排除：按源码测试入口恢复规则从官方 tag 拉取，obj/test 201/201 通过（见
  reports/upstream-test-ledger.md）