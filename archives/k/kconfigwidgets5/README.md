# kconfigwidgets5

KDE Frameworks 5 - KConfigWidgets 配置对话框控件库。

KConfigWidgets 提供 KConfigDialog（KPageDialog 子类）、KConfigDialogManager、
KStandardAction、KColorScheme、KCodecAction、KRecentFilesAction、KCModule 等
配置界面控件，是 KDE 应用程序设置界面的基础设施。

本目录为 KF5 系列（Qt5）适配，版本轨道与 KF6 的 `kconfigwidgets` 区分。

## 构建（CMake + Qt5）

- 构建系统：CMake
- 运行时依赖：`qt5-qtbase/5.15.2.2`（Widgets/DBus）、`kconfig5/5.116.0`、
  `kcoreaddons5/5.116.0`、`kguiaddons5/5.116.0`、`ki18n5/5.116.0`、
  `kwidgetsaddons5/5.116.0`、`kcodecs5/5.116.0`
- KAuth 关闭（WITH_KAUTH=OFF，KF5Auth 未发布，仅影响可选握手宏）
- 上游测试 5/5 通过；kstandardactiontest 因 OHOS 无 inotify 豁免
  （KStandardShortcutWatcher 通知不触发，kconfig5 同根因先例）

## OHOS 适配要点

- ELF 占位符 .codesign 需 binary-sign-tool 重签名后方可加载（本地 ctest/
  test_package 前置步骤，knotifications5 先例）
- SONAME 注入（E537）、ECM_MODULE_PATH 手动注入、Qt5 mkspecs 兼容复制
- 详见 5.116.0/notes.md
