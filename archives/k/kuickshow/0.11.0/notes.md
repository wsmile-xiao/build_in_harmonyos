# kuickshow 0.11.0 适配笔记

## 上游
- https://invent.kde.org/graphics/kuickshow tag v0.11.0（官方 archive tarball）
- 源 https://invent.kde.org/graphics/kuickshow/-/archive/v0.11.0/kuickshow-v0.11.0.tar.gz
- sha256=8b68f67db4fb97ca76081ebbb5a762b708da950ac849c78e94504560fa4d399e
- Qt6(Core/Gui/PrintSupport) + KF6(DocTools/I18n/IconThemes/KIO/WindowSystem/XmlGui)，cmake ≥ 3.28
- 图像后端三选一：Imlib1/Imlib2（可选，带 X11）或纯 Qt（默认兜底 imlib_qt.cpp）——OHOS 走纯 Qt 后端，零 X11 依赖

## 关键决策
1. **kwindowsystem X11 部件裁剪**（patches/0003）：ohpcd 的 kwindowsystem/6.14.0 以 KWINDOWSYSTEM_X11=OFF 构建，**不装 kstartupinfo.h / kwindowinfo.h**（本地缓存实测，包内只有 KWindowSystem/KWindowEffects/KWindowShadow + netwm_def.h）。上游两处引用语义均为 X11/Wayland 专有：KStartupInfo::appStarted()（启动通知视觉反馈完成信号）删除（hide() 保留）；Kuick::frameSize() 的 KWindowInfo NET WM 框饰查询替换为 invalid s_frameSize 回退（0 框尺寸 = 上游"窗口未显示"路径的等价结果）。KUrlLabel 在档（kwidgetsaddons）无需处理。
2. **PrintSupport 裁剪**（patches/0001）：ohpcd 发布的 qtbase/6.11.1 只含 Core/Gui/Widgets/Network/Sql/Test/DBus/Concurrent/Xml，**无 libQt6PrintSupport.so、无 Qt6PrintSupport cmake 配置**（实测 find 遍历本地缓存全量确认）。上游打印链（src/printing.cpp + printing_page.ui + QPrinter/QPrintDialog）整体移出构建；Print Image 菜单动作保留注册，触发时 KMessageBox::information 报平台不支持（比删菜单动作改动面小，保住 kuickActions 键枚举与 shortcuts 配置读写）。
3. **kdoctools 裁剪**（patches/0001）：KF6DocTools 移出 REQUIRED 组件表，doc/ 手册目录挂 KF6DocTools_FOUND 守卫 + CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE（kfourinline 26.04.0 / kgoldrunner 26.04.0 双先例）。
4. **C++17**（patches/0002）：上游钉 CMAKE_CXX_STANDARD 11，KF6 6.14 头文件要求 C++17（kio 6.14.0 配方为同因设 20）。
5. **KF6 6.14.0 基线**：与 kio/6.14.0 + kxmlgui/6.14.0 的已发布 binary 闭包对齐（kconfig/kconfigwidgets/kcoreaddons/kcrash/ki18n/kiconthemes/kitemviews/kjobwidgets/ktextwidgets/kwidgetsaddons/kwindowsystem/kcompletion/kcodecs/kbookmarks/kguiaddons/kcolorscheme/kauth/solid/kservice/karchive 全部传递解析），KLineEdit/KUrlComboBox 归 kcompletion 闭包内。
6. **N=0 补偿测试**：上游 0 注册测试（无 tests//autotests/、无 add_test/enable_testing/ECMAddTests，grep 证据）。test_package 四段消费者验证：①安装的 kuickshow --version（offscreen）②im_palette.pal 调色板契约（64 行三字段 RGB 十六进制，misc/im_palette.pal 数据制品）③pics/ 应用数据 + desktop 入口文件契约 ④hicolor 图标 + logging categories。

## 配方要点
- package_type="application" + commands.json（kgoldrunner 先例）
- ecm/6.20.0 tool_requires（kio 6.14.0 / keditbookmarks 26.04.0 同款）
- KF_IGNORE_PLATFORM_CHECK=TRUE + KF_SKIP_PO_PROCESSING=ON（audiocd/kgoldrunner 先例）
- USE_IMLIB1/USE_IMLIB2=OFF 显式钉死（防 cache 翻转引入 X11）
- -Wl,-z,max-page-size=0x1000（OHOS lld 布局 workaround，audiocd 先例）
- cmake_find_mode=none 的 qtbase/KF6 包：手工 conan_cmakedeps_paths.cmake（audiocd/kgoldrunner 先例）
- 运行环境：QT_QPA_PLATFORM=offscreen + HOME 隔离（kgoldrunner/audiocd 先例）

## 上游测试（N=0）
- grep -rn 'add_test|enable_testing|ECMAddTests' 全 tarball 无匹配
- 无 tests/ autotests/ 目录
- 消费者测试补偿：kuickshow_consumer_test（四段式，见 test_package/MANIFEST.yml）
