# pcb2gcode

Isolation routing and drilling G-code generator for PCBs：读入 PCB CAD 输出（Gerber RS-274X + Excellon 钻孔），
生成 CNC 机床可执行的 G-code（隔离铣削路径、钻孔、板框切割）。

## Homepage
https://github.com/pcb2gcode/pcb2gcode

## License
GPL-3.0-or-later（内置依赖 gerbv 为 GPL-2.0-or-later）

## Build System
CMake（上游 3.0.3 起由 autotools 迁移到 CMake）

## Dependencies
- Boost（program_options + Boost.Geometry，后者 header-only）
- libgerbv（Gerber/Excellon 解析；**制品仓无此包，源码 vendor 并去 GTK 裁剪后静态链接**）
- GEOS（多边形布尔/偏移，可选但默认启用）

## OHOS Adaptation
- pcb2gcode 本体无 GUI；GTK 依赖来自依赖库 gerbv。制品仓既无 gerbv 也无 GTK-2.0（只有 GTK3），
  因此 vendor gerbv v2.13.0 源码并按 `GERBV_WITH_GUI=OFF` 裁剪：不编译 GTK GUI 应用、GDK 渲染后端与 GTK 导出器，
  只保留 pcb2gcode 实际用到的 Gerber/Excellon 解析库，静态链入可执行文件
- 裁剪连带处理：gerbv.h 显式 include `<stdio.h>`、`CMAKE_C_EXTENSIONS ON`（`-std=gnu2x`，恢复 fileno 等 POSIX 声明）、
  gerbv CMake 显式声明 cairo、GDK 渲染函数以编译门控移除
- Boost.Test 改用 header-only 模式（制品仓 boost 无已编译的 unit_test_framework 组件）
- GEOS 探测：配方生成 wrapper `geos-config`（conan 包内脚本硬编码 `/usr/local` 不可重定位）
- 可执行文件按 HarmonyOS PC 要求重签名

## Versions

| Version | Status | Build Date |
| --- | --- | --- |
| 3.0.4 | built | 2026-09-24 |

### 3.0.4
- 上游测试（实测）：ctest 执行 32/32 通过 —— 16 个 Boost.Test 单元套件（126 用例）+ 16 个集成预期失败用例
- 消费者测试：`pcb2gcode --version` + 对样例 KiCad Gerber 真实执行 Gerber->G-code 转换（产出 outline/front 两个 `.nc`）
- 用法：
  ```bash
  pcb2gcode --config=millproject
  pcb2gcode --outline board-Edge.Cuts.gbr --front board-F.Cu.gbr --zwork=-0.15 ...
  ```
