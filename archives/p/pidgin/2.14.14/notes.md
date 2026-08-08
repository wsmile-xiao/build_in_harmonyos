# pidgin 2.14.14 — OpenHarmony PC 适配笔记

## 适配日期
2026-07-21

## 平台
- **目标**：OpenHarmony PC (aarch64-linux-ohos)
- **工具链**：gcc-aarch64-linux-gnu 11.4.0
- **Sysroot**：OpenHarmony DevEco Studio SDK native/sysroot (aarch64-linux-ohos)

## 编译策略

### 选择
仅编译 libpurple 核心库，不编译 pidgin GTK UI 和 finch ncurses UI。

### 原因
- GTK/X11 在 OH 平台不存在运行时（OH 使用 ArkUI + Wayland）
- ncurses 在 OH 上存在，但 finch 仍依赖 libpurple，与 GTK UI 互斥
- libpurple 是纯 GLib 库，跨平台兼容性最好

### 配置参数（已验证可编译）
来源：`build_pidgin.sh`（已纳入本归档）

```bash
./configure \
  --host=aarch64-linux-gnu \
  --disable-gtkui \
  --disable-consoleui \
  --disable-gstreamer --disable-vv \
  --disable-tcl --disable-tk --disable-meanwhile \
  --disable-avahi --disable-dbus --disable-gestures \
  --disable-screensaver --disable-sm \
  --disable-startup-notification --disable-gtkspell \
  --disable-idn --disable-perl --disable-mono \
  --disable-nss --disable-gnutls --disable-cyrus-sasl \
  --without-krb4 --disable-zephyr \
  --disable-doxygen-doc --disable-dot --disable-devhelp \
  --disable-pixmaps-install --disable-fortify \
  --disable-deprecation --disable-finch \
  --enable-nls=no \
  --enable-static --disable-shared
```

### 依赖项
- glib-2.0 >= 2.16.0（系统库，静态链接）
- libxml2（XML 解析）
- 不需要 GTK/X11/Perl/Python/Mono

## 已验证成果

| 项目 | 值 |
|------|-----|
| libpurple.a 大小 | 7.2 MB（静态库） |
| 测试程序大小 | 37.6 MB（test_pidgin） |
| qemu-aarch64 运行 | ✅ 通过 |
| libpurple 版本 | 2.14.14 |
| 输出验证 | `[OK] libpurple ARM64 binary is working on OHOS!` |

## 已知限制

1. **0 个协议插件**：当前只编译 libpurple 核心，没编译 prpl（IRC、Jabber、GG 等）
2. **静态链接 getpwuid 警告**：运行时不影响
3. **未在真机测试**：仅在 qemu-aarch64 上验证

## 后续工作

- [ ] 编译 prpl 协议插件（jabber/irc/gg）
- [ ] 编译 finch ncurses 客户端
- [ ] 真机测试
- [ ] 提取知识到 knowledge/graph/

## 编译命令回顾

```bash
# 已成功（脚本路径：D:\build_in_harmonyos\pidgin-build/）
./configure --host=aarch64-linux-gnu --disable-gtkui --disable-consoleui \
  --disable-gstreamer --disable-vv --disable-finch --enable-static \
  --disable-shared ... && make -j"$(nproc)"
```

## 知识沉淀

- 配置过程中不需要 source patch（configure 接受 `--host=aarch64-linux-gnu`）
- libtool 能正确识别 cross-compile
- glib 静态链接需要确保不引用 `/lib/x86_64-linux-gnu/libglib-2.0.so.0`

## Conan 配方（v3.0）

- 完整 `conanfile.py` + `conandata.yml` + `test_package/`
- 静态构建，`shared=False` 默认
- `package_info()` 设置 `cmake_file_name=pidgin`、`cmake_target_name=pidgin::pidgin`、`pkg_config_name=libpurple`
- `cpp_info.includedirs = ["include/libpurple"]`（pidgin 头文件位于 `include/libpurple/` 子目录）
- `cpp_info.requires = [...]` 列出 libpurple 真正链接的全部 6 个 glib 子组件（glib-2.0 / gobject-2.0 / gmodule-2.0 / gthread-2.0 / gio-2.0 / gio-unix-2.0）+ libxml2::libxml2（AI-review P2 2026-07-30；缺组件会导致下游消费者 `target_link_libraries(pidgin::pidgin)` 时出现 `undefined reference to g_object_* / g_module_* / g_thread_* / g_io_* / g_main_context_*`，conan-center glib 没有 `glib::glib` 聚合目标，必须显式列组件）

## test_package 设计

- CMakeDeps + CMakeToolchain（conan 2.x 标准）
- `test_pidgin.c` 包含 `<purple.h>` 并调用 `purple_core_get_version()`（R34 反空壳）
- 显式链接 glib components（`glib::glib-2.0`, `glib::gobject-2.0`, `glib::gio-2.0` 等）
- 显式添加 glib/libxml2 include paths（conan-center 2.72.4/2.10.3 components
  在 CMakeDeps 中不自动传播 INTERFACE_INCLUDE_DIRECTORIES，需手动加）

## 验证结果（2026-07-25）

| 项目 | 状态 |
|------|------|
| conan create（wsl-aarch64 profile） | ✅ PASS |
| G1 编译链接 | ✅ PASS |
| G2 静态 libpurple.a 产出 | ✅ PASS |
| test_package 编译 | ✅ PASS |
| test_pidgin ARM64 binary | ✅ PASS |
| qemu-aarch64 smoke test | ✅ PASS（"test pidgin 2.14.14: OK (libpurple version = 2.14.14)"）|
| L2 API 调用验证 | ✅ PASS（`purple_core_get_version()` 返回非空）|

## 编译结束
2026-07-25 — test_package 编译通过，R34 API 验证通过，PR-ready

## CI 特殊修复记录（ohos-aarch64 worker）

### getpass() ISO C99 问题（2026-08-04 Pass 6 + 2026-08-05 Pass 8）

- **问题**: CI worker(OHOS) clang 编译 `libpurple/example/nullclient.c:311` 报错
  `error: call to undeclared function 'getpass'; ISO C99 and later do not support implicit function declarations`
- **根因**: `getpass()` 是已被废弃/移除的 POSIX 函数，在 ISO C99+ 标准中不再可用。
  OHOS clang 严格遵循 C99 标准，不提供隐式声明。
- **修复方案**: 在 `conanfile.py build()` 中运行时 patch `nullclient.c`:
  1. 注入 `pidgin_getpass()` portable wrapper 函数（使用 `fgets` 读取 stdin）
  2. 移除 `extern char *getpass(...)` 声明（v2.14.14 实际无此声明）
  3. 将 `getpass(...)` 调用替换为 `pidgin_getpass(...)`
- **为什么不 patch configure**: pidgin configure 无 `--disable-example` flag
- **为什么不加 conandata.yml patch**: 这是运行时 patch(conanfile.py build() 内),
  不是 source patch，conandata.yml 仅存储 source patch

**Pass 8 修复 idempotency bug（2026-08-05）**:
- Pass 6 实际 CI 报 `pidgin_getpass undeclared`
- **真因**: idempotency check `if "pidgin_getpass" not in _nc_new` 在 `getpass→pidgin_getpass`
  regex 替换 **之后** — 替换后 _nc_new 已经有 pidgin_getpass 了, 跳过了 wrapper 注入
- **修复**: 改为 `if "static char *pidgin_getpass(" in _nc_text` 在 **原文件** _nc_text 上检测;
  wrapper 注入改为无条件（除已注入外）

**Pass 9 修复 wrapper 需要 stdio.h（2026-08-06）**:
- 修复 idempotency 后, wrapper 真的被插入了, 但放在 #include 之前
- CI 报 `fputs/fflush/fgets/strcspn/stderr/stdin/NULL` 全 undeclared
- **修复**: wrapper 自带 `#include <stdio.h>` + `#include <string.h>`, 用 `#ifndef`
  guard 保证 idempotency

### Pass 11: nullclient 链接 g_libintl_* 失败（2026-08-06）

- **问题**: `nullclient` 链接时 `ld.lld: error: undefined symbol: g_libintl_bindtextdomain`
  等等 7 个 `g_libintl_*` 符号
- **根因**: glib/2.84.0 编译时启用了 NLS, 其 static lib 内含 `g_libintl_*` 引用,
  这些符号由 libintl 提供。但 libpurple.a 是 archive, undefined weak symbol 允许,
  所以 libpurple.la 链通过。但 nullclient 是 executable, 必须全解析。OHOS musl
  没有 libintl.so / libintl.a（OHOS 用自带 i18n, 不用 gettext）。
- **修复**: patch `libpurple/example/Makefile`, 把所有 leading `$(MAKE) ...` 替换为
  `@$(TRUE)`, 让 example 变成 no-op. nullclient 只是开发者示例, 不需要 ship.
  `libpurple/example/` 目录本身保留 (downstream packaging scripts 还会 grep 它).

### PKG_CONFIG_PATH 全局污染修复（2026-08-05 Pass 7）

- **问题**: 原 `os.environ["PKG_CONFIG_PATH"] = ...` 在 `build()` 内直接赋值,
  build() 返回后依然存在,会污染同一 Conan 进程中的后续操作
  (test_package CMake configure, package() 打包等)。
- **修复方案**:
  1. **主路径**: `tc.environment().prepend_path("PKG_CONFIG_PATH", ...)`
     (conan 2.x 标准 env 注入方式, autotools.run 会写入 conanbuild.sh)
  2. **fallback**: `os.environ["PKG_CONFIG_PATH"] = ...` 仍保留作为
     ohpcd bundle 的兼容性回退, 但用 `try/finally` 包裹 build 主体,
     在 build() 退出前恢复原始 PKG_CONFIG_PATH 值
- **结果**: PKG_CONFIG_PATH 修改严格限定在 build() 调用期间, 不再污染其他阶段
---

**编译结束**: 2026-07-26 04:52
**最终状态**: published
