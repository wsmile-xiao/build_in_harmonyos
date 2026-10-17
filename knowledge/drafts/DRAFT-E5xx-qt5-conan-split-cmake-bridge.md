# DRAFT: Qt5 Conan 拆包后伞形 find_package(Qt5 COMPONENTS ...) 的跨包桥接

> 草稿状态：随 kirigami2 5.116.0 PR #12191 提交，五要素齐。来源：kirigami2
> 5.116.0 适配全过程（2026-09-23，KF5/Qt5 生态首个用伞形 Qt5 find 的库）。

## 适用场景

任何在 OHPCD Conan 生态里消费 **Qt5 拆分包链**（qt5-qtbase +
qt5-qtdeclarative + qt5-qtquickcontrols2 + qt5-qtsvg + ...）且上游构建系统使用
伞形 `find_package(Qt5 ... COMPONENTS <跨包组件>)` 或链接 `Qt5::<Component>`
/`Qt5::GuiPrivate`/运行 QML 测试（QtTest QML 模块）的 KF5/Qt5 软件包。

已知消费者：kirigami2（已适配）、kirigami-app、kirigami-gallery、以及一切
`ecm_add_qml_module` 系（ECMQmlModule5）的 KF5 QML 模块件。

## 症状（error_signature）

1. `Qt5::Core references the file ".../p/../b//mkspecs/linux-clang" but this
   file does not exist` —— qtbase config 构建期路径残留
2. `Target "X" links to: Qt5::Qml/Qt5::QuickControls2/... but the target was
   not found` —— 伞形 find 无跨包分发
3. `qt5-qtdeclarative_DEPS_TARGET contains Qt5::Network but the target was
   not found` —— CMakeDeps 依赖链前置组件缺失
4. `undefined symbol: QTest::setMainSourcePath` —— QuickTest 别名没链
   qtbase 的 libQt5Test
5. `QtTest/TestCase.qml: No such file or directory / Type TestCase
   unavailable` —— qtdeclarative 包 qml payload 不完整

## 根因

Qt5 链按模块拆包 + qmake 原生构建产物直接打包，四个断点（详见 .kv 的
root_cause）：① qtbase config 树不可重定位；② qtdeclarative 只有单一
Qt5QmlConfig；③ CMakeToolchain 的 PREPEND 顺序压制外部桥目录；④
QuickTest 符号在 qtbase、QML payload 不在包里。

## 修复方案（rec_approach）

五步桥接（完整实现见 `archives/k/kirigami2/5.116.0/conanfile.py` 的
`_stage_fixed_qtbase_cmake` / `_write_qt5_bridge` /
`_install_qt5_bridge_into_generators` / `_stage_qttest_qml`）：

1. staged-fixed qtbase config 树（symlink 镜像 + regex 修 mkspec 路径）
2. Qt5Config 组件分发桥覆写 generators/Qt5Config.cmake（tc.generate() 后写）
3. 预物化 Qt5Core/Gui/Network/Concurrent
4. Qt5QuickTestConfig.cmake+ConfigVersion shim（双链 qtdeclarative 包级
   target + Qt5::Test）
5. QtTest QML payload stage（src/imports/testlib 拷贝 + QML2_IMPORT_PATH
   前置）

## 验证

- kirigami2 5.116.0 PR #12191：修复前 CI-030/CI-021 两 Worker 确定性失败
  （全部 19 用例挂在 TestCase.qml 缺失）；修复后 CI 等价本地模拟 19/19 执行、
  非 Accessible 用例 7/7 通过、test_package 2/2。

## 兜底（fallback）

- 改上游 CMakeLists 逐组件 find（侵入源码，最后手段）
- 依赖包补发：qt5-qtdeclarative 加 .N 版本装全 qml payload；qtbase 修
  MkspecDir 可重定位性——届时本桥的对应步骤可按条件跳过
  （`if "/../b/" not in content: return None` 已内置该探测）。
