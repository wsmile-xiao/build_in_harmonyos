# pcb (geda-pcb) — printed circuit board layout CAD

Interactive printed circuit board design tool (geda-pcb lineage).
This port builds the **batch HID** variant for HarmonyOS PC: all
headless export actions (-x gerber / bom / gcode / IPC-D-356 / ps ...)
work without a display or the GTK/Lesstif GUI stack.

**注意**：本包按"命令行工具 + 复杂 autotools 适配"处理（GUI HID 依赖
gtk/lesstif/X11 生态，未适配 OHOS；batch HID 提供完整导出/DRC 功能面）。

## 构建

- 系统：GNU autotools（git 归档无 configure，需 autogen.sh 引导）
- 依赖：glib-2.0（硬依赖，src/global.h 无条件 include）
- 工具链：automake/1.18 + intltool/0.51.0 (tool_requires)；autoconf 套件
  与 autopoint 由构建镜像提供
- 交叉/平台：--host=aarch64-unknown-linux-ohos（config.sub 补丁短路识别）

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 4.3.0 | built | batch HID；上游 3 文本导出场景 + 7 新增错误路径断言 |
