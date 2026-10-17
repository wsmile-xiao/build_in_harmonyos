# cvechecker OpenHarmony 编译记录

该目录包含 cvechecker 4.0（适配版本号 `4`）的 HarmonyOS PC 适配配方。cvechecker
是一个命令行安全审计工具，将本机已安装软件清单与本地 CVE 数据库匹配，报告潜在漏洞。

构建使用 Autotools，但 GitHub 的 archive tarball 只是 git 快照（仅含 configure.ac
与已提交的 configure，无生成产物 Makefile.in / aclocal.m4 / config.h.in），
因此配方在 configure 前用 `autoreconf -fi` 自举。

上游不携带任何自动化测试（各子目录 `make check` 均为空操作）；交付物为若干命令行工具
（cvechecker、pullcves、cvereport、cvegenversdat、cverules），通过 test_package
对打包产物做冒烟验证，并在 `commands.json` 中声明为工具类。

依赖 libconfig、sqlite3、argp-standalone（argp.h 不在 OHOS musl libc 中）。libbsd 无可用 conan 包，而 configure.ac 无条件要求它（源码仅使用其 `strlcpy`），配方在构建期合成最小 vendored libbsd（真实 strlcpy + `<bsd/string.h>` + libbsd.pc）。libconfig/sqlite3/vendored-libbsd 的 .pc 经 PkgConfigDeps / VirtualBuildEnv 被 configure 的 PKG_CHECK_MODULES 发现。
