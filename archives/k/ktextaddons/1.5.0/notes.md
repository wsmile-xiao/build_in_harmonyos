# ktextaddons 1.5.0 适配笔记

## 适配概况
- KDE 文本编辑增强组件库（KPim6TextEdit/kpimtextedit 的依赖件）
- 构建系统：CMake + ECM（KDE Frameworks 6 线）
- 产物：9 个共享库 KF6TextAddonsWidgets / KF6TextAutoCorrectionCore / KF6TextAutoCorrectionWidgets / KF6TextEmoticonsCore / KF6TextEmoticonsWidgets / KF6TextTranslator / KF6TextGrammarCheck / KF6TextUtils / KF6TextCustomEditor + bing/google/lingva/yandex 翻译插件
- 上游：https://github.com/KDE/ktextaddons tag v1.5.0（KDE download 镜像 1.5.0 已不发布，GitHub 归档为官方可用形态，tarball 实测 200）

## 依赖（W0 预检全在档）
- qtbase/6.11.1（Core/Gui/Widgets/Network/Test，Qt6 模块全在包内，offscreen 平台插件含）
- ki18n/karchive/kxmlgui/sonnet/ksyntaxhighlighting 6.26.0
- kconfigwidgets/6.18.0（ohpcd 仅此版本；传递依赖 override 到 6.26 线，kxmlgui 先例）
- kconfig/kcoreaddons/kguiaddons/kwidgetsaddons/kcolorscheme/kcodecs 6.26.0（override=True）
- openssl/3.5.6.1 + zstd/1.5.7（KF6ArchiveConfig find_dependency 链，kxmlgui 先例）
- ecm/6.26.0（tool_requires）

## 适配要点（六补丁）
1. 0001 顶层 CMakeLists：去 KIO 组件（ohpcd kio 为 KIOCORE_ONLY 基线，无 KIOWidgets/KIOGui 目标）+ Qt6Keychain TYPE REQUIRED→OPTIONAL
2. 0002 textcustomeditor/CMakeLists：去 KIOWidgets 私有链接项
3. 0003/0004 plaintexteditor.cpp/richtexteditor.cpp：移除 KIO::KUriFilterSearchProviderActions include/成员/webshortcut 菜单块 + 死 QtDBus include（无实际调用，Qt6 DBus 未发布）
4. 0005 plaintexteditor autotests：去 KIOWidgets 链接
5. 0006 translator plugins：deepl/libretranslate 加 if(TARGET qt6keychain) 守卫（qtkeychain/0.14.2 在 ohpcd 依赖 qtbase-sql-dbus/6.11.1 第二 Qt 树，与 qtbase 基线冲突；bing/google/lingva/yandex 插件保留）
6. KF_IGNORE_PLATFORM_CHECK=TRUE / KF_SKIP_PO_PROCESSING=ON / BUILD_DESIGNERPLUGIN=OFF / BERGAMOT_TRANSLATOR_PLUGIN=OFF / QT_MAJOR_VERSION=6 / C++20（kio 先例）
7. textedittexttospeech 子目录在 Qt6TextToSpeech 未找到时上游自动跳过（ohpcd 未发布）
8. grammalecte 的 python3 仅为运行时路径配置（QStandardPaths::findExecutable），非构建依赖

## 测试结果（2026-10-02 本机 conan create 实跑，CONAN_RC=0）
- 上游测试（BUILD_TESTING=ON，ctest 全量真跑）：**56/56 通过（100%），0 失败**，总耗时 7.83s
- 上游实注册测试数：62 项（56 执行全过 + 6 项 OHOS 沙箱环境限制排除，排除原因逐项如下）：
  - languagetoolresultjobtest / languagetoolgetlistoflanguagejobtest：对 www.kde.org 发真实 HTTP 请求，构建沙箱无出站网络，QEventLoop 驱动的 job 永久等待（kio 6.26.0 excluded-tests 先例）
  - grammalecteresultwidgettest / grammalecteconfigwidgettest / languagetoolconfigwidgettest：断言 QDialogButtonBox 标准按钮 icon 非空（QIcon::fromTheme），OHOS 沙箱无图标主题资源（QFontDatabase 亦报 "Cannot find font directory"），icon().isNull() 确定性为 true
  - translator-translatorwidgettest：TranslatorWidget 构造器初始化 google 引擎并填充 from/to 语言下拉框（断言 count()>0 需引擎语言列表），触发真实网络请求，沙箱内 QEventLoop 永久挂起（实测 >150s 停滞；kio kioworker procmgr_wait 同构先例）
- deepl / libretranslate 插件随 if(TARGET qt6keychain) 守卫整体跳过（补丁 0006），其 autotests（约 7 项）未构建未注册，不计入统计
- ctest 加 --timeout 180 防御网（防网络型测试挂死构建）
- 消费者测试（test_package）：ctest 1/1 通过 + 二进制直跑 6/6 断言 ALL PASS（TextUtils::ConvertText::normalize/upperCase/lowerCase + SlideContainer 构造/content 往返/slideHeight，R34 实调 API）

## 测试运行机制（conanfile.py 内嵌，kio 6.26.0 先例）
1. 相对 soname symlink 农场：依赖 KF6 包烤入构建布局相对 DT_NEEDED（../../bin/libKF6ConfigCore.so 等），musl loader 按进程 CWD 解析含斜杠路径不走 LD_LIBRARY_PATH——对每个 CTestTestfile 目录布点 ./ ../bin ../../bin 三层 symlink（kcalendarcore/libkgapi 先例）
2. SONAME 旗标：CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname, 恢复 DT_SONAME（CMake 无 Platform/HarmonyOS 模块时缺省不设）
3. 翻译插件 staging：KDE 构建布局把 MODULE 插件平铺 <build>/bin，TranslatorEngineLoader 按 libraryPaths()+/kf6/translator/ 扫描——staging 到 <build>/bin/kf6/translator/（symlink）后 bing/google/lingva/yandex 四引擎可加载
4. 测试环境：LD_LIBRARY_PATH 依赖全链 + /system/lib64 前置（防 SDK llvm/lib 的 libc++_shared.so 遮蔽系统版）+ QT_QPA_PLATFORM=offscreen + 独立 test-home/XDG 目录 + CTEST_PARALLEL_LEVEL=1
5. test_package 直跑：conanrun.sh + 内联 LD_LIBRARY_PATH=/system/lib64 前缀 + offscreen（内联赋值优先级高于包装器导出，手动验证 6/6 断言后固化）
