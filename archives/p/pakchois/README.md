# pakchois — OpenHarmony 编译档案

## 软件简介
pakchois（Joe Orton 编写）是一个 **PKCS#11 薄封装库**：负责加载 PKCS#11
provider 模块（DSO）并转发面向对象的 C 接口，目标是让调用方不必关心模块在
系统中的存放位置/命名，且不依赖任何特定密码工具包（"just another PKCS#11
wrapper library"，主页 http://www.manyfish.co.uk/pakchois/ ）。许可证为
**LGPL-2.0-or-later**。本次适配上游发布版 **0.4**（2008 年 autoconf 2.61 /
libtool 时代工程）。

## OHOS 适配要点
- **config.sub（2006-09-20）不识别 aarch64**：`aarch64` 出现次数为 0。适配为
  最小补丁：在「裸 CPU 列表」补入 `aarch64 | aarch64_be`、在「带厂商名 CPU
  列表」补入 `aarch64-* | aarch64_be-*`（与既有 `arm`/`arm-*` 同构）。
  configure 显式传 `--build=aarch64-unknown-linux-gnu`（`-linux-gnu` 该
  config.sub 原生支持），从而完全跳过 config.guess（2006 版无法识别
  `uname -s=HarmonyOS`）。
- **configure.ac 硬检查 `-lpthread`/`-ldl`**（`AC_CHECK_LIB(... , [AC_MSG_ERROR])`）：
  OHOS musl 将两者并入 libc。向 configure 注入缓存变量
  `ac_cv_lib_pthread_pthread_mutex_lock=yes` / `ac_cv_lib_dl_dlopen=yes` 跳过
  实链探针（autoconf 对 `VAR=value` 参数直接预置缓存，见 conanfile 注释）。
- **GNU gettext po/ 子树**（`AM_GNU_GETTEXT([external])`）：传 `--disable-nls`，
  `po/Makefile.in.in` 自带空 `all-no:` 目标，gettext 工具链不再需要。
- **HMDFS autotools 临时目录问题**：configure/config.guess 中 `umask 077` →
  `022` 放宽（config.status 的 mktemp 临时目录在 HMDFS 上无组写权限），并把
  `TMPDIR` 指向 conan 可写 build 目录。
- **上游无自动化测试**：`Makefile.am` 未注册任何 `TESTS`；`test` 是
  `noinst_PROGRAMS` 的手动/演示程序，运行期需要一个真实 PKCS#11 token
  （`--pkcs11module <token.so>`）。如实记录 `upstream_test=0`，不做虚构；
  反空壳验证放在 test_package（dlopen `libpakchois.so` + dlsym 真实导出符号）。

## 依赖关系
- 无编译/运行依赖（仅 C 运行时；musl libc 提供 dl*/pthread* 符号）
- 被依赖: 无（独立 PKCS#11 包装库）

## 参考资料
- [pakchois 官方主页](http://www.manyfish.co.uk/pakchois/)
- [pakchois-0.4.tar.gz](http://www.manyfish.co.uk/pakchois/pakchois-0.4.tar.gz)
  （sha256 `d73dc5f235fe98e4d1e8c904f40df1cf8af93204769b97dbb7ef7a4b5b958b9a`）
- 说明：上游 0.4 发布包**不含独立 COPYING 文件**，许可证文本仅在
  `pakchois.h` 等文件头部声明（GNU Library General Public License v2 or
  later）——本次在清单/conanfile 中如实声明为 LGPL-2.0-or-later。
