# KSyntaxHighlighting (KF5)

KDE Frameworks 5 语法高亮引擎。为文本编辑器等应用提供可复用的语法高亮引擎，
内置数百种语言定义与主题，支持 Qt Widgets / Qt Quick / HTML 高亮。

## 特性

- 通过 `KSyntaxHighlighting::Repository` 按名称加载语法定义（如 "C++"）与主题。
- 语法定义经 `katehighlightingindexer` 索引并 bundle 进库内资源（QRC_SYNTAX）。
- 提供 `KSyntaxHighlighter`(Qt Widgets) / `HTMLHighlighter` / `SyntaxHighlighter`(Stream) 等 API。
- 附带 `kate-syntax-highlighter` 命令行工具。

## OpenHarmony 适配

- 以 `ksyntax-highlighting` Conan 包发布到 HarmonyOS PC AArch64。
- KF5 分支基于 Qt5（`qt5-qtbase/5.15.2.2`），CMake + KDE ECM 构建。
- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台检测；`KF_SKIP_PO_PROCESSING=ON` 跳过翻译。
- 上游 CTest 6/6 通过（wildcardmatcher / repository / theme / testhighlighter / htmlhighlighter / folding），
  消费者用例加载内置 C++ 语法与 Breeze Light 主题验证通过。
- 语法/主题数据通过 qrc 资源编译进库，运行时无需外部数据文件。

## 依赖

- 运行时: `qt5-qtbase` (Qt5Core/Gui/Network)
- 构建期: `ecm`、`perl`
