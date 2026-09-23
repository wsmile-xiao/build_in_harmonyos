# comptext 1.0.1 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 configure，Autoconf 2.68 生成）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（OHOS SDK 26.0.0.18 / LLVM 15）
- 目标平台: aarch64-unknown-linux-gnu（config.guess 映射，qalculate-gtk 同款）
- 状态: built

## 编译步骤

```bash
# 依赖注入（libfltk/1.3.11 静态库 + libx11/1.8.13 + xorgproto/2025.1）
export FLTK_CFLAGS="-I$FLTK/include -isystem$X11/include -isystem$XPROTO/include"
export FLTK_LIBS="-L$FLTK/lib -lfltk_images -lfltk -lm -lX11 -lpthread -lm -ldl"
export PKG_CONFIG_PATH="$X11/lib/pkgconfig:$XPROTO/share/pkgconfig:..."
export CPPFLAGS="-I$X11/include -I$XPROTO/include"
export LDFLAGS="-L$X11/lib"
# configure conftest 运行时需 libX11 传递库 + libc++_shared.so
export LD_LIBRARY_PATH="<依赖lib目录>:/data/service/hnp/.../llvm/lib/aarch64-linux-ohos/c++"

./configure --prefix=/storage/Users/currentUser/usr/local
make -j1   # HMDFS 不支持 make jobserver（mkfifo 被拒），必须 -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-comptext-1.0.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 "cannot guess build type" | 2008 版 config.guess 不识别 HarmonyOS（uname -s=HarmonyOS） | 补丁 0001：添加 aarch64-HarmonyOS 分支映射为 aarch64-unknown-linux-gnu（qalculate-gtk 已合入同款最小补丁，config.sub 无需改动） |
| 2 | config.status 报 "Permission denied"（conf*/subs1.awk） | configure 用 `umask 077 && mktemp -d` 创建 0700 临时目录，HMDFS 属主映射为 file_manager 导致进程 euid 20020179 无法写入 | 补丁 0002：改 mkdir 保持组写权限（HMDFS 兼容） |
| 3 | main.cxx 报 "invalid suffix on literal" (UDL) | C++11 中 `"Version: "VERSION` 无空格时 VERSION 被词法视为用户自定义字面量后缀，宏不展开 | 补丁 0003：加空格 `"Version: " VERSION "\n"` |
| 4 | conftest 运行报 "Error loading shared library libc++_shared.so" | OHOS clang++ 链接的测试程序运行时找不到 C++ 共享库 | LD_LIBRARY_PATH 注入 OHOS SDK llvm/lib/aarch64-linux-ohos/c++（CI profile 同款配置） |
| 5 | conftest 运行报 libX11.so.6 / libxcb.so.1 等找不到 | libx11 为 shared 构建，运行时需其传递库链 | LD_LIBRARY_PATH 注入 libx11/libxcb/libXau/libXdmcp 依赖 lib 目录 |
| 6 | fltk-config 引用的 .cache 路径无效 | libfltk 的 fltk-config 记录的是 CI 构建时 .cache 路径，本地不可用 | 不用 fltk-config：configure.ac 检测到 FLTK_CFLAGS/FLTK_LIBS 已设即跳过检查，手动注入依赖路径 |

## 源码修改

- 0001-build-aux-config.guess.patch: 添加 HarmonyOS 系统识别分支（+11 行）
- 0002-configure.patch: 临时目录创建改 mkdir（HMDFS 兼容，+4/-4）
- 0003-src-main.cxx.patch: UDL 空格修复 + 两处尾随空格清理（+3/-3）

## 依赖版本

- libfltk/1.3.11（静态库，FLTK API 1.3，含 libx11/1.8.13 + xorgproto/2025.1 传递依赖）

## 验证结果

```bash
# 二进制 --version/--help 验证
comptext --version   # Version: 1.0.0（上游 configure 2.68 解析 comptext_PATCH=.1 丢失，属上游既有行为）
comptext --help      # 输出用法，含 --version 选项
# 上游测试（R51 穷尽核查）
make check           # check-am 空目标（上游无 TESTS/check_PROGRAMS 注册）
# test_package 断言（R34）
bash test.sh         # 2 项断言（--version 输出 Version / --help 列出 --version）
```

## 注意事项

- 版本号怪癖：上游 tarball 的 configure 由 Autoconf 2.68 生成，configure.ac 中
  `m4_define(comptext_PATCH, [.1])` 被 2.68 解析丢失，`--version` 输出 `Version: 1.0.0`
  而非 1.0.1（用 2.72 重新生成 configure 才输出 1.0.1）。保持上游原始 configure
  以最小补丁，PR 中如实说明。
- 上游无自带测试用例（源码包无 tests/、make check 空目标、GitHub 树无 test 路径），
  由 test_package 自研 2 项断言补齐功能覆盖（R51 证据链完整）。
- comptext 是 FLTK GUI 应用，沙箱无 X display，无法运行 GUI 主循环；
  --version/--help 在 GUI 初始化前退出（parse_args 内 exit(0)），可正常验证。
---

**编译结束**: 2026-09-10 18:09
**最终状态**: built
