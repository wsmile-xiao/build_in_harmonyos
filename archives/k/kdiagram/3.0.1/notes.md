# kdiagram 3.0.1 适配笔记（OHOS arm64）

## 1. 上游事实（全树实测核实）

- 上游：https://invent.kde.org/graphics/kdiagram（KDE 图表库，独立发布线，非 Frameworks）。
- tarball（官方单条 URL，实测可达）：https://download.kde.org/stable/kdiagram/3.0.1/kdiagram-3.0.1.tar.xz
  sha256=4659b0c2cd9db18143f5abd9c806091c3aab6abc1a956bbf82815ab3d3189c6d（693440 字节）。
  注意：stable/kdiagram/3.0.1/src/ 子目录路径 404，tarball 直接在 stable/kdiagram/3.0.1/ 下；
  invent.kde.org/-/archive/3.0.1/ 归档路径同样 404（实测）。
- **世代判定**：3.0.1 是 Qt6/KF6 世代（QT_REQUIRED_VERSION "6.5.0"、KF_MIN_VERSION "5.245.0"）。
  任务卡原 Qt5 依赖清单（qt5-qtbase/kcoreaddons5/ki18n5）系平台元数据错误，已按主 agent
  裁决走 Qt6 栈（qtbase/6.11.1 + qtsvg/6.11.1 + ecm/6.26.0）。
- **依赖面（全树 find_package 扫描）**：ECM（REQUIRED NO_MODULE）+ Qt6{Svg,Widgets}
  （REQUIRED）+ Qt6Test（QUIET，BUILD_TESTING 时）+ Qt6Sql（QUIET，仅 examples/Sql）。
  **无任何 KF6 框架库链接**——kcoreaddons/ki18n 等勿引入。
- 交付物：libKChart6.so.3（Cartesian/Polar/Ternary 图表引擎）+ libKGantt6.so.3（甘特图
  scene/view 工具箱）+ KChart6Config.cmake/KGantt6Config.cmake（KChart6::KChart6 /
  KGantt6::KGantt6 导出目标）。eventviews（KDE PIM）消费 KChart 走的正是这套 config。

## 2. OHOS 适配（patches/0001-ohos-drop-printsupport.patch）

- **问题**：上游顶层 find_package(Qt6 ... PrintSupport ...) REQUIRED；已发布的
  qtbase/6.11.1 线 PrintSupport=OFF（kgraphviewer 26.04.0 先例确认，本地缓存 4 个变体
  cmake/ 目录均无 Qt6PrintSupport、无 libQt6PrintSupport.so、无 QPrinter 头文件）。
- **方案（上游原生降级，非手写 no-op）**：KGantt 库源码自带 HAVE_PRINTER 宏守卫
  （kganttgraphicsscene.cpp:36-44：`#ifndef QT_NO_PRINTER` → `#define HAVE_PRINTER`），
  定义 QT_NO_PRINTER 后所有打印入口自动 no-op，API 签名完整保留。比 kgraphviewer
  26.04.0 手写 13 对源文件 no-op patch 干净得多。
- patch 内容（11 文件）：
  1. 顶层 CMakeLists：find_package 组件表去掉 PrintSupport；add_definitions(-DQT_NO_PRINTER)。
  2. src/KGantt/CMakeLists.txt：KGantt6 链接行去掉 PRIVATE Qt::PrintSupport。
  3. src/KGantt/KGantt6Config.cmake.in：去掉 find_dependency(Qt6PrintSupport)（否则消费端
     find_package(KGantt6) 在 PrintSupport=OFF 环境直接失败）。
  4. src/KGantt/kganttgraphicsscene.cpp / kganttgraphicsview.cpp：`#include <QPrinter>` 守卫化。
  5. examples/HeadersFooters/Advanced、examples/DrawIntoPainter：include + 未守卫打印函数体
     （slotPaintRequested/on_printButton_clicked/on_savePDF_clicked）守卫化。
  6. examples/Gantt/project、printing、palette：include 守卫化 + slotFilePrintPreview 守卫化
     （Gantt 三个示例的 slotFileSavePdf/slotFilePrint 上游已带 #ifndef QT_NO_PRINTER 守卫）。
  7. tests/Gantt/view/main.cpp：include + slotPrint 守卫化。
- examples/Sql 上游守卫为 `if(Qt5Sql_FOUND)`（Qt6 世代下变量名错误导致永假）→ 自动跳过，
  无需 patch（上游自身的 bug 反而帮我们裁掉了 Qt6Sql 依赖）。

## 3. 构建接线（Qt6 split-package 通行模式）

- qtbase/6.11.1（Core/Gui/Widgets/Test）+ qtsvg/6.11.1（Qt6::Svg，KChart6 PRIVATE 链接）
  + ecm/6.26.0（tool_requires）。QT_ADDITIONAL_PACKAGES_PREFIX_PATH 挂 qtsvg 包目录
  （kfourinline 26.04.0/libkdegames 已验证模式）。
- qtbase/qtsvg 均 cmake_find_mode=none → 手写 conan_cmakedeps_paths.cmake（kfourinline
  先例）+ CMAKE_PROJECT_TOP_LEVEL_INCLUDES 挂钩。
- CMAKE_SYSTEM_NAME=Linux 强制（主配方+test_package；CMake>=4 worker 在 HarmonyOS 映射下
  编译器探测 broken，chain-wide convention）。
- OHOS soname 规则（CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,）+
  max-page-size=0x1000 链接器钉子 + binary-sign-tool -selfSign 1 签名（kinfocenter 6.7.2
  全套先例）。
- KF_SKIP_PO_PROCESSING=ON：poqm/ 37 语言目录的 .po→.qm 需要 gettext msgfmt；
  ecm_process_po_files_as_qm 在该 flag 下提前 return（ECM 6.26 源码核实）。
  ecm_create_qm_loader 生成的 loader cpp 无 .qm 时运行时空加载，编译不受影响。
- KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台清单）。

## 4. 上游测试（实测结果）

- 注册目标 N=23（ecm_add_test 全树清点）：
  - qtests/ 19 个 KChart QTests：AttributesModel、AxisOwnership、BarDiagrams、
    CartesianDiagramDataCompressor、CartesianPlanes、ChartElementOwnership、Cloning、
    DrawIntoPainter、Legends、LineDiagrams、Measure、Palette、ParamVsParam、PieDiagrams、
    PolarDiagrams、PolarPlanes、QLayout、RelativePosition、WidgetElementOwnership。
  - src/KGantt/test/ 4 个：KGanttConstraint、KGanttConstraintModel、KGanttMultiItems、
    KGanttView。
- **实测：100% tests passed, 0 tests failed out of 23**（Total Test time 8.20 sec，
  conan-create.log 第 2165 行）。无环境排除项——23 个目标全部在本机 OHOS arm64
  runner 实跑通过（QT_QPA_PLATFORM=offscreen）。
- tests/（DelayedData/RootIndex/tests/Gantt 交互式示例）与 examples/ 不注册 ctest，
  不计入 N。
- 消费测试 test_package：1/1 通过（kdiagram_consumer_test Passed 0.10 sec）。

### 迭代修复记录（本地预验证五轮）
1. R1: tests/Gantt + examples 共 10 处 CMakeLists 遗漏 Qt::PrintSupport 链接 → patch 移除
2. R2: kganttgraphicsscene.cpp:907 printer->logicalDpiX() 未守卫 → 补 HAVE_PRINTER 守卫
3. R3: examples/Bars/Simple 上游潜伏 bug（QSvgGenerator 用了未链 Qt::Svg，仅拆分包布局
   暴露）→ 补链接
4. R4: KGanttView::testSetGraphicsView SIGSEGV @0x4 → 移植上游 15a4437（v3.0.1 后官方
   修复）takeGrid() 空指针守卫；glibc 上该 UB 良性（上游 CI 绿）、OHOS musl/clang 必崩
   ——平台差异实锤，B 判定核心素材
5. R5: test_package 裸目标名（KChart6/KGantt6，上游 install(EXPORT) 无 NAMESPACE）+
   OHOS 适配版 conan 2.29.1 的 CMake.test() 无 output_on_failure 形参 → 修正

## 5. 遗留与下游

- eventviews #14755 依赖本件解锁：其 find_package(KChart) 将解析到本包
  KChart6Config.cmake（libKChart6.so.3）。
- 打印功能为平台性裁剪（无打印栈），API 签名保留（no-op），源码兼容。
- KGantt 的 pri 文件 DEPS 仍写 "widgets printsupport"（上游未改，仅影响 qmake 消费者；
  cmake 消费者走 config 文件不受影响——已在 patch 中保留该行为，因 ECM pri 生成器
  DEPS 参数不参与 cmake 链接解析）。
