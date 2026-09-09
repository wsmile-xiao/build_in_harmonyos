# Qt Quick Test（QML 系）上游测试无头跑通环境组合 + QML 绑定层判别

> DRAFT — 待主编确认编号（拟 E543）
> 来源：kirigami-addons 1.13.0 适配（PR #8714，审核打回修复过程中实证）

## 错误特征

QML 系包开启 `BUILD_TESTING=ON` 后跑上游 autotests，遇到的三类典型报错：

1. **loader 层**：`Error loading shared library libKF6I18n.so: libintl.so.8 ...`——依赖库路径不全
2. **QML 编译期**：`module "QtMultimedia" is not installed`、`Type BaseAlbumMaximizeComponentTestCase unavailable`——QML 导入树缺失或绑定层不在
3. **插件解析**：`Could not resolve dynamic plugin with base name "qtquick2plugin"`——QML2_IMPORT_PATH 根目录缺失

以及构建期：`QtQuickTest not found, autotests will not be built`（Qt6QuickTest 找不到时上游静默跳过）。

## 根因（两个机制）

### 机制一：Qt Quick Test 运行期环境是三路注入的组合

`QUICK_TEST_MAIN_WITH_SETUP` 生成的 `qmltest` 可执行在运行期需要：

- **QPA 平台插件**：无头环境必须 `QT_QPA_PLATFORM=offscreen`（qtbase 包 `plugins/platforms/libqoffscreen.so`）
- **QML 导入树（三级）**：
  1. 本包构建产物 `<build>/bin`（`ecm_add_qml_module` 的 qmldir + plugin）
  2. QML 依赖包的导入树：qtdeclarative 的 `qml/`（QtTest/QtQuick）、kirigami 的 `lib/qml/`
  3. （依赖由配方逐包 prepend，布局可能是 `qml/` 或 `lib/qml/`，都要试）
- **共享库（双布局）**：Qt 包的库在 `lib/`，**KF6 包的库在 `bin/`**（kirigami/ki18n/kconfig 全家）——只收 lib/ 会漏一串 `libKF6*.so`
- 另需独立 XDG/HOME 可写沙箱（QML engine 启动会写缓存）

### 机制二：Qt 模块的 QML 绑定层与 C++ 库是两个制品包

- `qtdeclarative/6.11.1` 提供 Qt6Qml/Quick/QuickTest **及** `qml/` 导入树（task 预判"qtbase 裁剪包无 Qt6Qml"不成立——组件由独立包提供）
- `qtmultimedia/6.11.1` 制品包**只有 C++ 库**（libQt6Multimedia.so 等），**无 qml/ 目录**——其配方 requires 仅 qtbase+qtshadertools（无 qtdeclarative），构建天然不产出 QML 绑定
- 判别方法：`conan cache path <ref> && ls <pkg>/qml/` 包内实测。**"C++ 库在仓" ≠ "QML 绑定在仓"**

## 解法（代码级）

见 `.kv` 的 `solution` 字段——conanfile.py 的 `_test_env()` + `_run_upstream_tests()` 完整可复制实现。

### 排查顺序

| 报错 | 定位手段 | 修法 |
|---|---|---|
| loader 找不到库 | 看报错库属于哪个包 | LD_LIBRARY_PATH 补该包 lib/ **和 bin/** |
| Type/module unavailable | `QML_IMPORT_TRACE=1` 重跑 | 按 trace 找缺失 import 的文件:行号；绑定层缺失则逐项豁免 |
| dynamic plugin 无法解析 | QML2_IMPORT_PATH 检查 | 补导入树根目录 |

### 排除豁免的写法（审核合规）

依赖在仓但 QML 绑定不在仓时，**不能用"缺依赖"口径**（审核规则 rule4：缺依赖必须解决依赖跑通）。合规写法：

- 逐项列出排除测试 + **具体报错文本 + 文件:行号**（`tst_sounds.qml:11,1: module "QtMultimedia" is not installed`）
- **实证根因**：制品包 qml/ 目录为空的实测证据（包结构事实，非本包缺陷）
- 受测面说明：C++ 消费侧（test_package 链接验证）覆盖了受测组件本体的可用性

## 红线

- ❌ 禁止"缺依赖"豁免口径（依赖在仓时）——审核员明确否决（PR #8714 审核实录）
- ❌ 禁止不加 can_run 守卫直接跑（交叉 CI worker 架构未知时）
- ❌ 禁止把 conan 缓存路径写死进配方（缓存目录随环境漂移）

## 实证记录

- kirigami-addons 1.13.0：tst_avatar 0.60s（AvatarTests/Colors/Actions 12 test function）+ tst_onboarding 1.42s（21 断言）全绿；tst_sounds + tst_album×3 定性为 qtmultimedia 制品包无 QML 绑定（`ls ~/.conan2/p/qtmul*/p/` 无 qml/ 目录实证）
- CI #41915 conan-build-test ✅（上游 autotests 构建+执行+test_package 全链路）
- 本机 OHOS PC arm64 主机可直接运行 aarch64 OHOS ELF（qmltest/qmltestrunner 直接执行）

## 与既有条目的边界

| 条目 | 主题 | 与本条关系 |
|---|---|---|
| E606（knotifications 链）ECMQmlModule | 构建期 include 陷阱（find_package 升级 REQUIRED） | 本条是**运行期**环境组合，互补 |
| E343/E344 | qtmultimedia 自身适配（shader 宏/媒体后端测试排除） | 本条揭示其制品包缺 QML 树的结构事实（下游视角） |
| qtscxml DRAFT | C++ Qt Test 子集（QT_BUILD_TESTS 变量模式） | 本条是 QML Quick Test 运行期注入，互补 |
| kcalendarcore #8667 | C++ Qt Test 的 CWD/lib 注入 | 本条扩展到 QML 系（+QML2_IMPORT_PATH/QPA），同族演进 |

## 适用范围

一切在 OHOS 适配的 QML 系包跑上游 Qt Quick Test：kdeclarative、kpimtextedit、kpublictransport、qqc2-desktop-style、所有 kirigami-addons 类 QML addon 库。
