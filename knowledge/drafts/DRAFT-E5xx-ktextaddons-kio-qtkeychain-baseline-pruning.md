# DRAFT-E5xx：KF6 依赖包在 ohpcd 受限基线上的依赖裁剪模式

- **软件**：ktextaddons 1.5.0（KDE 文本编辑增强组件库，KPim6TextEdit 依赖件）
- **类别**：平台差异（OHPCD 基线能力边界）
- **error_signature**（可机器匹配）：`Could NOT find KF6(KiOWidgets|KIOGui)` / `qt6keychain.*not found` / `qtbase-sql-dbus.*conflict` / `Duplicated requirement`
- **状态**：draft（待主编定稿编号）

## 根因

ohpcd 制品仓的 KF6/Qt 基线存在两类结构性限制，上游 KF6 生态包直接 find_package 必失败：

1. **kio 只发布 KIOCore-only 版本**（KIOCORE_ONLY=ON）：KF6KIOCore 库+kioworker 可执行存在，但 KIOWidgets/KIOGui 的 cmake 目标与 libKF6KIOWidgets.so/libKF6KIOGui.so 均不存在。原因：KIO 完整版的依赖（solid/kbookmarks/kcolorscheme/kjobwidgets 6.26）未发布（kio 6.26 manifest 自述）。
2. **qtkeychain/0.14.2 传递依赖 qtbase-sql-dbus/6.11.1**：这是第二棵 Qt 包树（含 Qt6 DBus 模块），与下游普遍使用的 qtbase/6.11.1 基线在同一依赖图中冲突（重复的 Qt6::Core cmake 目标定义）。

## 方案（三步裁剪法）

**第一步：消费点分析**。grep 全部 `KF6::<Component>` 引用，确认受限依赖的真实消费面：
- ktextaddons 中 KIO 唯一消费点 = textcustomeditor 的 `KIO::KUriFilterSearchProviderActions`（web 快捷搜索菜单，非核心功能）
- qtkeychain 唯一消费点 = deepl/libretranslate 两个翻译插件的 API key 存储（4 个无凭证插件不受影响）

**第二步：补丁裁剪**（8 件 portability 补丁中的 0001-0006）：
- 顶层 CMakeLists：KF6 REQUIRED 组件集去 `KIO`；`set_package_properties(Qt6Keychain ... TYPE REQUIRED)` → `TYPE OPTIONAL`
- 消费点源文件：删 KIO include/成员/菜单构建块（PlainTextEditor/RichTextEditor 各 3 处）
- plugins/CMakeLists.txt：`if (TARGET qt6keychain)` 守卫 deepl/libretranslate 子目录
- autotests：去 KIOWidgets 链接项（测试断言零改动）

**第三步：依赖图收口**：
- kconfigwidgets 只有 6.18.0 → 传递 KF6 依赖 `override=True` 钉 6.26 线（kxmlgui 6.26 先例）
- **Conan 2 坑**：同一包的 plain `requires` 与 `override=True` requires 并存报 `Duplicated requirement`——override 形式本身既是图级 pin 也算直接依赖，只声明一次

## 验证

ktextaddons/1.5.0 本机 conan create CONAN_RC=0：9 库+4 插件全产出，上游测试 56/56（100%），消费者冒烟 6/6 断言。

## 附加发现（同任务内固化）

1. `QT_NO_CAST_FROM_ASCII`（ECM KDEFrameworkCompilerSettings 注入）+ kconfig 6.26 删除 `KConfigGroup(KConfigBase*, const char*)` 过时重载 → KF5 风格 char 组名全树编译失败；解法：`remove_definitions(-DQT_NO_CAST_FROM_ASCII)`（一处修复 17 个调用点，纯风格严格性无语义变化）
2. musl loader 对含斜杠的 DT_NEEDED（`../../bin/libKF6ConfigCore.so` 相对 soname）按进程 CWD 解析不走 LD_LIBRARY_PATH → 按 CTestTestfile 目录布 `./`、`../bin`、`../../bin` 三层 symlink 农场（kcalendarcore/libkgapi 先例）
3. KDE MODULE 插件平铺 `<build>/bin`，KPluginLoader 按 `libraryPaths()+/kf6/<category>/` 扫描 → staging symlink 到 `<build>/bin/kf6/translator/`
4. CMake 无 Platform/HarmonyOS 模块时需显式 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,` 恢复 DT_SONAME（kio 6.26 先例）
