# gtkmm 4.0.0.1 适配笔记 (r02 harfbuzz 修复版本消费核验)

## 编译环境
- 构建系统: meson（官方 release tarball，meson dist 产物自带 untracked/ 预生成绑定）
- 编译日期: 2026-09-11
- 编译器: clang/clang++ 15 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS PC (OHOS aarch64, Broadway-only 图形配置)
- 状态: built

## 任务背景
本版本 (4.0.0.1) 为仓库 .1 修复版本基线，对应官方 gtkmm-4.0.0.tar.xz
（gnome 官方 4.0 系列仅 4.0.0/4.0.1/4.0.2，无 4.0.0.1 tarball；版本号递增
表示 OHOS 修复基线，惯例同 pango 1.50.14.1.1）。核心变更：整图
harfbuzz override 到 ohpcd 已发布的 14.2.0.1.1.2，核验 gtkmm 可解析、
可构建、可消费该新修复依赖版本，不回退 14.2.0.1。

## 编译步骤
- conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
- meson 配置项沿用 4.0.0：maintainer-mode=false（无需 gmmproc 生成）、
  build-documentation=false、build-demos=false（epoxy 仅 demos 需要）、
  wrap_mode=nodownload、default_library=shared
- 测试：meson test -v -C <build> --timeout-multiplier=16 --no-rebuild --no-suite=failing
  （排除 3 个显示服务器依赖测试，同 4.0.0）

## 依赖图关键点（r02）
- gtk4/4.22.4 发布二进制 requires harfbuzz/14.2.Z（范围），override 到
  14.2.0.1.1.2 不破坏其 binary 匹配
- pango/1.56.4 钉 harfbuzz/14.2.0.1，override 统一到 14.2.0.1.1.2
- harfbuzz/14.2.0.1.1.2 远程二进制绑定 glib/2.84.0.1 共享链 + freetype/2.14.Z，
  与 gtkmm 4.0.0 既有 glib/2.84.0.1.1 override 兼容
- glib2/2.88.0#aa5b8908、glib/2.84.0.1.1、zlib/1.3.1.1、fontconfig/2.18.1.1
  override 沿用 4.0.0（R2/R8 修复）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方无 4.0.0.1 tarball | GNOME 4.0 系列仅 4.0.0/4.0.1/4.0.2 | 仓库 .1 修复版本惯例：源码 = 官方 4.0.0 tarball + patches，conandata 注明映射 |
| 2 | 依赖图中 harfbuzz 版本分裂 | gtk4 钉 14.2.0.1、pango 1.56.4 钉 14.2.0.1、pango 1.50.14.1.1 用 14.2.0.1.1.1 | gtkmm 配方 override 到 14.2.0.1.1.2（ohpcd 已发布），整图统一 |

## 依赖版本
- harfbuzz/14.2.0.1.1.2（r02 核心核验对象）
- glibmm/2.68.2, gtk4/4.22.4, cairomm/1.18.0, pangomm/2.50.1, gdk-pixbuf/2.44.6
- glib/2.84.0.1.1 (shared, override), glib2/2.88.0#aa5b8908 (override),
  zlib/1.3.1.1 (override), fontconfig/2.18.1.1 (override)

## 验证结果
（详见 reports/ 证据日志）
- conan create: 见 .ci-result.json
- 上游测试台账：见双口径台账（source_declared/configured/executed_passed）
- OHOS 专项测试 / test_package / 消费者验证：见证据日志

## 注意事项
- harfbuzz 是 gtk4 传递依赖（经 pango），gtkmm 自身 meson 不直接
  dependency('harfbuzz')；核验证据以依赖图解析 + 消费者链接为准
- 3 个 GUI 测试（bitset_iterator/object_move/tree_model_iterator）依赖显示
  服务器，OHOS Broadway 无窗口系统，以 --no-suite=failing 排除

**编译结束**: 2026-09-11
**最终状态**: built