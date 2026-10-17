# librcc 0.2.13 适配笔记

## 上游信息
- 仓库: https://github.com/RusXMMS/librcc
- 版本: 0.2.13 (tag librcc-0.2.13, tarball 135 文件, sha256 112b2e6ea465e34bd28d34d39a9982da16a1cc2b016966123e12075b52833920)
- 构建系统: autotools (configure.ac + Makefile.am, 无预生成 configure, 需 autoreconf -fi)
- CMakeLists.txt 仅 Windows (非 WIN32 直接 FATAL_ERROR), OHOS 必须走 autotools

## 依赖
- 必需: libxml2/2.15.3 (configure.ac PKG_CHECK_MODULES libxml-2.0)
- 可选已关闭: gtk1/glib2/gtk2/gtk3/bdb/libtranslate, enca/librcd/libguess/aspell 保持自动探测 off, 避免引入未发布依赖
- 构建工具: automake/1.18, libtool/2.5.4.1 (tool_requires, 无 configure 需自举)

## OHOS 适配点
1. autoreconf -fi 自举 + _prepare_autotools_env 修正 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 硬编码路径
2. --build/--host=aarch64-unknown-linux-ohos 跳过 config.guess 探测 (E007)
3. 生成后 configure 去 `umask 077` (HMDFS setgid 目录不可写, E011)
4. make -j1 (HMDFS jobserver fifo EPERM, E074)
5. PkgConfigDeps + VirtualBuildEnv + PKG_CONFIG_PATH 指向 generators_folder, 满足 PKG_CHECK_MODULES(libxml-2.0)
6. 安装后删除 .la 文件

## 上游测试审计 (2 个回归目标, 已实跑)
- 根 Makefile.am: SUBDIRS = src engines external ui, 无 TESTS/check_PROGRAMS; src/ui/engines/external 亦无测试目标
- 但 examples/Makefile.am 定义真实测试目标: test (cat input-russian.txt | ./example2) 与 test-russian (cat input-russian.txt | ./example2 ru), fixture 为 examples/input-russian.txt (91 字节, 混合编码 + Good Morning/Guten Abend/Auf widersehen 三行 ASCII)
- 结论: 上游共 2 个测试条目。build() 用 HNP clang 直接编译 examples/example2.c 并原生运行两个管道, 断言退出码 0、输出非空、含 Current Language/Unable Detect Language 标记与 ASCII 透传内容, 输出 HMBS_UPSTREAM_TEST_RESULT(status passed, discovered/executed/passed 2/2/2); MANIFEST 声明 upstream_tests_exist:true + audit

## test_package (3 用例)
- test.c: rccInit / rccInitDefaultContext(input/output 类) / rccGetCurrentLanguageName + rccRecode ASCII 透传
- test() 先走标准 ctest, 再直跑二进制捕获 `^ok N` 计数校验 >=3, 输出 HMBS_TEST_PACKAGE_RESULT(discovered 3)
- 在 HarmonyOS aarch64 环境实测 (以真机预检日志为准)

## 申请人
- GitCode 用户名: zhangyuge147, 队伍名称: 龙骑士
