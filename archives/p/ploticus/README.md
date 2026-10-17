# ploticus

Ploticus 数据展示引擎（作者 Stephen C. Grubb）：从 ploticus 脚本渲染图表，输出
PS / EPS / SVG / SVGZ / PNG。上游官网 <https://ploticus.sourceforge.net/>。

## OHOS 适配要点

- 上游 2.42 是**手写 GNU Makefile** 工程（`src/Makefile`），无 configure/CMake；
  配方 `build()` 直接驱动 `make`（变量 `GD16H`/`GD16LIBS` 承载 libpng/zlib 路径）。
- HarmonyOS PC 的 `/tmp` 为只读挂载，上游把编译期宏 `TMPDIR`（`/tmp`）写死为临时目录，
  导致 `proc drawcommands` / `proc processdata` / cgi 诊断**静默失败**（`error 522`）。
  补丁 `0001-src-preliminaries.c.patch` 改为运行期选择临时目录
  （`$TMPDIR` → 编译期默认 → 当前目录，用探测文件判定可用性），不含平台宏。
- 构建面按上游默认：bundled GD16（PNG + SVGZ）、`-DNOX11 -DNOSWF`；
  交付 `bin/pl`、`lib/libploticus.a`、`include/libploticus.h`、`share/ploticus/prefabs/`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.42 | built | 上游套件 46 例逐条实测（44 通过 + 2 例上游自身缺陷）；test_package 7/7（含 3 个鸿蒙特有用例） |

详见 `2.42/README.md`、`2.42/notes.md`、`2.42/reports/test-report.md`。
