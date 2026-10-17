# xclicker 1.5.1 适配笔记

## 编译环境
- 构建系统: meson（上游根 Makefile 仅封装 meson+ninja，不参与实际构建）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS SDK，armv8 / aarch64-linux-ohos，libc++，Release）
- Conan profile: `ohos-aarch64`（host=build，native OHOS 编译）
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

配方内部（`generate()` → `build()` → `package()`）：
1. `PkgConfigDeps` 生成 gtk/x11/xi/xtst 及其传递依赖的 `.pc`
2. 从 `glib` 包复制 `glib-compile-resources` 到构建目录并签名（`gnome.compile_resources` 构建期需要）
3. `MesonToolchain` 生成 machine file，并注入
   `glib-compile-resources` / `ar` / `ranlib` / `pkg-config` 的绝对路径到 `[binaries]`
4. `meson configure` + `meson compile`
5. `package()` 拷贝 `build/src/xclicker` → `bin/xclicker` 并 OHOS 自签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Version conflict: libx11/6.4.0 vs libx11/1.8.13` | `libxi/1.8.3`、`libxtst/1.2.5` 的 recipe 固定拉 `libx11/6.4.0`；顶层声明 `libx11/1.8.13` 冲突 | X11 家族统一使用按 `.so` 主版本命名的同源组：`libx11/6.4.0` + `libxi/6.1.0` + `libxtst/6.1.0` |
| 2 | `meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]` | `MesonToolchain` 的 `[binaries]` 只写 `c`/`cpp`，meson 自行探测 clang 默认 `llvm-ar`/`llvm-ranlib`，而 conan 构建 env 的 `PATH` 不含 OHOS SDK bin | 解析 SDK bin（`tools.build:compiler_executables` 的 c 同目录）并把 `ar`/`ranlib`/`pkg-config` 绝对路径注入 machine file `[binaries]`，同时把 SDK bin 前置到构建 `PATH` |
| 3 | `gnome.compile_resources` 需要 `glib-compile-resources` | 制品仓 `glib` 包只对 `.so` 签名、不签名 `bin/` 工具；OHOS 下未签名 ELF 不可执行；Meson 的 `[binaries]` 也无该项 | 按 gtk/gdk-pixbuf 既有方案：从 glib 包复制 `glib-compile-resources` 到构建目录、OHOS 下 `binary-sign-tool` 自签名，并注入 `[binaries]` |

## 上游测试清点（R51）

**结论：上游确无自动化测试入口。** 清点证据：

| 清点项 | 结果 |
|--------|------|
| `tests/` 目录 | 不存在（`find . -type d -iname '*test*'` 无输出） |
| `meson.build` / `src/meson.build` `test()` 注册 | 无（仅 `project()` + `subdir('src')` + `executable()`） |
| 根 `Makefile` 测试目标 | 无 `test` / `check` 目标（仅有 `build/run/version/release/install/uninstall/deb/appimg/clean`） |
| 上游 CI workflow | 仅 `.github/workflows/docker.yml`、`release.yml`（打包发布，无测试 job） |
| 上游测试框架依赖 | 无（meson.build 未引用 gtest/ctest/check 等） |

真实测试入口即上游 `Makefile` 的 `release` 目标（`meson --buildtype release` + `ninja install`），
该目标是**构建**而非测试。因上游无测试用例，无 `make check` 统计可上报。
`test_package` 不替代上游测试统计 —— 本包按规范如实申报"上游无测试入口"。

## 鸿蒙特有测试（新增）

`test_package/test.sh` 与既有库测试不同，专门验证 OHOS PC（aarch64）平台产物属性与运行闭包：

- ELF magic（`od` 读魔数）
- ELF machine = AArch64
- 动态链接器 = `/lib/ld-musl-aarch64.so.1`（OHOS musl）
- 存在 `.codesign` 签名段（OHOS 可执行前提）
- `NEEDED` 含 `libgtk-3.so.0` / `libX11.so.6` / `libXi.so.6` / `libXtst.so.6`（OHOS 适配栈）
- 真实执行 `xclicker --help`：退出 0 且输出用法 —— 该命令在 `main()` 前加载全部
  `NEEDED` 动态库，等价于验证 OHOS 上运行期依赖闭包完整

实测结果：`test xclicker 1.5.1: 9 passed, 0 failed`（`reports/test-report.md`、
`reports/w3-local-ci.log`）。CI L1e 破坏性反向验证通过：
移走 `bin/` 后 test 失败，证明测试真实依赖被测包（非空壳）。

## 源码修改

无。本包未对上游源码打任何补丁（`patches: {}`）。

## 依赖版本

- gtk/3.24.43（含传递依赖 glib/2.84.0.1、cairo/1.18.4、pango/1.50.14.1.1、
  gdk-pixbuf/2.44.6.1、atk/2.38.0.1.1、fribidi/1.0.16、libepoxy/1.5.10 等）
- libx11/6.4.0
- libxi/6.1.0
- libxtst/6.1.0

## 验证结果

```bash
# 产物属性
$ llvm-readelf -h  bin/xclicker | grep -E 'Class|Machine'   # ELF64 / AArch64
$ llvm-readelf -l  bin/xclicker | grep interpreter          # /lib/ld-musl-aarch64.so.1
$ llvm-readelf -S  bin/xclicker | grep .codesign            # .codesign 存在
$ llvm-readelf -d  bin/xclicker | grep NEEDED \
    # libgtk-3.so.0 libgdk_pixbuf-2.0.so.0 libgio-2.0.so.0 libgobject-2.0.so.0
    # libglib-2.0.so.0 libX11.so.6 libXi.so.6 libXtst.so.6 libc.so

# 运行（conanrun 环境）
$ xclicker --help   # exit 0，输出 Usage: / --display=DISPLAY ...
```

## 注意事项

- 上游 `src/meson.build` 的 `executable()` 未声明 `install: true`，`meson install`
  不会安装可执行文件；配方在 `package()` 中显式拷贝。
- 沙箱/CI 无 X display：`xclicker` 无参数运行会以
  `Gtk-WARNING: cannot open display` 退出 1，因此运行期验证只做 `--help`。
- 本地网络对 `codeload.github.com` 限速严重；`source()` 在 `~/tmp/builds/xclicker-1.5.1.tar.gz`
  存在时直接复用（仍做 sha256 校验），CI 走官方源。
---

**编译结束**: 2026-09-24 20:25
**最终状态**: built
