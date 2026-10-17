# qt5-qtquickcontrols2 5.15.19 适配笔记（HarmonyOS PC）

## 上游概况
- 上游：qt/qtquickcontrols2 tag v5.15.19 = 00c621488d674eccbb5e4d628a0489f6e70516bc（code.qt.io）
- tarball: qtquickcontrols2-everywhere-opensource-src-5.15.19.tar.xz，sha256 eb8e76d3b5f811e96cc80328dc173b97d045734d956712c96834f7b73a95687b
  （TUNA 镜像实测可达且同哈希；conandata.yml 前置镜像源，官方源 download.qt.io 为 fallback）
- 模块（qmake 系，与 5.15.2 相同）：src/quicktemplates2 → libQt5QuickTemplates2.so、
  src/quickcontrols2 → libQt5QuickControls2.so；QML 插件 8 个（QtQuick/Controls.2 主模块 +
  Fusion/Imagine/Material/Universal 风格、Templates.2、Qt/labs/{calendar,platform}）

## 适配策略（recipe 层 + 1 个源码补丁）
| 问题 | 处置 |
|------|------|
| qmake 生成的 ABI 别名步骤（-ln -s $(TARGET)）在 OHOS 工作区报 EPERM，且带 - 前缀被 make 静默忽略 → 无版本名 .so 缺失，同树链接 libQt5QuickTemplates2 报 clang no such file or directory | build() 用独立 qmake 进程预生成两个库子目录 Makefile，_rewrite_ln_aliases 把 -ln -s $(TARGET) 改写为 -cp -f $(TARGET) 实拷贝（顶层 make 判据 test -e Makefile ||，已存在不重生成） |
| PATH ln 垫片方案 | 实测死路：OHOS 工作区内新建脚本不可直接执行（两种 shebang 均 Permission denied rc=126；同目录 ELF 正常执行、sh <脚本> 可解释执行） |
| qmake -r 单进程递归报 Could not find feature quickcontrols2-default | 弃用 -r：顶层 qmake 一次 + 两个库子目录各自独立 qmake 进程 |
| accessibility=off 配置下 qtquicktemplates2global.cpp 编译失败 | patches/0001：用 QT_CONFIG(accessibility) 包裹 accessible/qaccessiblequickpage_p.h 的 include |

## 关键适配点
1. **ABI 别名实拷贝（本版新增）**：qmake 为每个 shared lib 生成三条别名步骤
   （无版本名、.so.5、.so.5.15）。OHOS 工作区 ln -s 一律 EPERM；失败步骤被 make
   静默忽略（Error 127 (ignored)），clang 随后找不到 libQt5QuickTemplates2.so。
   改写为 cp -f 后别名以实文件形式落盘，同树链接与下游消费者均正常。
2. **脚本执行禁令**：工作区内新建的 sh 脚本（即使 -rwxrwx---）exec 报 Permission
   denied（rc=126），/bin/sh 与 /system/bin/sh 两种 shebang 均如此；同目录 clang ELF
   正常执行。垫片类方案（PATH 注入 ln 包装）因此不可用。
3. **accessible 头护栏补丁（5.15.19 上游特有）**：本版 qtquicktemplates2global.cpp
   无条件 include accessible/qaccessiblequickpage_p.h；qtbase 以 -no-accessibility
   配置构建时 QAccessibleQuickItem 未声明 → 4 个编译错误（unknown class name /
   only virtual member functions can be marked override ×2 等）。
   负向测试实证：完整构建树内换回原始文件单对象重编译 negative_rc=2（复现全部错误），
   恢复补丁版 restore_rc=0。
4. **jobserver 警告**：make 报 mkfifo ... Operation not permitted，无害（构建照常完成）。
5. 沿用 5.15.2：syncqt 转发头用 src/ 真头覆盖（_sync_forward_headers）；依赖 .pri
   合并进 qtbase mkspecs（_fix_qtdecl_paths）；无头测试用 Default 风格。
6. **QtTest QML 模块的 install-only 布局特性（qtdeclarative 包，本版测试时发现）**：
   `qml/QtTest` 仅含 libqmltestplugin.so + qmldir，qmldir 引用的 TestCase.qml/SignalSpy.qml/
   testlogger.js 在上游 release 布局中经 `make install` 入前缀、不随构建树与包分发
   （平台既有 Qt5 包同型）。测试时按 qtdeclarative 5.15.2 源码 `src/imports/testlib/`
   补齐模块目录并前置 import path。取证：源码与包内 qmldir md5 同为
   da9a1687487d76528d099b2d0ea642be（193 字节逐字节一致）。
7. **QV4 JIT 崩溃根因与 noexec 垫片（本版核心环境发现）**：OHOS 允许匿名 mmap(PROT_EXEC)
   却拒绝 mprotect(PROT_EXEC)；QV4 的 JIT 能力探测只做 mmap 形态 → 误判可用 →
   ExecutableAllocator::makeExecutable 的 mprotect 被拒 → perror + Q_UNREACHABLE → SIGSEGV。
   QV4_FORCE_INTERPRETER=1 只降 JS 函数 JIT 阈值，不覆盖正则探测。处置：LD_PRELOAD 垫片
   拦截匿名 PROT_EXEC mmap 返 MAP_FAILED（文件型映射放行），探测如实失败 → 引擎纯解释执行
   （本平台 JIT 本不可用）。此前因崩溃中止/跳过的用例（monthgrid/weeknumbercolumn/snippets/
   qquickmaterialstyle/tst_sanity::attachedObjects 后续全量）本次全部执行。
8. **Qt.labs.calendar 模块 install-only（同 6 类）**：构建树与包内 calendar 目录缺
   DayOfWeekRow/MonthGrid/WeekNumberColumn.qml（Makefile 的 install_qmlfiles 才列出这三者，
   构建树 copy 目标仅 qmldir/plugins.qmltypes）；测试前按源码补齐。另 Imagine 风格
   DelayButton/ProgressBar 依赖平台未提供的 QtGraphicalEffects 模块 → 整体模式中止于
   tst_delaybutton.qml，改 `-input` 逐文件补救（49 文件：46 全过、2 阻塞）。

## 上游测试
- tests/auto（auto.pro）36 个注册目标：accessibility 因 qtbase 以 -no-accessibility 构建、
  由上游 qmake 机制在 qmake 阶段 Skipped；其余 35 个目标全部真机编译并在目标机逐目标
  独立进程执行（防连坐）。
- 运行环境：QT_QPA_PLATFORM=offscreen + QV4_FORCE_INTERPRETER=1 + QML_DISABLE_DISK_CACHE=1；
  另按上面关键适配点 6/7/8 补齐 QtTest 模块目录、注入 noexec 垫片、补齐 calendar 模块目录。
- **真机实测（2026-10-04）**：合计执行 10192 个测试函数——**10040 通过 / 22 失败 / 130 跳过
  （上游 QSKIP），通过率 99.8%**。22 例失败全部逐条定性为平台/环境类（无字体目录度量差异 5、
  qtbase 未启用 accessibility 5、平台缺 QtGraphicalEffects 模块 11、productType=unknown 1），
  无本包代码缺陷。imagine 风格因缺 QtGraphicalEffects 改逐文件补救执行（49 文件：46 全过、
  1 文件 1 例字体类失败、2 文件被模块缺失阻塞）。逐目标明细、失败证据与 5.15.2 会话对比
  见 reports/test-report.md。

## test_package（消费者测试）
- 3 用例真机全过（TEST SUMMARY: 3 passed, 0 failed）：
  case_api_qquickstyle（QQuickStyle::setStyle Default + name() 校验）、
  case_qml_import（QtQuick.Controls 2.15 模块解析）、
  case_e2e_component_create（QQmlComponent create() 端到端）

## 版本
- 5.15.19（2026-10-04 适配，HarmonyOS PC aarch64）；含 1 个源码补丁（0001 accessibility 编译守卫）

## 战略意义
- 下游解锁：kirigami2 5.116.0（libkirigami 硬依赖 Qt5::QuickControls2）

---
**编译结束**: 2026-10-04
**最终状态**: published（conan create 全绿：Package 367aad264e778fa6d26a278c11b8c5bad5f7a79a created +
test_package PASSED；conan-verify Verdict PASS；上游测试真机全量执行 10040/22/130；构建树 qt5-q37c4b3ef57758 留档）
