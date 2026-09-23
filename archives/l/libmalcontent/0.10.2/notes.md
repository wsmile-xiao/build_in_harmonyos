# libmalcontent 0.10.2 适配笔记

## 编译环境
- 构建系统: meson（上游 endlessm/malcontent，tag Version_0.10.2）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built

## 版本说明
任务指定版本 0.14.0 在上游（endlessm/malcontent，GitHub tags 按 commit 时间排序）
不存在；上游 0.x 最新为 Version_0.10.2，按任务总纲版本替换规则采用 0.10.2。
制品仓无 malcontent/libmalcontent 任意版本适配记录，未重复适配。

## 编译步骤
1. `meson setup builddir -Dui=disabled -Dintrospection=disabled --prefix=...`
2. `ninja -C builddir`（79/79 目标全部通过）
3. `ninja -C builddir install`
4. `meson test -C builddir --print-errorlogs`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 1.12 报 `i18n.merge_file` 位置参数错误 | 上游用旧式位置参数语法，新版 meson 不接受 | 0001 patch：改为 input:/output: 关键字形式 |
| 2 | help 模块缺 itstool/yelp-build | OHOS 无 yelp 文档工具链 | 0003 patch：根 meson.build 条件化 help 子目录（工具不存在则跳过） |
| 3 | pam 模块缺 libpam/libpam_misc | OHOS 无 PAM 栈 | 0003 patch：根 meson.build 条件化 pam 子目录（系统库不存在则跳过） |
| 4 | GIR 生成需 gobject-introspection，与 polkit 的 glib 版本约束冲突 | GI 锁定 glib/2.84.0.1 vs polkit 锁定 glib/2.84.0 | 0002+0004 patch：introspection 选项化（默认 disabled，GIR 仅动态语言绑定用，C 库消费者不需要） |
| 5 | glib-2.0.pc 缺 glib_mkenums 等工具变量 | Conan PkgConfigDeps 生成的 .pc 不含工具变量 | conanfile generate() 从 glib 包原始 .pc 合并变量行（polkit 同款模式） |
| 6 | dbus-1.pc / polkit-gobject-1.pc 缺失 | dbus/polkit conan 包无 pkg_config_name/组件 | conanfile 生成别名并补齐 datadir/interfaces_dir/policydir 变量 |
| 7 | meson 报 `Could not detect Ninja` | OHOS SDK ninja 依赖 libc++_shared.so，未注入 LD_LIBRARY_PATH | conanfile _build_environment() 注入 llvm/lib/aarch64-linux-ohos 到 LD_LIBRARY_PATH |
| 8 | gdbus-codegen `No such file or directory` | 系统 /data/service/hnp/bin/gdbus-codegen shebang `#!/usr/bin/python3` 在 OHOS 不可用 | conanfile 生成 glib 包内脚本 wrapper，并写入 meson native file `[binaries] gdbus-codegen` |
| 9 | msgfmt `cannot locate ITS rules` | accounts-service policy 翻译需 polkit ITS 规则 | conanfile _build_environment() 注入 GETTEXTDATADIR 指向 polkit 包 share/gettext |
| 10 | libglib-testing 子项目不可用 | 上游 gitlab.gnome.org wrap 拉取不可达 + 0.1.0 meson.build 在新版 meson 下 static_library 不接受 version/soversion、docs 需 gtkdoc-scan | 修复后源码随 conan 包分发（exports_sources），wrap_mode=nodownload |

## 源码修改
- `patches/0001-accounts-service-meson.build.patch`：i18n.merge_file 关键字化
- `patches/0002-libmalcontent-meson.build.patch`：GIR 生成 options 化
- `patches/0003-meson.build.patch`：help/pam 模块条件化
- `patches/0004-meson_options.txt.patch`：新增 introspection 选项
- `subprojects/libglib-testing/`：测试专用库随包分发（含 meson 兼容修复）

## 依赖版本
- glib/2.84.0（polkit/127 锁定的 glib，其顶层 cpp_info 无 components）
- dbus/1.14.10（configure-time，取 interfaces_dir 变量）
- polkit/127（configure-time，取 policydir 变量 + ITS 规则）
- libglib-testing 0.1.0（测试专用，随包分发）

## 验证结果
- meson setup 通过（66 个构建目标 + libglib-testing 子项目）
- ninja 编译 79/79 全过，安装成功
- conan-verify G0-G4 + L2/L4/L5 全部通过
- 上游测试：signal-logger、app-filter/session-limits 非 bus 断言 33 项全过；bus 测试需会话 D-Bus（unix socket），OHOS 上绑定被拒（Operation not permitted），属系统级平台限制
- test_package 自研 5 组实质断言通过（app-filter builder/查询/serialize→deserialize 往返 + session-limits builder + 类型检查）

## 注意事项
- OHOS 环境不支持 unix domain socket 绑定（bus 测试无法运行，已在 PR 如实说明）
- UI 模块（libmalcontent-ui/malcontent-control）依赖 appstream-glib/flatpak（未发布），按可选特性关闭，核心库不受影响
- `subprojects/libglib-testing/` 为随包分发的**上游第三方源码**（gitlab.gnome.org/pwithnall/libglib-testing 0.1.0，LGPL-2.1+，含 COPYING），仅做 meson 新版本兼容修复（static_library 去 version/soversion、docs 条件化）；其中的 dbus-queue.c/signal-logger.c 等处 FIXME 注释为**上游原文**，非本 PR 模板残留，属第三方原文而非本 PR 改动
---

**编译结束**: 2026-09-15 17:24
**最终状态**: built
