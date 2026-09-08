# centerim5 5.0.1 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac，需先 bootstrap 生成 configure）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. `bootstrap`：上游 tarball 不带 configure，需手动执行 autotools 序列
   （aclocal -I m4 → autoheader → autoconf → automake --add-missing --copy）
2. `./configure --prefix=/usr CC=clang CXX=clang++`，依赖由 conan 提供
   （purple/glib-2.0/sigc++-2.0/ncursesw 全部通过 PKG_CHECK_MODULES）
3. `make -j1`
4. `make check`：上游唯一测试 treeview.test（termex 终端模拟 playbook）1/1 PASS
5. conan 配方：`conan create` 干净构建 + 8 门禁验证（G0-G4 + L2/L4/L5 全 PASS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap 时 `configure` 生成后 `PKG_CHECK_MODULES` 未展开 | aclocal 搜索路径缺 `pkg.m4` | 配方 build-aux/m4 自带 pkg.m4，aclocal -I m4 展开 |
| 2 | 本机 libtoolize 损坏（func_error），`config/ltmain.sh` 未生成 | 环境 libtool 脚本不完整 | 配方自带 libtool 2.4.7 的 ltmain.sh，手动执行 autotools 序列 |
| 3 | configure 找不到 `purple` 包 | pidgin 配方 pkg_config_name=libpurple，PkgConfigDeps 生成 libpurple.pc | generate() 生成 purple.pc 别名并修正 include 根路径 |
| 4 | config.status `Permission denied`（subs1.awk） | autoconf 2.72 `umask 077 && mktemp -d` 创建受限临时目录，hmdfs 无法写入 | 生成 configure 后放宽 umask 为默认值 |
| 5 | src/request.h 与 libpurple request.h 同名，PurpleRequestField 未定义 | automake DEFAULT_INCLUDES（-I.）优先命中 centerim5 自身头文件 | 生成的 Makefile DEFAULT_INCLUDES 前插 pidgin include 路径 |
| 6 | `-l:ld-musl-aarch64.so.1` 链接失败 | ohpcd glib-2.0.pc 内嵌 musl 加载器引用 | 净化生成的 .pc，剥离 musl 引用 |
| 7 | glib.h not found | ohpcd glib-2.0.pc 将 -I 误放 Libs 行、无 Cflags | sanitize .pc：-I 移入 Cflags |
| 8 | undefined bindtextdomain/gettext | glib 静态库依赖 libintl 但 pc 未带 -lintl | glib-2.0.pc 追加 -lintl |
| 9 | `--version` smoke 失败 | `--prefix=/usr` 装到 p/usr/bin，VirtualRunEnv 只认 p/bin | package() 中 usr/bin → bin 归位 |
| 10 | test 进程缺 libc++_shared.so | 非 conan 依赖包，conanrun 环境不含其目录 | test.sh 定位 hnp SDK 并注入 LD_LIBRARY_PATH |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| 0001-tests-colorpicker.cpp.patch | `&(std::ostringstream() << x)` 在 C++11+ 对右值取地址非法，改 std::to_string() |
| 0002-tests-termex.py.patch | 子进程 execle 未继承 LD_LIBRARY_PATH，测试程序找不到动态库；改为继承 |
| 0003-tests-window.cpp.patch | 同 colorpicker：右值取地址改 std::to_string() |

## 依赖版本

- pidgin/2.14.14（libpurple）
- libsigc/2.10.8（sigc++-2.0）
- glib/2.84.0
- ncurses/6.4（ncursesw）
- libtermkey/0.22
- unibilium/2.1.2
- gettext/0.22.5
- libiconv/1.17

## 验证结果

```bash
# conan 干净构建 + 8 门禁
ohc-run.py conan-verify centerim5 5.0.1   # G0-G4 + L2/L4/L5 全 PASS
# 上游测试（AI 编译阶段）
make check                                # treeview.test 1/1 PASS
# test_package smoke
bash test.sh                              # --version / --help / 启动 3 项 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/centerim5-5.0.1-ohos-aarch64.tar.gz | bin/centerim5 |

## 注意事项

- tarball 无预生成 configure，必须 bootstrap（配方 build() 手动执行 autotools 序列）
- 测试运行需 tic（ncurses 包 bin）在 PATH 且 termex.py 子进程继承 LD_LIBRARY_PATH
