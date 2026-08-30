# DRAFT-gtkmm-4.0-ohos-display-adaptation — GUI 绑定库无显示服务器环境的测试分类与验证边界

> **结构化数据**: [drafts/DRAFT-gtkmm-4.0-ohos-display-adaptation.kv](DRAFT-gtkmm-4.0-ohos-display-adaptation.kv)
> **严重度**: 🔴 blocking（测试门禁层面）| **分类**: platform|display|testing|binding|meson | **自动修复**: ⚠️ partial（测试排除可脚本化，运行验证需人工判定）
> **实例**: gtkmm 4.0.0（archives/g/gtkmm/4.0.0）| **可复用**: 任何依赖 GTK/GDK 显示后端的 *mm 绑定层（pangomm、cairomm、giomm GUI 类）及类似 GUI 绑定库
> **stemd**: DRAFT-gtkmm-4.0-ohos-display-adaptation（与 .kv 相同）

---

## 问题现象

OHOS PC 无原生 X11/Wayland/EGL 显示服务器。当底层 GUI 库（如 gtk4，Broadway-only 构建）**已经可编译可用**后，其 C++ 绑定层（gtkmm）的测试套件出现两类截然不同的行为：

1. **无显示 API 测试**可真实运行：如 `gdk_rgba_test`（Gdk::RGBA 颜色结构）在无显示环境直接 PASS。
2. **显示依赖测试**不可运行：`bitset_iterator_test`、`object_move_test`、`tree_model_iterator_test` 等调用 `gtk_init()` 的测试，运行期报
   ```
   (process:NN): Gtk-WARNING **: Failed to open display
   ```
   并 `exit status 1`。

同时，尝试为测试提供显示服务时，Broadway 服务器二进制（`gtk4-broadwayd`）在 OHOS 上因未签名/不可执行报 `Operation not permitted`（EPERM）——与 r3 中 `glib-compile-resources` EPERM 同源（OHOS ELF 签名/执行约束）。

## 根因

- OHOS PC 无任何原生显示后端；GTK4 在此平台仅启用 broadway(HTML5) 后端（E336 已记录构建层适配）。
- gtkmm 4.0.0 的 `tests/meson.build` 中「可执行测试」与「GUI 构建但不执行测试」由元组第 4 位（`GUI` 标志）与第 5 位（`execute` 标志）区分：`execute=true` 的 4 个测试中有 3 个仍会调用 `gtk_init()`，**display 标志与 execute 标志并不等价**——「可执行」≠「无需显示」。
- 无显示环境下 `gtk_init()` 初始化失败，测试进程以非零退出；这**不是库缺陷**，而是测试对显示服务器的真实依赖。
- 另外，`gtk_init()` 前置的 fontconfig 初始化在无 `/etc/fonts/fonts.conf` 的 OHOS 上也会失败（`Fontconfig error: Cannot load default config file`），需注入 `FONTCONFIG_FILE/FONTCONFIG_PATH` 后才能进入 GTK 初始化。

## 可复用方案

1. **按真实显示依赖对测试分类，而非按上游 execute 标志**：
   在绑定库的 `tests/meson.build` 中，把实际调用 `gtk_init()` / 创建窗口的测试标记为 `failing` suite：
   ```python
   if ex_name in ['bitset_iterator_test', 'object_move_test', 'tree_model_iterator_test']
     test(ex_name, exe_file, suite: ['failing'])
   else
     test(ex_name, exe_file)
   endif
   ```
   构建/CI 侧统一用 `meson test ... --no-suite=failing` 排除（与 glibmm 2.68.2 的 E215 `--no-suite=failing` 同款机制），并如实记录排除原因（无显示服务器）。

2. **为无显示 API 测试注入 fontconfig 配置**：
   在配方 `build()` 运行 meson test 前，把 fontconfig 包内的真实配置注入环境：
   ```python
   os.environ["FONTCONFIG_FILE"] = f"{fontconfig_pkg}/etc/fonts/fonts.conf"
   os.environ["FONTCONFIG_PATH"] = f"{fontconfig_pkg}/etc/fonts"
   ```
   无此步时即使无显示 API 测试也会因 fontconfig 默认配置缺失失败。

3. **新增无显示 API 鸿蒙特有探针测试（test_package）**：
   用不依赖显示服务器的公开 API（如 `Gdk::RGBA::set_rgba_u/get_red_u`、`Gdk::Rectangle`、`sigc++-3.0` 信号连接）构造真实调用测试，单独记录通过率。gtkmm 4.0.0 实测 7 断言 PASS：
   ```
   gtkmm probe: checks=7 PASS
   ```

4. **显示服务器前置条件的如实记录**：
   `gtk4-broadwayd` 在 OHOS 上不可执行（EPERM，签名约束）——记录为「提供 Broadway 服务或真实显示环境后方可执行显示依赖测试」，不得在无显示环境强行跑并写成失败/通过。

5. **测试统计边界**：
   15 个上游测试程序按「真实运行 / 不可运行（显示依赖，failing suite 排除）/ 构建但不执行（上游 execute=false）」三分类分别统计；排除必须给出真实原因，禁止把跳过写成 100% 通过。

## 验证证据（引用 r3/r4 真实日志）

| 证据 | 命令（绝对日志） | 退出码 |
|---|---|---|
| 上游 meson test：1 运行/3 failing suite 排除/11 构建不执行 | `meson test -v -C build-release --timeout-multiplier=16 --no-rebuild --no-suite=failing`（r3-evidence/build-and-test-results.log） | 0 |
| gdk_rgba_test 真实 PASS | 同上一日志（`Ok: 1 / Fail: 0`） | 0 |
| 3 个显示依赖测试 failing suite 排除 | r3-evidence/conan-create-r21-transport.log | 0 |
| 新增鸿蒙探针测试 7 断言 PASS | test_package `./test_probe` → `gtkmm probe: checks=7 PASS` | 0 |
| broadwayd 不可执行（EPERM） | r3 会话实测 `gtk4-broadwayd: Operation not permitted` | 126 |
| fontconfig 默认配置缺失 | r3 会话 `Fontconfig error: Cannot load default config file` | 1（修复前） |
| W3 全绿（含 JC pass） | r4-evidence/w3-local-ci-r4-transport.log（`JC_RESULT=pass`，Pass rate 100%） | 0 |

日志 SHA-256（节选）：
- build-and-test-results.log `be53d7429595cb06fd5bcea72e22e628b0f14493885c10600b551ca7c6d48fd2`
- conan-create-r21-transport.log `55eb907bba14367657a1a50d2f2363151e3d7717c908193f04905e6b1c8eeeed`
- w3-local-ci-r4-transport.log `dbea97e2d1808b5952fd8ad15086fa120840c7f9465ae3d72d9b1b268d633672`

## 不可适用场景

- 有真实显示服务器的环境（X11/Wayland/DRM 或 XComponent+EGL）：应按真实显示运行全部测试，不应套用 failing suite 排除。
- 上游测试本身不区分 display/execute 标志、且 `gtk_init()` 可无显示继续（如 GTK 允许 headless 初始化）的场景：需重新评估，不要照搬 `--no-suite=failing`。
- 纯非 GUI 库（无任何显示依赖）：本知识不适用。
- 不得把 goaccess 基线文件（archives/g/goaccess/1.10.2/ncurses-headers.tar.gz，r4 已证属无关历史基线，W3/JC 命中为基线噪声）写入本知识或归因于 gtkmm。

## OHOS 显示服务器前置条件

- 运行显示依赖测试需：可执行且已签名的 `gtk4-broadwayd`（或等价显示服务） + 浏览器/显示访问路径；当前 OHOS 上 broadwayd 因签名约束不可执行 → 显示依赖测试整体不可运行，只能分类排除并如实记录。
- 无显示 API 测试仅需：fontconfig 配置注入（FONTCONFIG_FILE/PATH）+ 无窗口 API 探针。

## 测试统计边界

- 分类：真实运行（gdk_rgba，1 项，PASS）/ 显示依赖不可运行（3 项，failing suite 排除，附真实原因）/ 构建但不执行（11 项，上游 execute=false）。
- 新增鸿蒙探针测试单独记录：`./test_probe` → checks=7 PASS（1/1）。
- 禁止：跳过显示测试后填 100%；把 broadwayd EPERM 写成构建失败；把基线噪声归因于当前库。

## 与 gtkmm 本次具体文件的关联边界

- 补丁：`patches/0003-failing-suite-for-display-dependent-tests.patch`（tests/meson.build 测试分类）、`patches/0002-gate-demos-on-build-demos.patch`（demos 门控）。
- 配方：`conanfile.py::_inject_fontconfig_env`（FONTCONFIG 注入）、`conanfile.py::build()`（`--no-suite=failing`）。
- 测试：`test_package/test.cpp`（无显示 API 探针，7 断言）。
- 本知识**不**覆盖：gtk4 库本身的 broadway 构建层适配（E336）、OHOS ELF 签名通用层（E077/E135）、goaccess 基线问题（r4 已排除）。
