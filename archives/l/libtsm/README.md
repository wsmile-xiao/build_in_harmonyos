# libtsm (TSM) — Terminal-emulator State Machine

libtsm 是一个终端模拟器状态机库：它把终端应用输出的字节流解析成屏幕状态，
实现 DEC VT100–VT520 兼容的转义序列、屏幕/滚动缓冲、字符集、鼠标与键盘编码。
它不包含任何 UI，终端模拟器（最典型的是 kmscon）在它之上实现渲染与输入。

本仓库适配的是官方仓库 **kmscon/libtsm**（libtsm 起源于 David Herrmann 的 kmscon
项目，现随 kmscon 走官方组织）。所适配的 **v4.3.0** tag 中提供多套配色（vga /
solarized / base16 / soft-black）、24 位真彩色、下划线与斜体渲染、Ctrl+方向键等特性
（均在 `src/tsm/` 实测存在）；官方线此后已演进到更高版本。

## 功能概述

- VT100–VT520 转义序列状态机（`tsm_vte_*`）：CSI/OSC/ESC 解析、光标寻址、
  擦除、插入/删除、滚动区域、alternate screen、DEC 私有模式；
- 屏幕缓冲区（`tsm_screen_*`）：单元格属性、宽字符（CJK）宽度、制表位、
  滚动缓冲（scrollback）、屏幕绘制回调 `tsm_screen_draw()`；
- 选择与复制（`tsm_screen_selection_*`）：按单元格/词/行选择并输出 UTF-8 文本；
- 键盘与鼠标编码（`tsm_vte_handle_keyboard()` / `tsm_vte_handle_mouse()`）：
  普通模式与 DEC 光标键应用模式、X10/1002/1003/1006/1016 鼠标追踪；
- Unicode 辅助（`tsm_ucs4_*`）、符号表、内部哈希表与 wcwidth 实现。

## OHOS 适配

- **构建系统**：上游 meson（>= 1.1），配方用 `MesonToolchain` + `Meson`
  （`-Dtests=false -Dgtktsm=false -Dextra_debug=false`）。工程本身不含任何
  平台探测脚本，OHOS aarch64 + clang 15 + musl 下**零补丁**通过。
- **xkbcommon（可选依赖）**：上游 `dependency('xkbcommon', required: false)`
  只用于 keysym 翻译；ohpcd 未发布 xkbcommon，于是走上游自带的
  `external/xkbcommon/xkbcommon-keysyms.h` 回退（上游明确支持的路径），
  不需要补丁，也不需要把 xkbcommon 带进依赖链。
- **产物形态**：上游只声明 `shared_library('tsm')`，产出
  `libtsm.so.4.3.0`（SONAME `libtsm.so.4`，符号版本 LIBTSM_3/LIBTSM_4），
  并安装 `include/libtsm.h` 与 meson 生成的 `lib/pkgconfig/libtsm.pc`。
  没有静态变体，因此配方的 `shared` 选项默认 `True`，请求 `False` 时明确
  报 `ConanInvalidConfiguration`，不静默产出 `.so`。
- **上游测试范围**：`test/meson.build` 的 7 个 `check` 套件通过
  `declare_dependency(..., sources: libtsm_srcs)` 把库源码直接编进测试二进制，
  验证的是源码树而不是交付的 `.so`；交付物由 `test_package` 消费者测试与
  设备端 dlopen/字节一致性补测覆盖（见 `4.3.0/notes.md`）。
- **已知差异**：无平台条件编译补丁；`xkbcommon` 缺失时键位翻译使用上游内置
  keysyms 头，行为与链接 xkbcommon 时一致（同为 X11 keysym 数值）。

## 依赖关系

- 编译依赖：无必选依赖；`xkbcommon` 可选（本适配未启用）。
- 运行依赖：仅 libc（`readelf -d` 实测 `DT_NEEDED: libc.so`）。
- 测试依赖：`check`（仅上游测试用，不进包依赖链）。

## 参考资料

- 上游仓库（官方）：https://github.com/kmscon/libtsm
- 典型消费者：kmscon（https://github.com/kmscon/kmscon）
- 本仓库配方：`archives/l/libtsm/4.3.0/conanfile.py`
