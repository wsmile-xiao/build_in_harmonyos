# libpanelw 鸿蒙系统编译指南

libpanelw 是 ncurses 发行版中的 panel 重叠窗口管理组件（宽字符版本
`libpanelw`）。本文档记录其在鸿蒙（aarch64, OHOS）平台上以拆分包形式的
适配与验证。

## 版本索引

- libpanelw 6.6_p20260516：基于 ncurses 6.6 快照 20260516 的当前 Conan 配方

## 概述

panel 库在 curses 窗口之上提供面板（deck）管理：压栈/弹栈、上下排序、
隐藏/显示、窗口替换与用户指针等。上游并不单独发行 panel 源码包，panel
始终随 ncurses 源码树构建，因此本包从 ncurses 上游作者官方快照仓
（ThomasDickey/ncurses-snapshots，tag `v6_6_20260516`，`NCURSES_PATCH=20260516`）
取整树源码，仅构建并打包 panel 组件。

## 与 ncurses 包的关系（拆分包契约）

- 本包 `requires ncurses/6.6`：编译期在树内静态链接 ncursesw 以完成
  panel 构建，但**不打包**任何 ncurses 核心产物。
- 包内仅含三件产物：`include/panel.h`、`lib/libpanelw.a`、
  `lib/pkgconfig/panelw.pc`（prefix 重定位）。
- 消费者通过 Conan 目标 `libpanelw::libpanelw` 使用；核心
  `ncurses::ncurses`（libncursesw.a）由 ncurses 包传递提供。

## ⚠️ 重要风险提示

panel 属 ncurses 家族，共享库风险与 ncurses 相同：用户编译的
`libpanelw.so`/`libncursesw.so` 会劫持系统同名库导致系统组件（如依赖
curses 的 shell）崩溃。本包强制静态（`--without-shared`），配方在
`configure()` 拒绝 `shared=True`，并在打包后校验产物中不存在 `.so`、
不混入 ncurses 核心静态库。

## 平台适配要点

- 静态编译：`--disable-shared --enable-static --without-shared --with-normal`
- 宽字符：`--enable-widec` 生成 `libpanelw`（依赖 `libncursesw`）
- 元数据：`--enable-pc-files` 生成 `panelw.pc`，打包时重定位 prefix
- 平台补丁（与 ncurses 6.6 同源，按快照实测适配）：
  - `0001` Toybox `expr` 无法计算复合表达式时改选 GNU 实现
  - `0002` 允许 `lib_mvcur` 测试在静态链接下覆盖其存根符号（快照行号已适配）
  - `0003` HMDFS 下经所选 shell 执行生成的头文件安装器
  - `0004` `config.guess` 识别原生 HarmonyOS（`aarch64-unknown-linux-ohos`）
- OHOS 构建在 `/data/storage/el2/base` 下的任务私有构建根内进行
  （HMDFS 绝对路径不进入生成规则），`ac_cv_func_setfsuid=no` 规避
  未实现 syscall 探针。

## 验证合同（6.6_p20260516）

- 上游构建：`make -j1`，`test/programs` 全部 86 项入口构建成功
  （含 panel 消费者 `demo_panels`）
- 上游检查：`make -j1 check` 通过（含逐头文件独立编译检查）
- 消费者：`test_panel_consumer` 13 项 panel API 断言经
  `libpanelw::libpanelw` 全过；`panelw.pc` pkg-config 消费者经
  `-Wl,-t` 溯源确认选中本包 `libpanelw.a` 与 ncurses 包
  `libncursesw.a`，且不链接任何 curses 共享库
- 详见 `6.6_p20260516/manifest.yaml`、`6.6_p20260516/notes.md` 与
  `6.6_p20260516/test_package/MANIFEST.yml`
