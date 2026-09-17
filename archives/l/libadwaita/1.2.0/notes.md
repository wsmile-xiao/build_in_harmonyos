# libadwaita 1.2.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (aarch64-linux-ohos, llvm 15.0.4)
- 状态: built

## 编译步骤

```bash
# conan 配方驱动（Meson 交叉构建 OHOS aarch64）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 生成环境：PkgConfigDeps 提供 gtk4/glib-2.0/gio-2.0/fribidi 的 .pc；
# MesonToolchain 项目选项：-Dintrospection=disabled -Dvapi=false
#   -Dgtk_doc=false -Dexamples=false -Dtests=true
```

## 依赖版本

| 依赖 | meson dependency() 名 | conan 包 | 版本要求 |
|------|----------------------|----------|----------|
| glib | glib-2.0 / gio-2.0 | glib/2.84.0.1.1 (shared=True, override) | >= 2.66 |
| gtk4 | gtk4 | gtk4/4.22.4 (transitive headers/libs) | >= 4.5.0 |
| fribidi | fribidi | fribidi/1.0.16 (transitive) | 任意 |
| zlib | (图内统一) | zlib/1.3.1.1 (override) | - |
| fontconfig | (图内统一) | fontconfig/2.18.1.1 (override) | - |

> glib 必须对齐 gtk4 图内固定的 2.84.0.1.1 shared=True，并传递 zlib/fontconfig
> override，避免与 pango/harfbuzz/cairo 链的版本冲突（承接 gtk4 配方既定图）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 内部 urllib 下载 gitlab.gnome.org 卡死 | 环境网络对 python urllib 直连不稳 | curl 预下载 tarball 到 $TMPDIR/builds/，init-build 复用 |
| 2 | conan-init 生成 Autotools 模板 | 默认按 URL 猜测构建系统 | 重写为 Meson 配方（MesonToolchain + PkgConfigDeps） |
| 3 | MesonToolchain 不写 ar/ranlib | 交叉工具链不在 PATH | generate() 用绝对路径探针绑定 ar/as/strip/nm/ranlib |

## 源码修改

无补丁（patches/ 为空）。OHOS 适配全部通过配方选项完成：
- introspection/vapi/gtk_doc/examples 禁用（无 GI/Vala/显示后端需求）
- tests=true 保留上游 37 个测试程序编译

## 上游测试枚举台账（双口径）

源码测试目录：`tests/`（37 个独立测试程序，全部注册于 `tests/meson.build` 的
`test_names` foreach → `test(test_name, t)`）

- **source_declared_total** = 37（官方 tag 源码 tests/meson.build 声明的独立可执行测试程序）
- **configured_executable_total** = 37（OHOS 配置 `-Dtests=true` 全部实例化，无条件分支排除）
- 用户测试源内 g_test 注册用例 = 178 条（g_test_add_func/data_func/add，含
  test-easing 的 13 个 easing 枚举数据驱动用例）

| # | 测试程序 | 源码文件 | g_test 注册数 | 类别 |
|---|----------|----------|--------------|------|
| 1 | test-about-window | tests/test-about-window.c | 1 | 独立上游用例 |
| 2 | test-action-row | tests/test-action-row.c | 6 | 独立上游用例 |
| 3 | test-animation-target | tests/test-animation-target.c | 2 | 独立上游用例 |
| 4 | test-animation | tests/test-animation.c | 1 | 独立上游用例 |
| 5 | test-application-window | tests/test-application-window.c | 1 | 独立上游用例 |
| 6 | test-avatar | tests/test-avatar.c | 3 | 独立上游用例 |
| 7 | test-bin | tests/test-bin.c | 1 | 独立上游用例 |
| 8 | test-button-content | tests/test-button-content.c | 5 | 独立上游用例 |
| 9 | test-carousel-indicator-dots | tests/test-carousel-indicator-dots.c | 1 | 独立上游用例 |
| 10 | test-carousel-indicator-lines | tests/test-carousel-indicator-lines.c | 1 | 独立上游用例 |
| 11 | test-carousel | tests/test-carousel.c | 7 | 独立上游用例 |
| 12 | test-combo-row | tests/test-combo-row.c | 3 | 独立上游用例 |
| 13 | test-easing | tests/test-easing.c | 13 | 独立上游用例（枚举数据驱动） |
| 14 | test-entry-row | tests/test-entry-row.c | 2 | 独立上游用例 |
| 15 | test-expander-row | tests/test-expander-row.c | 6 | 独立上游用例 |
| 16 | test-flap | tests/test-flap.c | 13 | 独立上游用例 |
| 17 | test-header-bar | tests/test-header-bar.c | 6 | 独立上游用例 |
| 18 | test-leaflet | tests/test-leaflet.c | 5 | 独立上游用例 |
| 19 | test-message-dialog | tests/test-message-dialog.c | 14 | 独立上游用例 |
| 20 | test-password-entry-row | tests/test-password-entry-row.c | 1 | 独立上游用例 |
| 21 | test-preferences-group | tests/test-preferences-group.c | 3 | 独立上游用例 |
| 22 | test-preferences-page | tests/test-preferences-page.c | 4 | 独立上游用例 |
| 23 | test-preferences-row | tests/test-preferences-row.c | 2 | 独立上游用例 |
| 24 | test-preferences-window | tests/test-preferences-window.c | 2 | 独立上游用例 |
| 25 | test-split-button | tests/test-split-button.c | 8 | 独立上游用例 |
| 26 | test-squeezer | tests/test-squeezer.c | 8 | 独立上游用例 |
| 27 | test-status-page | tests/test-status-page.c | 3 | 独立上游用例 |
| 28 | test-style-manager | tests/test-style-manager.c | 5 | 独立上游用例 |
| 29 | test-tab-bar | tests/test-tab-bar.c | 7 | 独立上游用例 |
| 30 | test-tab-view | tests/test-tab-view.c | 29 | 独立上游用例 |
| 31 | test-timed-animation | tests/test-timed-animation.c | 7 | 独立上游用例 |
| 32 | test-toast-overlay | tests/test-toast-overlay.c | 2 | 独立上游用例 |
| 33 | test-toast | tests/test-toast.c | 11 | 独立上游用例 |
| 34 | test-view-switcher-bar | tests/test-view-switcher-bar.c | 2 | 独立上游用例 |
| 35 | test-view-switcher | tests/test-view-switcher.c | 2 | 独立上游用例 |
| 36 | test-window-title | tests/test-window-title.c | 2 | 独立上游用例 |
| 37 | test-window | tests/test-window.c | 1 | 独立上游用例 |

合计：37 个独立上游测试程序 / 178 个 g_test 注册用例。
样例（tests/ 下框架内部文件）、benchmark、fixture、脚本均不在此列（本包
tests/ 目录无样例/基准/脚本，全部为独立测试程序）。

## 上游测试实际运行结果（双口径台账）

运行环境：构建产物（OHOS aarch64）+ 本机执行 `meson test -C build-release`
（G_TEST_SRCDIR/G_TEST_BUILDDIR/GSETTINGS_BACKEND=memory/GTK_A11Y=none）。

- **source_declared_total** = 37（meson 注册的独立测试程序）
- **configured_executable_total** = 37（`-Dtests=true` 全部实例化，无条件排除分支）
- **executed** = 37/37（全部实际执行尝试）
- **executed_passed_total** = 0
- **executed_failed_total** = 37（全部 `killed by signal 6 SIGABRT`）
- **uninstantiated** = 0

失败首错（37 个测试一致）：
```
Gtk-WARNING **: Failed to open display
Signal 6 (core dumped)
```
根因：37 个测试全部调用 `gtk_test_init()` / `adw_init()`（adw_init 内部调
gtk_init()），需要连接显示服务器。OHOS PC 无 X11/Wayland/EGL 窗口系统
（gtk4 适配为 Broadway-only 后端），故无 display 可连。

运行时环境恢复尝试（如实记录）：
1. Fontconfig 缺失 → 设置 FONTCONFIG_FILE/FONTCONFIG_PATH（fontconfig 包
   内 fonts.conf）→ 仍失败于 display（fontconfig 只是前置告警，非崩溃首因）
2. Broadway 无头后端 → `gtk4-broadwayd :0` 启动报 `Operation not permitted`
   （gtk4 包内工具二进制同样缺有效 codesign，与 glib 工具一致），无法提供
   Broadway display 服务器 → display 阻塞无法在 OHOS 本机恢复

阻塞归属：真实平台限制（OHOS 无显示服务器 + gtk4 Broadway 后端需要
broadwayd 服务器进程），非当前库适配缺陷。恢复条件：OHOS 设备存在可用
display 服务器（X11/Wayland/Broadway）或 gtk4-broadwayd 工具完成签名后可
以本机重跑全部 37 个上游测试。测试已全部编译成功（configured=37），仅
运行阶段受 display 阻塞，计入分母不计通过。

## 鸿蒙专项测试

test_package/test.c — 仅通过公开头 `<adwaita.h>` 和公开 API：
- `adw_get_major/minor/micro_version()` 运行时版本断言（== 1.2.0）
- `ADW_MAJOR/MINOR/MICRO_VERSION` 编译期宏断言
- `ADW_CHECK_VERSION(1,2,0)` API 可用性宏
- `adw_is_initialized()` 初始化前必须为 FALSE
> OHOS 无显示服务器，adw_init() 内部调 gtk_init() 需 display，故专项测试
> 故意不调用 adw_init()，验证库链接与导出 API 的真实可用性（同 gtk4 口径）。

## 消费者用例

test_package/test.c 同时作为消费者用例：模拟上层业务组件，仅通过库已安装的
公开头文件（`<adwaita.h>`，安装于 include/libadwaita-1）与公开 API
（adw_get_*_version / adw_is_initialized）编译、链接（libadwaita-1）并运行，
验证第三方使用者可正常消费。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 配方（requirements/generate/package_info） |
| conandata.yml | 官方源 URL + SHA-256 ab0030434af58ae0a01e6979acc56f7e88cc43ca5a2bbd53da9a3b7707403687 |
| test_package/ | 消费者/鸿蒙专项测试（test.c + meson.build + conanfile.py + MANIFEST.yml） |
| manifest.yaml | 版本元数据 |

## 注意事项

- 库类型（仅 libadwaita-1.so + 头文件 + pkgconfig），无 CLI 产物 → 不需要 commands.json
- 共享库安装后需 binary-sign-tool -selfSign（OHOS XPM dlopen 权限要求）

## 知识候选台账与查重（W5/knowledge-reuse-governance）

执行范围：本轮适配的真实错误 → 根因 → 修复 → 验证 → 适用范围，逐项四范围
查重（index.tsv 正式条目 / knowledge/doc / knowledge/graph kv / drafts 草稿）。

| # | 知识候选（错误→根因→修复） | 验证 | 适用范围 | 查重结果 | 既有条目覆盖 | 新增差异 |
|---|------------------------------|------|----------|----------|--------------|----------|
| K1 | GNOME Meson 项目 gnome.compile_resources 需 gio-2.0.pc 携带 glib_compile_resources 等工具变量，PkgConfigDeps 生成 .pc 缺失 → "Could not get pkg-config variable"；修复：generate() 补工具变量 + datadir | conan create G2 实测通过 | 所有用 PkgConfigDeps + GNOME Meson 的库（gtk4 等） | 部分覆盖 | E527 (broadway-backend-native-tools-wrapper 提及 glib-mkenums 等工具变量)、gtk4 配方同款处理 | 无实质新增：gtk4 配方已有同款 .pc 工具变量补全模式，本轮为同模式复用 |
| K2 | MesonToolchain 不把 ar/ranlib 写入 native 文件 → meson 探测裸 llvm-ar 失败；修复：generate() 绝对路径注入 | conan create G2 实测通过 | 所有 Conan+Meson OHOS 交叉构建 | 已有条目覆盖 | E296 (complete-meson-cross-machine)、E481 (shared-only-meson-toolchain-with-llvm-tools)、E012 (llvm-ar not found) | 无实质新增：gtk4 配方同款 _inject_meson_archiver 模式 |
| K3 | glib 包 bin 工具（glib-compile-resources）OHOS 上因签名失效报 Operation not permitted / 缺 LD_LIBRARY_PATH 报 Error loading shared library；修复：重签名 + PATH/LD_LIBRARY_PATH prepend | conan create G2 实测通过 | 所有消费 glib/2.84.0.1.1 shared 的 GNOME 生态库 | 已有条目覆盖 | E077 (ELF 重签名四步流程)、E135 (ELF signature/dynamic linker)、E471 错误特征含 gtk4-broadwayd Operation not permitted | 无实质新增：gtk4 配方同款 _prepend_glib_bin_to_path 模式 |
| K4 | fribidi.h 位于 include/fribidi 子目录，PkgConfigDeps 生成的 fribidi.pc 缺 -I${includedir}/fribidi → #include <fribidi.h> not found；修复：Cflags 补子目录 | conan create G2 实测通过 | 所有消费 fribidi 的库 | 已有条目覆盖 | E075 (pkg-config/include path 环境类)、gtk4 配方同款 | 无实质新增 |
| K5 | libadwaita stylesheet 构建需 sassc，git subproject clone (github) 失败；修复：ohpcd 已发布 sassc/3.6.2 以 tool_requires 提供 | conan create G2 实测通过 | 所有需要 sassc/libsass 的 GNOME 库 | 未命中专用条目（general tool_requires 模式属 R18 既有原则） | 无专用 E 条目；R18 预编译优先原则 | 工具链 tool_requires 场景；跨库复用价值一般，R18 已覆盖 |
| K6 | GTK/GNOME 测试在 OHOS 无显示后端全量 Failed to open display（37/37 SIGABRT），gtk4-broadwayd 签名约束不可执行；修复：如实分类为显示依赖阻塞，不伪造通过 | meson test 37/37 实测 | 所有 GUI/GTK 生态库测试分类 | 已有条目覆盖 | E471 (display-test-classification-and-no-display-api-probes) 错误特征与本轮 100% 吻合 | 无实质新增：本轮测试分类口径与 E471 完全一致 |

## 路径判断

- **K1-K4、K6**：四范围查重全部命中既有条目（E296/E481/E012/E077/E135/E075/E471）或
  gtk4 已入库同款模式，无新增跨库差异 → **reuse_existing**
- **K5**：sassc tool_requires 属 R18 预编译优先通用原则，无独立知识价值 →
  **path_a_no_knowledge**
- 路径决定：**path_a_no_knowledge**（常规基础适配，知识库已有解决方案，本轮无
  需新建知识草稿；已核验无 exact/causal duplicate 未命中项，无 path B 候选）
- 关系字段：K1-K6 均属 `similar_to` 既有条目（E296/E481/E077/E135/E471），无
  `caused_by`/`prerequisite_of`/`conflicts_with` 新增关系
---

**编译结束**: 2026-09-15 22:07
**最终状态**: built
