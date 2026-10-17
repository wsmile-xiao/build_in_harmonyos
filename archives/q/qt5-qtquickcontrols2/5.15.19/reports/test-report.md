# qt5-qtquickcontrols2/5.15.19 — 测试报告（OHOS aarch64 真机）

> 本文件位于 `reports/`（仓库 .gitignore 覆盖目录），随任务分支以 `git add -f` 强制纳入，供评审查看测试证据。
> 按任务纪律，conan-create.log 等构建日志不随仓提交（本目录不含）。

## 0. 结论摘要

- 上游注册测试目标 N=36（tests/auto/auto.pro）：其中 accessibility 因 qtbase 以 `-no-accessibility`
  构建、由上游 qmake 机制在 qmake 阶段 Skipped；其余 **35 个目标全部真机编译并在目标机逐目标独立进程执行**。
- 合计执行 **10192** 个测试函数：**10040 通过 / 22 失败 / 130 跳过（上游 QSKIP）**，通过率 **99.8%**。
- 22 例失败全部逐条定性为平台/环境类（见 §3），**无本包代码缺陷**；其中 0 例与本适配补丁相关。
- imagine 风格目标因平台未提供 QtGraphicalEffects 模块，在单进程整体模式下中止于
  tst_delaybutton.qml 的加载；改用**逐文件补救**执行其全部 49 个用例文件：46 个文件全过、
  1 个文件含 1 例字体类失败、2 个文件（tst_delaybutton/tst_progressbar）被模块缺失阻塞（见 §4）。
- 与 5.15.2 会话结果对比：执行函数数 8187 → 10192，通过 8174 → 10040；5.15.2 因 QV4 JIT
  崩溃未能执行/中止的用例（monthgrid、weeknumbercolumn、snippets、qquickmaterialstyle、
  tst_sanity::attachedObjects 之后的全量用例等）本次全部执行通过（见 §5）。

## 1. 运行环境与测试环境补齐

- 目标机：HarmonyOS PC aarch64 真机（SELinux `u:r:adhoc_bin:s0`，uid 20020084）
- 构建：conan create（本包配方 build()），clang 15.0.4，`-spec linux-clang`
- 运行基线三件套：`QT_QPA_PLATFORM=offscreen` + `QV4_FORCE_INTERPRETER=1` + `QML_DISABLE_DISK_CACHE=1`
- 执行方式：每个目标二进制在其构建目录内以独立进程运行（防连带；日志见 §6）

测试环境另有三项补齐，均为**平台既有发布布局特性**所致、不修改上游源码与用例：

1. **QtTest QML 模块目录补齐（qmlpatch）**。qtdeclarative 5.15.2 包 `qml/QtTest` 仅含
   `libqmltestplugin.so` + `qmldir`，其 qmldir 引用的 TestCase.qml/SignalSpy.qml/testlogger.js
   在上游 release 布局中经 `make install` 入前缀、不随构建树与包分发（平台既有 Qt5 包同型）。
   按 qtdeclarative 5.15.2 源码 `src/imports/testlib/` 补齐后置于 import path 最前，
   qmltest 系目标方可加载。取证：源码 `src/imports/testlib/qmldir` 与包内 `qml/QtTest/qmldir`
   md5 同为 `da9a1687487d76528d099b2d0ea642be`（193 字节逐字节一致）。
2. **noexec 垫片（LD_PRELOAD）**。OHOS 允许匿名 `mmap(PROT_EXEC)` 但拒绝 `mprotect(PROT_EXEC)`；
   QV4 的 JIT 能力探测只做 mmap 形态 → 误判可用 → W^X 分配器 `mprotect` 被拒 →
   `ExecutableAllocator::makeExecutable` 触发 `Q_UNREACHABLE` → SIGSEGV。垫片令匿名
   `PROT_EXEC` mmap 返回 `MAP_FAILED`（文件型映射放行）→ 探测失败 → 引擎全量转入纯解释执行
   （本平台 JIT 本不可用，垫片只是让探测结果与事实一致）。逐目标运行中垫片实际拦截
   5–50 次不等（例：controls/default 50 次、calendar 5 次）。
3. **Qt.labs.calendar 模块目录补齐**。其 3 个 .qml 同上属上游 install-only 文件（取证：
   构建树 `src/imports/calendar/Makefile` 的 `install_qmlfiles` 目标列出 DayOfWeekRow.qml/
   MonthGrid.qml/WeekNumberColumn.qml，构建树 copy 目标仅含 qmldir/plugins.qmltypes），
   测试前按源码补齐构建树模块目录，calendar 目标（含 calendarmodel/dayofweekrow/monthgrid/
   weeknumbercolumn 4 个数据文件）方可执行。

## 2. 逐目标结果（35 目标，imagine 为逐文件补救合计）

汇总由 clean-summary 聚合各目标日志 Totals 得出；标记含义：**字体**=无字体目录度量差异；
**A11y**=qtbase 未启用 accessibility（Accessible 附加对象不存在）；**QtGE**=平台缺
QtGraphicalEffects 1.12 模块；**Sel**=QSysInfo::productType()=unknown 平台选择器。

| # | 目标 | passed | failed | skipped | 标记 |
|---|------|-------:|-------:|--------:|------|
| 1 | calendar/tst_calendar | 23 | 0 | 0 | |
| 2 | controls/default/tst_default | 1358 | 1 | 9 | 字体 |
| 3 | controls/fusion/tst_fusion | 1358 | 1 | 9 | 字体 |
| 4 | controls/imagine/tst_imagine | 1343 | 1 | 9 | 字体（逐文件补救，2 文件阻塞 · §4） |
| 5 | controls/material/tst_material | 1358 | 1 | 9 | 字体 |
| 6 | controls/universal/tst_universal | 1358 | 1 | 9 | 字体 |
| 7 | cursor/tst_cursor | 8 | 0 | 0 | |
| 8 | customization/tst_customization | 612 | 3 | 0 | A11y |
| 9 | designer/tst_designer | 30 | 0 | 0 | |
| 10 | focus/tst_focus | 26 | 0 | 0 | |
| 11 | font/tst_font | 63 | 0 | 1 | |
| 12 | palette/tst_palette | 63 | 0 | 0 | |
| 13 | platform/tst_platform | 67 | 0 | 0 | |
| 14 | pressandhold/tst_pressandhold | 8 | 0 | 0 | |
| 15 | qquickapplicationwindow/tst_qquickapplicationwindow | 23 | 3 | 0 | A11y×2 + QtGE×1 |
| 16 | qquickcolor/tst_qquickcolor | 3 | 0 | 0 | |
| 17 | qquickdrawer/tst_qquickdrawer | 270 | 0 | 0 | |
| 18 | qquickheaderview/tst_qquickheaderview | 7 | 0 | 0 | |
| 19 | qquickiconimage/tst_qquickiconimage | 20 | 0 | 6 | |
| 20 | qquickiconlabel/tst_qquickiconlabel | 25 | 0 | 1 | |
| 21 | qquickimaginestyle/tst_qquickimaginestyle | 5 | 0 | 2 | |
| 22 | qquickmaterialstyle/tst_qquickmaterialstyle | 117 | 0 | 0 | |
| 23 | qquickmaterialstyleconf/tst_qquickmaterialstyleconf | 5 | 0 | 0 | |
| 24 | qquickmenu/tst_qquickmenu | 225 | 0 | 65 | |
| 25 | qquickmenubar/tst_qquickmenubar | 30 | 0 | 10 | |
| 26 | qquickninepatchimage/tst_qquickninepatchimage | 70 | 0 | 0 | |
| 27 | qquickpopup/tst_qquickpopup | 325 | 10 | 0 | QtGE |
| 28 | qquickstyle/tst_qquickstyle | 19 | 0 | 0 | |
| 29 | qquickstyleselector/tst_qquickstyleselector | 50 | 1 | 0 | Sel |
| 30 | qquickuniversalstyle/tst_qquickuniversalstyle | 23 | 0 | 0 | |
| 31 | qquickuniversalstyleconf/tst_qquickuniversalstyleconf | 3 | 0 | 0 | |
| 32 | revisions/tst_revisions | 20 | 0 | 0 | |
| 33 | sanity/tst_sanity | 1008 | 0 | 0 | （另 10 例上游 blacklist，不计失败） |
| 34 | snippets/tst_snippets | 112 | 0 | 0 | |
| 35 | translation/tst_translation | 5 | 0 | 0 | |
| | **合计（含 imagine 补救）** | **10040** | **22** | **130** | 通过率 99.8%（10040/10062 已执行） |

注：35 个目标官方日志聚合为 8697/21/121；imagine 整体模式中止（无 Totals）故以逐文件补救
合计 1343/1/9 计入，见 §4。

## 3. 22 例失败逐条定性（全部环境类）

| 类别 | 例数 | 涉及用例 | 直接证据 |
|------|----:|----------|----------|
| 字体目录缺失度量差异 | 5 | controls default/fusion/material/universal/imagine 各 1：`TextArea::test_implicitSize()` | 运行日志含 `QFontDatabase: Cannot find font directory <qtbase>/lib/fonts`；失败明细 Actual 3 / Expected 2（tst_textarea.qml:157，换行度量差异） |
| qtbase -no-accessibility | 5 | customization：`creation(identified:AbstractButton)`、`override(identified:AbstractButton)`、`override(overidentified:AbstractButton)`；qquickapplicationwindow：`activeFocusOnTab1/2` | 测试数据文件使用 Accessible 附加属性：customization/data/styles/identified/AbstractButton.qml:61,67,73 `Accessible.name`；qquickapplicationwindow/data/activefocusontab.qml:72,84 `Accessible.role`；该特性未启用时附加对象不存在，组件创建失败（日志 `Type AbstractButton unavailable`） |
| 平台缺 QtGraphicalEffects 1.12 模块 | 11 | qquickpopup：`toolTipCrashOnClose`、`setOverlayParentToNull`（Default/Fusion/Imagine/Material/Universal 各 2）；qquickapplicationwindow：`clearFocusOnDestruction` | 日志 `module "QtGraphicalEffects" is not installed`；数据文件 import 行：qquickpopup/data/toolTipCrashOnClose.qml:54、qquickapplicationwindow/data/clearfocusondestruction.qml:54 |
| productType=unknown 平台选择器 | 1 | qquickstyleselector::`platformSelectors()` | QSysInfo::productType() 在 OHOS 为 unknown，`+linux` 平台目录选择期望落空（与 5.15.2 会话同款定性） |

注：§2 中 sanity 的 10 例 blacklist 为上游自带 QSKIP/黑名单机制，不计入失败。
22 例中 imagine 的 1 例（字体类）来自 §4 逐文件补救日志。

## 4. imagine 风格逐文件补救（49 个用例文件）

单进程整体模式在该风格下中止于 `data/tst_delaybutton.qml` 加载（其创建 DelayButton 时触发
`qt-project.org/imports/QtQuick/Controls.2/Imagine/DelayButton.qml:41 import QtGraphicalEffects 1.12`，
平台无该模块）。改为 `-input <file>` 逐文件独立进程执行全部 49 个 tst_*.qml：

- 结果：`files=49 ok=46 blocked=2 passed=1343 failed=1 skipped=9`
- 被阻塞（BLOCKED，文件加载失败、用例无法执行，不计入失败数）：
  - `tst_delaybutton.qml`（Imagine/DelayButton.qml:41 导入 QtGraphicalEffects）
  - `tst_progressbar.qml`（Imagine/ProgressBar.qml:41 同上）
- 含失败的 1 个文件：`tst_textarea.qml` 61 通过 / 1 失败（字体类，同 §3）

## 5. 与 5.15.2 会话对比（本适配的环境修复成果）

| 项目 | 5.15.2（2026-09-19） | 5.15.19（本次） |
|------|----------------------|------------------|
| 执行测试函数 | 8187 | 10192 |
| 通过 | 8174 | 10040 |
| 完整执行目标 | 31/36 | 35/36（accessibility 上游 Skipped） |
| monthgrid/weeknumbercolumn（Date 解析触发 JIT 崩溃） | 未执行 | 通过（calendar 23/0/0） |
| snippets（RegExp JIT） | 跳过 | 112/0/0 |
| qquickmaterialstyle（RegExp JIT） | 跳过 | 117/0/0 |
| tst_sanity::attachedObjects QFATAL 及其后续用例 | 中止（仅 761 例） | 1008/0/0（QFATAL 消除，全量执行） |

差异来源：QV4 JIT 崩溃根因已定位（OHOS mprotect(PROT_EXEC) 拒绝 vs 探测只做 mmap），
经 noexec 垫片使引擎以纯解释执行运行，清单见 §1.2。

## 6. 补丁负向测试证据（patches/0001-guard-accessible-include.patch）

在完整构建树内将 qtquicktemplates2global.cpp 换回上游原始版、单对象重编译：
复现全部 4 个编译错误（unknown class name 等，negative_rc=2）；恢复补丁版重编译：通过
（restore_rc=0）。原始日志：设备 `$HOME/qqc2-negative/out/{negative.log,restore.log}`。

## 7. test_package（消费者级验证，真实执行器）

逐用例输出（TEST SUMMARY 行由被测程序自身打印，任一用例失败进程退出码非零）：

```
TEST case_api_qquickstyle: PASS [style=Default]
TEST case_qml_import: PASS
TEST case_e2e_component_create: PASS
TEST SUMMARY: 3 passed, 0 failed
```

用例 1：`QQuickStyle::setStyle("Default")` 真调用 + `name()` 校验；用例 2：QML 模块导入解析
（`import QtQuick.Controls 2.15`，插件实际 dlopen）；用例 3：QQmlComponent 端到端 create()
（消费链路全过程）。

## 8. 原始日志位置（设备）

- 构建树：`/storage/Users/currentUser/.conan2/p/b/qt5-q37c4b3ef57758/b`
- 逐目标日志（35 个）：`$HOME/qqc2-tests/out/<目标>.log`；被重跑目标旧日志留 `<目标>.log.pre`，
  早期环境日志留 `out/mainenv/`
- imagine 逐文件补救：`$HOME/qqc2-tests/out/salvage-imagine/<文件>.log`（汇总行在 salvage-imagine.log）
- 重跑批次记录：`$HOME/qqc2-tests/rerun.log`、`rerun2.log`
- 目标清单（35 条）与本报告同目录 `upstream-test-binary.txt`；`conan-verify-report.md` 为八门禁验证报告
