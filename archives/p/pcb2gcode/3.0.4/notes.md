# pcb2gcode 3.0.4 适配笔记（HarmonyOS PC）

## 编译环境
- 构建系统: cmake（pcb2gcode 3.0.3 起由 autotools 迁移到 CMake；gerbv v2.13.0 亦为 CMake）
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 profile：os=OHOS 6.0, arch=armv8, cppstd=17）
- 状态: built

## 上游信息
- 上游: https://github.com/pcb2gcode/pcb2gcode tag v3.0.4（2026-04-05, commit a5604c4）
- tarball: https://github.com/pcb2gcode/pcb2gcode/archive/refs/tags/v3.0.4.tar.gz
- sha256: `46351d4b7479059becae064cc68f2d1d68d42ae314ff7a1d9a240c71a3c0c98c`（本地计算，上游无旁挂 checksum）
- pcb2gcode 是纯命令行工具：读入 Gerber(RS-274X) + Excellon 钻孔，输出机床 G-code。**自身无 GUI**。

## 依赖分析

| 依赖 | 上游要求 | ohpcd 现状 | 决策 |
|------|----------|-----------|------|
| Boost | >=1.60，program_options + Boost.Geometry(header-only) | boost/1.84.0 手编 program_options/filesystem/regex/iostreams，**无 Boost.Test** | 用 1.84.0；测试改 header-only Boost.Test |
| libgerbv | >=2.1.0（pkg-config） | **无 gerbv**；且 **无 GTK-2.0**（只有 gtk/3.24.38=GTK3） | vendor gerbv v2.13.0 源码 + 去 GTK 裁剪 |
| GEOS | 可选（geos-config，默认开） | geos/3.14.1（含 geos-config，但硬编码 /usr/local） | 用 3.14.1 + 配方生成 wrapper geos-config |
| glib | gerbv 需要 | glib/2.84.0.2（要求 zlib 1.3.1.1） | 用 2.84.0.2 |
| cairo | gerbv 需要（公共头暴露 cairo_t） | cairo/1.18.4（要求 zlib 1.3.1.1） | 用 1.18.4 |
| zlib | boost 1.3.1 / cairo 1.3.1.1 / glib 1.3.2 冲突 | 多版本 | `zlib/1.3.1.1, override=True` |
| GTK-2.0 | gerbv GUI + GDK 渲染 | **无** | 裁剪掉（GERBV_WITH_GUI=OFF） |

## GTK 裁剪方案（核心）

pcb2gcode 实际只调用 gerbv 的**解析 API**：`gerbv_create_project()`、`gerbv_open_layer_from_filename()`，以及读取
`project->file[0]->image->{info,netlist,aperture,state}` 与 `gerbv_aperture_t/net_t/layer_t/cirseg_t/...` 结构体常量。
不触碰任何 GDK / 绘图 / GUI 代码。

grep 实测的 GTK/GDK 耦合点：
- `gerbv.h` 只用到 `GdkColor`（公共结构的颜色字段）/ `GdkPixmap`（渲染声明）
- GDK **函数调用只出现在 `src/gerbv.c::gerbv_render_to_pixmap_using_gdk()` 一处**
- `attribute.c/callbacks.c/interface.c/main.c/project.c/render.c/table.c/draw-gdk.c/export-image.c/export-dxf.cpp` 属 GUI/GTK 导出，可整体剔除

因此：`GERBV_WITH_GUI=OFF`（新加选项）时不编译 GUI 应用与 GTK 源，只留解析库；GTK 相关 include 用最小本地类型替换。
**上游没有任何关闭 GUI 的开关**（任务提示词的预期与上游实际不符，以 tarball 为准）。

## 补丁清单

### pcb2gcode
| 补丁 | 内容 |
|------|------|
| 0001 | `tests/CMakeLists.txt`：GTK/GNOME 成像栈（glibmm-2.4/gdkmm-2.4/librsvg-2.0）由 REQUIRED 改可选，仅在齐全时注册 `gerberimporter_tests`；Boost.Test 不再要求已编译组件 |
| 0002 | `tests/*.cpp`（17 个）：`<boost/test/unit_test.hpp>` -> `<boost/test/included/unit_test.hpp>`（header-only Boost.Test） |

### gerbv（vendored）
| 补丁 | 内容 |
|------|------|
| 0001 | 顶层 CMake：GTK 改 `GERBV_WITH_GUI`（默认 OFF）、共享库改 `GERBV_BUILD_SHARED`；GUI 关闭时跳过 locale/man/desktop/test；显式 `pkg_check_modules(CAIRO REQUIRED cairo)`；`CMAKE_C_EXTENSIONS ON`（`-std=gnu2x`，恢复 POSIX 可见性） |
| 0002 | thirdparty：dxflib/tinyscheme 仅 GUI 需要，GUI 关闭时不构建 |
| 0003 | src CMake：GUI 关闭时剔除 draw-gdk.c/export-image.c/export-dxf.cpp 与 gerbv-app；静态库同时安装 gerbv.h |
| 0004 | gerbv.h：去掉 gtk/gdk include，GdkColor/GdkPixmap 用最小本地类型；**显式 include `<stdio.h>`**（原由 GTK 传递带入）；GDK 渲染声明加门控 |
| 0005/0006 | draw.h / drill_stats.h：`<gdk/gdk.h>` -> `<glib.h>` |
| 0007 | gerbv.c：去掉无用的 `<pango/pango.h>` 与 draw-gdk.h；GDK 渲染函数加 `GERBV_WITH_GDK_RENDER` 门控（不编译） |
| 0008 | libgerbv.pc.in：`Requires: glib-2.0 gtk+-2.0` -> `glib-2.0 cairo` |

## 配方要点
- `generate()`：`CMakeDeps`（boost/geos 走 `find_package(... CONFIG)`）+ `PkgConfigDeps`（glib/cairo/gerbv 走 pkg-config）；
  `PKG_CONFIG_PATH` 注入 generators 目录与 `${package_folder}/lib/pkgconfig`。
- `build()`：先以 `GERBV_WITH_GUI=OFF, GERBV_BUILD_SHARED=OFF` 子构建 gerbv（复用 conan_toolchain），
  再构建 pcb2gcode；最后 `ctest --output-on-failure --no-tests=error` 执行上游测试。
- geos-config 用配方生成的 wrapper（原脚本 `prefix=/usr/local` 不可重定位）。
- `package()`：清理 gerbv 的构建期产物（`lib/`、`include/`，libgerbv 已静态链入），并对 `bin/pcb2gcode` 重签名。
- 语言标准：**不要**降标；CMake 4.1.2 会把 C_STANDARD 23 映射成 `-std=gnu2x`（clang15 接受），降 C17 会导致 `[[fallthrough]]` 语法错误。

## 构建步骤

```bash
conan create archives/p/pcb2gcode/3.0.4 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```

## 测试结果（实测）

```
100% tests passed, 0 tests failed out of 32
```
- ctest 注册 122 项；实际执行 **32 项全部通过**
  - **16 个 Boost.Test 单元套件**（voronoi/eulerian_paths/segmentize/path_finding/tsp_solver/units/available_drills/
    options/autoleveller/common/backtrack/trim_paths/outline_bridges/geos_helpers/disjoint_set/segment_tree），
    共 **126 个测试用例**（`--list_content` 实测合计）
  - **16 个集成脚本测试**（上游标注 expect-failure 的用例：坏输出目录 / 坏输入 / 非法参数等），16/16 通过
- 90 项集成用例被**上游自身**按 Boost 版本门闸禁用（`tests/CMakeLists.txt` 要求 Boost==1.83 且 GEOS 与 ci.yml 钉版本一致；仓内为 Boost 1.84.0）
- `gerberimporter_tests`（栅格化对比 golden 图）需 GTK/GNOME 成像栈（glibmm-2.4/gdkmm-2.4/librsvg-2.0），
  HarmonyOS PC 制品仓无 gdkmm-2.4，裁剪后不注册

## test_package（消费者视角）
1. **鸿蒙特有**：校验交付二进制为 AArch64/LP64 小端 ELF64（EI_CLASS=2、EI_DATA=1、e_machine=0xB7）
2. `pcb2gcode --version`（纯 I/O 退出路径，输出 Boost/gerbv/GEOS 版本）
3. **真实转换**：对样例 KiCad Gerber（上游 `tests/data/gerbv_example/backtrack` 的 outline + F.Cu + millproject）
   执行 `pcb2gcode --config=millproject`，产出 2 个 `.nc`（outline + front）并校验含 G-code 运动指令

## 运行时
- 包只交付 `bin/pcb2gcode`（libgerbv 静态链入）+ `licenses/`（GPL-3.0 pcb2gcode + GPL-2.0 gerbv）
- 动态依赖：boost_program_options / geos / glib / cairo / zlib 等 conan 依赖（已由各自包签名）

## 踩坑记录
- `conan list "gtk"`（不带通配）会误报 "Recipe 'gtk' not found"；核查制品仓必须用 `gtk/*` 这类通配模式，否则会得出"GTK 不存在"的错误结论
- Conan 2 的**直接 require 不会覆盖传递依赖的精确版本**，解决冲突必须 `override=True`
- `CMake.test()` 底层是 `cmake --build --target test`，**不接受 ctest 参数**；要传 `--output-on-failure` 需直接调 `ctest`
- `conan_toolchain.cmake` 用普通 `set()` 强制 `CMAKE_INSTALL_PREFIX`，命令行 `-DCMAKE_INSTALL_PREFIX` 无效（子构建注意）
- 编辑文件与启动构建必须**串行**（本轮曾把两件事放进同一并行块，构建读到了旧配方）
