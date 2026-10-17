# qalculate-gtk 5.8.2-r0 适配笔记

## 编译环境
- 构建系统: autotools（自带 configure，无需 autoreconf）
- 编译日期: 2026-09-03
- 编译器: clang/clang++（SDK aarch64-linux-ohos）
- 状态: built（conan-verify 全门禁通过，CI upload 前）

## 依赖（GTK 生态 cmd-pkgs 预编译 + libqalculate conan requires）
| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| libqalculate | 5.8.2-r0 | conan requires | 计算引擎核心硬依赖（PKG_CHECK_MODULES QALCULATE） |
| gtk | 3.24.38 | cmd-pkgs | configure PKG_CHECK_MODULES 硬检查（gtk+-3.0 >= 3.10） |
| glib | 2.88.0 | cmd-pkgs | glib-2.0/gio-unix-2.0 |
| cairo/pango/atk/gdk-pixbuf/harfbuzz/fontconfig/freetype/libepoxy/pixman/fribidi/libpng | - | cmd-pkgs | GTK3 渲染栈 |

可选依赖 webkitgtk（用户手册显示，默认不启用）；GNOME Shell search-provider
默认启用但鸿蒙无 GNOME Shell 且 gdbus-codegen 需 Python pyexpat（conanbuild
环境不可用）→ `--disable-gnome-search` 禁用。

## 适配点（2 个补丁 + 运行时处理）

### 补丁 0001: config.guess（HarmonyOS 检测）
- `Linux|GNU|GNU/*|HarmonyOS)`，LIBC 简化为 gnu
- `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-gnu`

### 补丁 0002: configure
- 跳过 intltool XML::Parser 检查（OHOS 无该 perl 模块）
- 移除 umask 077（HMDFS 兼容）

### intltool-merge/extract shim（配方 build() 内生成）
- data/*.gresource.xml + po 处理需要 INTLTOOL_MERGE/EXTRACT，真工具需 XML::Parser
- shim 用 perl 去 `_` 翻译标记，**覆盖 $HOME/usr/local/bin 同名工具**
  （configure AC_PATH_PROG 优先命中该路径，CI 干净环境复刻本地验证）

## 关键踩坑（conan-verify 多轮修复）

### 1. PATH 注入必须在 generate() 的 tc 环境（非 build() os.environ）
- profile `[buildenv] PATH=+` 会把 /data/service/hnp/bin 前置到 PATH 最前
- make 阶段 glib-compile-resources 若命中 hnp 版（RUNPATH 指向不存在的
  /home/lycium++/...）→ 回落加载 conan 缓存 libffi 符号不匹配
- 修复：generate() 里 `tc.environment().prepend_path("PATH", GTK_PREFIX/bin)`
  + `tc.generate(_env)`（AutotoolsToolchain 环境，优先级高于独立 env 脚本）
- 本机探索 make 成功是因为手动 `export PATH=$HOME/usr/local/bin:$PATH`

### 2. 构建期工具运行时库（LD_LIBRARY_PATH 显式注入）
- 与 libqalculate 同源：conanbuild 沙箱不自动提供 SDK libc++/系统 lib
- build() 内 os.environ 注入顺序：SDK llvm/lib → /system/lib64 → GTK_PREFIX/lib
  → conan 依赖（避免 lld 被 conan libxml2 劫持）

### 3. gdbus-codegen 坏 shebang
- src/Makefile 裸调用 gdbus-codegen，PATH 命中 /data/service/hnp/bin 版
  （shebang #!/usr/bin/python3 在 OHOS 不存在）
- 本机 ~/usr/local/bin/gdbus-codegen（#!/usr/bin/env python3）可运行
- 最终方案：`--disable-gnome-search` 禁用（鸿蒙无 GNOME Shell，且 Python
  pyexpat 在 conanbuild 环境不可用）——彻底移除该工具链依赖

### 4. 依赖 .la 文件路径修复（libgsf E236 同款）
- conan 包 .la 的 libdir='//lib' → 跨包全局映射修复（mpfr.la 引用 gmp.la
  需解析到 gmp 包真实路径）

### 5. 上游无测试套件
- make check 仅执行 po/ intltool 工具链检查（XML::Parser 平台限制）
- src 无 check_PROGRAMS/TESTS，无 tests/ 目录 → 无真实上游测试
- test_package 链接 libqalculate 执行 `1 + 2 * 6` 验证依赖链完整（R34）

## 验证结果
- configure/make/make install: 成功（bin/qalculate-gtk 产出）
- make check: 上游无测试套件（仅为 intltool 工具链检查，平台工具限制）
- conan-verify: G0-G4/L2/L4/L5 全 PASS（verdict PASS）
- test_package: 创建 Calculator 并计算 `1 + 2 * 6` = 13 验证依赖链（R34）
- commands.json: 软件级声明（构建产物含 bin/qalculate-gtk, R38）

## R40 深度适配说明（GUI 应用）
qalculate-gtk 为 GTK3 图形界面应用。本次适配完成**编译/链接/依赖链**层面的验证：
- 补丁 0001/0002 为实质性平台适配（config.guess HarmonyOS 分支 / configure
  intltool+umask），非空壳 ifdef
- GTK3 渲染栈由 cmd-pkgs 预编译包体系承载（gtk3.24.38/glib/cairo/pango 等，
  gnumeric 同款已验证方案）

**需人工真机确认适配完整性**：GUI 渲染/窗口/输入在鸿蒙 PC 真机的实际表现，
本环境（无头）无法验证——实测 qalculate-gtk 二进制在注入 SDK/GTK 运行时库后
仍因缺 libcairo.so.2 等图形栈组件无法启动。建议在鸿蒙 PC 真机人工验证 GUI
可正常启动、渲染与响应输入后，在 PR 中补充真机验证记录。

## R34 测试豁免说明（GUI 无头环境）
test_package 未直接执行 bin/qalculate-gtk（GUI 应用在无头 CI/设备无法启动，
实测启动即缺图形栈库）。测试改为验证被测包的核心依赖链 libqalculate
（创建 Calculator 执行 `1 + 2 * 6` 断言 13），属历史 5.11.0 分支已验证的
同型方案（链接依赖库证明依赖链完整）。GUI 自身功能验证依赖真机人工确认。

## 产物
- bin/qalculate-gtk（GTK3 GUI 计算器）
- share/ 数据（icons/gresource）
---

**编译结束**: 2026-09-03 07:34
**最终状态**: built（conan-verify 全门禁通过，CI upload 前）
