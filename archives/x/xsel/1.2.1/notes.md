# xsel 1.2.1 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am)
- 编译日期: 2026-08-14
- 编译器: clang/clang++ (OHOS toolchain)
- 状态: built

## 编译步骤

1. 源码获取: `get()` 下载 GitHub tag archive
   `https://github.com/kfish/xsel/archive/refs/tags/1.2.1.tar.gz`
   (sha256 18487761f5ca626a036d65ef2db8ad9923bf61685e06e7533676c56d7d60eb14，
   已在本机实测校验一致；vergenet.net 官方主页仅提供至 1.2.0 的 tarball，
   1.2.1 唯一官方发布源是 GitHub tag archive)
1a. 下载可靠性（2026-08-14 真机预检修复）: 预检 source() 时 github.com 直连
   ConnectTimeout(30s)/ReadTimeout(60s) 失败 → conandata.yml 的 url 改为有序列表，
   `https://gh-proxy.com/` 前缀镜像优先（复用 ci/conan/build_and_test.sh 维护的
   GitHub 镜像映射），官方 URL 保留最后兜底；gh-proxy.com 下载的归档 sha256 与
   官方完全一致（已本机实测 18487761...eb14），校验值不变。
2. 引导 autotools: `autoreconf -fi`（GitHub archive 不含预生成 configure，
   configure 是 autoreconf 产物不进版本库）；真机 HNP 缺 automake/aclocal/
   libtoolize（E178），经 `tool_requires("automake/1.18")` +
   `tool_requires("libtool/2.5.4")` 用 build profile 解析
3. pkg.m4: configure.ac 用 `PKG_CHECK_MODULES([X], [x11])`，aclocal 阶段需要
   pkg.m4 宏 → `_prepare_aclocal_path()` 动态定位 pkg-config 安装目录
   （aircrack-ng 同法），兜底扫描 `/data/service/hnp/*/*/share/aclocal`
   （afuse 同法），写入 ACLOCAL_PATH
4. x11.pc: X11 走 conan 依赖 `libx11/6.4.0`（ohpcd 已发布 OHOS armv8
   binary，kxl/libxscrnsaver 同法）。generate() 中 `PkgConfigDeps` 把
   x11.pc（及其依赖 xorgproto/xtrans/libxcb 的 .pc）生成到 generators
   目录；build() 内作用域注入 `PKG_CONFIG_PATH`（generators 目录 + 各
   依赖 lib/pkgconfig，try/finally 恢复，同 pidgin——真机 conan 2.x 的
   tc.environment()/PkgConfigDeps 注入实测不生效），configure 即可找到 x11.pc
5. Configure: `autotools.configure()`（AutotoolsToolchain 注入 clang 工具链
   与 OHOS 环境）
6. Make: `make -j1`（hmbs 注入 tools.build:jobs=1，配方显式 -j1）
7. Make install DESTDIR=$package_folder

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 configure 脚本 | git tree 快照，configure 是 autoreconf 产物不进版本库 | build() 中 `autoreconf -fi` 自举，tool_requires 引入 automake/libtool（E178） |
| 2 | PKG_CHECK_MODULES 宏未定义 | 发行 aclocal.m4 不含 pkg.m4 | 动态定位 pkg-config 安装目录的 share/aclocal/pkg.m4，设置 ACLOCAL_PATH（aircrack-ng 同法） |
| 3 | x11.pc 找不到 | X11 是 cmd-pkgs 预编译包，非 conan 依赖 | generate() 中 PKG_CONFIG_PATH 前置 DEFAULT_PREFIX/lib/pkgconfig（xclip 0.13 同法） |
| 4 | config.status 临时目录权限问题（预期） | E114: configure 用 umask 077 建临时目录，HMDFS 下不可写 | autoreconf 后把生成的 configure 中 umask 077 → 022 |
| 5 | configure 报 'working directory cannot be determined'（2026-08-14 真机预检） | HMFS/HMDFS 不支持 getcwd：bash 启动报 `getcwd: cannot access parent directories`，`pwd` 失败，configure 的 pwd 判定直接报错 | build() 开头 `os.chdir(build_folder)`（try/except 兜底，路径查找可用、仅 getcwd 不可用）+ `os.environ["PWD"]=build_folder` 预置 PWD；autoreconf 后改写 configure 的 pwd 判定：2.70+ 的 `ac_pwd=`pwd`` 追加 `2>/dev/null \|\| ac_pwd="$PWD"` 兜底（保留 test -n 判定），2.69 的 `if (pwd) >/dev/null 2>&1` 追加 `\|\| test -n "$PWD"`（同 aribb24/1.0.4）；cd/ls 走路径查找不受影响 |
| 6 | configure 报 `No package 'x11' found`（2026-08-14 真机预检） | cmd-pkgs 预编译 X11 目录（DEFAULT_PREFIX/lib/pkgconfig）无 x11.pc；且真机 conan 2.x 的 `tc.environment()` prepend PKG_CONFIG_PATH 不传播进 conanbuild.sh（pidgin 笔记已证实同款坑） | X11 改走 conan 依赖 `libx11/6.4.0`（ohpcd 已发布 OHOS armv8 binary，kxl/libxscrnsaver 同法）+ `PkgConfigDeps` 生成 x11.pc 到 generators 目录；build() 内作用域注入 `PKG_CONFIG_PATH`（generators 目录 + 各依赖 lib/pkgconfig，try/finally 恢复环境变量，同 pidgin） |
| 7 | configure 报 `cannot guess build type; you must specify one`（2026-08-14 真机预检） | autoreconf 生成的 config.guess（2024-07-27）认不出 HarmonyOS（uname -s 输出 `UNAME_SYSTEM="HarmonyOS"`），无法猜测 build type | generate() 在 OHOS 分支显式追加 `--build=aarch64-unknown-linux-gnu` 与 `--host=aarch64-unknown-linux-gnu`，绕过 config.guess 探测（同 a52dec/0.7.4、acct/6.6.4、xcb-util-renderutil/0.3.10） |

## 源码修改

无补丁（patches 为空）。xsel.c 未做任何修改。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| libx11 | 6.4.0 | conan 依赖（ohpcd 已发布 OHOS armv8 binary，kxl 同源） |
| automake | 1.18 | tool_requires（build profile） |
| libtool | 2.5.4 | tool_requires（build profile） |

## 上游测试

xsel 1.2.1 上游**无任何自动化测试**（已审计）：
- 源码树无 tests/、test/ 目录，无测试文件（唯一源码 xsel.c/xsel.h 是主程序）
- Makefile.am 仅有 bin_PROGRAMS=xsel 与 dist_man_MANS=xsel.1x，无 check/test
  目标、无 TESTS 变量
- configure.ac 仅做编译器/头文件/函数探测与 PKG_CHECK_MODULES，无测试宏

因此 test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` +
`upstream_test_audit`，test_package 输出
`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,"executed":0}`
（数字来自真实审计，非跳过）。

## 验证结果

test_package 冒烟测试（3 个真实断言）：
1. `xsel --version` → 输出 `xsel version 1.2.1 by Conrad Parker`，rc=0
2. `xsel --help` → 输出 `Usage: xsel [options]`，rc=0
3. `xsel --output -t 500`（无 X server）→ 优雅失败 rc≠0
   （XOpenDisplay 失败，验证 X11 代码路径真实可达）

> xsel 的 --version/--help 在 XOpenDisplay 之前就 exit(0)，headless 环境可验证。

## 注意事项

- xsel 是 X11 工具，运行时需要 X server（鸿蒙 PC 有 X/图形环境时可用）。
  编译期依赖 conan 包 libx11/6.4.0（ohpcd 已发布 OHOS armv8 binary）。
- 产物为单一可执行文件 bin/xsel（package_type = application），无库可链接，
  已创建软件级 commands.json（R38，tool 类型）。
- 上游 1.2.1 无测试套件，属审计确认后的 no_tests 情形，非"跳过测试"。
