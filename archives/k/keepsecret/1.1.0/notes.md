# notes — keepsecret 1.1.0 (HarmonyOS PC；KDE Secret Service 密码管理器 GUI)

## 身份与来源

- 上游: https://invent.kde.org/utilities/keepsecret（KDE utilities）
- 归档: https://download.kde.org/stable/keepsecret/keepsecret-1.1.0.tar.xz
- SHA256: `d27a9925cd6b47de16fd29a7e18984e7a1524084eb614be110abdf279a0b57d1`
  （设备端 sha256sum 实算）
- SHA512: `a25ce3a65962887b02ea235fcd45bfcfa6f793f1568a22a9201b710e0d103b88
  11df89ba25c2a5d6b03e9125ace427f953bc1141a591c7730fa7c56d6f64c479`
  （与 Gentoo `app-crypt/keepsecret/Manifest` 的官方记录逐字一致，交叉验证通过）
- 版本: 1.1.0（上游 `project(keepsecret VERSION 1.1)`，release tarball 1.1.0）
- license: GPL-2.0-or-later（REUSE 合规，LICENSES/ 目录随源分发）
- 大小: 82100 bytes（与 KDE 官方 FTP 镜像 `keepsecret-1.1.0.tar.xz` 一致）
- 分支: `feat/keepsecret-1.1.0`（R40/L0n：分支名以 `<包名>-<版本>` 结尾）

## 任务性质判定

keepsecret 是 **KDE Plasma/Kirigami 桌面 GUI 应用**（非库），构建产物为
`bin/keepsecret` 单一可执行文件 + 内嵌 QML 模块 + desktop 元数据。核心功能是
作为 **Secret Service 兼容提供者**（KWallet / oo7 / gnome-keyring / KeepassXC）的
客户端，显示 secret collection 与 secret 条目。

数据链路有两条：
- **libsecret-1**：item/collection 数据模型（`secret_collection_*` / `secret_item_*`）
- **QtDBus**：Secret Service 客户端（`org.freedesktop.Secrets`，服务发现与 dbus 激活）

## 产物

- `bin/keepsecret` — 主程序（QML 内嵌 `qrc:/qt/qml/org/kde/keepsecret`，Kirigami UI）
- `bin/org/kde/keepsecret/` — 应用 QML 模块（qt_add_qml_module 产出）
- `share/applications`、`share/metainfo`、`share/icons` — desktop 元数据（上游安装规则）

## W0 依赖预检（R36：全部 `conan download -r=ohpcd` 实测在仓）

| 依赖 | 版本 | 状态 |
|------|------|------|
| qtbase-sql-dbus | 6.11.1 | 在仓（Core/Gui/Widgets/Test/Sql/DBus） |
| qtdeclarative | 6.11.1 | 在仓（Qml/Quick/QuickControls2 + QML 模块） |
| qtsvg | 6.11.1 | 在仓 |
| qtshadertools | 6.11.1 | 在仓 |
| kirigami | 6.18.0 | 在仓 |
| kirigami-addons | 1.13.0 | 在仓 |
| kcoreaddons | 6.18.0 | 在仓 |
| kconfig | 6.18.0 | 在仓 |
| ki18n | 6.18.0 | 在仓 |
| kitemmodels | 6.18.0 | 在仓 |
| kcrash | 6.18.0 | 在仓 |
| kdbusaddons | 6.18.0 | 在仓 |
| libsecret | 0.21.7 | 在仓（**0.21.8 仅本地目录未发布，故用 0.21.7**） |
| ecm | 6.26.0 | 在仓（tool_requires） |

**无依赖缺口**（仅需下述 zlib 图冲突消解）。

### 依赖图关键消解：zlib 版本冲突

裸装依赖图冲突：

```
Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.2 in the graph.
Conflict originates from glib/2.84.0.1
```

根因（`conan graph info --format=json` 实测依赖边）：

- `kirigami-addons/1.13.0` → `kiconthemes/6.18.0.1` → **`karchive/6.18.0` → `zlib/1.3.2`**
- `libsecret/0.21.7` → **`glib/2.84.0.1` → `zlib/1.3.1.1`**

**解法：根 override `zlib/1.3.2`**（不升 glib）。两次实测对照：

| 方案 | 结果 |
|------|------|
| `glib/2.88.3` override + `zlib/1.3.2` | ✗ `Missing prebuilt package for 'libsecret/0.21.7'` —— libsecret 已发布二进制是按 glib/2.84 闭包算的 package_id |
| **`zlib/1.3.2` override（glib 不动）** | ✓ 全图解析 + 二进制齐备（install finished successfully） |

即：**只能统一到 zlib/1.3.2 且必须保持 glib/2.84.0.1**。这与
`gnome-online-accounts` / `abiword-plugin-*` 系列配方同款做法。
若不 override，CI 的 `--build=missing` 会从源码重编 libsecret，而该 recipe 在
OHOS 上因 `proxy-libintl.pc` 缺失构建失败（实测），故 override 是必需项。

## 适配要点（六个 patch）

上游 CMake 强依赖 `Qt6 >= 6.8.0` / `KF6 >= 6.8.0`；在仓基线为 Qt 6.11.1 +
KF 6.18.0，**版本门槛无需下调**（全部满足）。真正的障碍是**制品仓缺失的 QML 模块**，
与 alligator / klevernotes 同一类问题：

### 1. KF6::I18nQml 不在仓（patch 0001 + 0002）

- 上游 `src/CMakeLists.txt` 链接 `KF6::I18nQml`，`main.cpp` 用
  `KLocalizedQmlContext`（ki18n `src/i18n-qml`）。
- 制品仓 ki18n **全版本以 `BUILD_WITH_QML=OFF` 构建**，该组件不存在。
- 替换为在仓的 `KLocalizedContext`（同一 QML i18n 上下文机制的**前代 API**，
  上游仅 6.8 弃用改名），`kirigami-addons` 1.13.0 autotests 同款用法先例。
- **陷阱**：`KLocalizedContext` 被
  `#if KI18N_ENABLE_DEPRECATED_SINCE(6, 8)` 包裹，而 keepsecret 的
  `ecm_set_disabled_deprecation_versions(KF 6.17.0)` 把
  `KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT` 定到 6.17 → 类不可见。
  解法：`target_compile_definitions(... KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0)`。

### 2. qqc2-desktop-style / qqc2-breeze-style 不在仓（patch 0002）

- 上游 `main.cpp` 默认 `QQuickStyle::setStyle("org.kde.desktop")`。
- 两种 KDE QQC2 样式均未发布；回落内置 `Basic` 样式（`QT_QUICK_CONTROLS_STYLE`
  仍可覆盖）。

### 3. org.kde.coreaddons QML 模块不在仓（patch 0003 + 0004）

- 在仓 `kcoreaddons/6.18.0` 以 **`KCOREADDONS_USE_QML=OFF`** 构建，无 QML 插件。
- `Main.qml` / `About.qml` 都 `import org.kde.coreaddons`，且
  `FormCard.AboutPage` 自身**无条件下** `import org.kde.coreaddons as Core`
  （`AboutPage.qml:12`，`property var aboutData: Core.AboutData`）→ 直接 import 报错。
- `About.qml` 改用 **`Kirigami.AboutPage`**（Kirigami 模块内、无 coreaddons 依赖，
  `Kirigami/AboutPage.qml` 仅 import QtQuick + kirigami），`aboutData` 传与
  `KAboutData` 同形的 **JS 字面量对象**（alligator 0003 先例）。
- `Main.qml` 的 `AboutData.version` → `Qt.application.version`。

### 4. org.kde.config QML 模块不在仓（patch 0004）

- `kconfig/6.18.0` 以 `KCONFIG_USE_QML=OFF` 构建，无 `org.kde.config`。
- `Main.qml` 的 `Config.WindowStateSaver` → **`QtCore.Settings`**
  （qtdeclarative 提供 QtCore QML 模块，`qml/QtCore/qmldir` 实测存在），
  以 `category: "MainWindow"` + alias 持久化窗口几何。

### 5. org.kde.kitemmodels QML 模块不在仓（patch 0005 + 0006）

- `kitemmodels` 配方**不 require qtdeclarative**（保持 Akonadi KF 最小基线），
  跳过 QML 插件；制品包内**无 `KSortFilterProxyModel` 头/符号**（实测）。
- `CollectionContentsPage.qml` 用 `KSortFilterProxyModel { sourceModel: ... }`
  （QML 类型），故新增 **`src/qmlsortfilterproxymodel.{h,cpp}`**：
  `QSortFilterProxyModel` 子类，`QML_ELEMENT` 注册进 org.kde.keepsecret 模块，
  暴露 `filterString` / `filterRole(Name)` / `filterCaseSensitivity` /
  `sortRole(Name)` / `sortCaseSensitivity`，与 KSortFilterProxyModel 的 QML 表面一致
  （roleName→role 经 `sourceModel()->roleNames()` 解析）。

> 说明：**未**尝试改 `kitemmodels` 配方打开 QML 插件——那会要求 kitemodels 新增
> qtdeclarative 依赖并重发二进制，属跨包基础设施改动（W2 一个配方一个 PR）。

## 上游测试清点（R51 三步法 · 第一步：适配前清点）

**结论：上游 keepsecret 1.1.0 确无测试套件。** 逐项证据：

| 清点项 | 方法 | 结果 |
|--------|------|------|
| tests/ autotests/ 目录 | `find` 全量 tarball | **不存在**（顶层 42 个条目无任何测试目录） |
| CTest 注册 | `grep add_test\|BUILD_TESTING\|enable_testing` 于 `CMakeLists.txt` + `src/CMakeLists.txt` | **0 命中**，无 `add_test()`、无测试子目录、无 QtTest 链接 |
| 上游 CI 声明的测试 | `.gitlab-ci.yml` / `.kde-ci.yml` | 仅构建与 clang-format/lint 检查，无测试作业 |
| 测试框架依赖 | `find_package` 全量 | 无 `Qt6Test` / `QtTest` |

因此配方 `build()` 中**不伪造 `make check`**：改为执行 `ctest -N` 并如实记录上游
注册状态（0 条），把"上游无测试"作为**可复核的实测结论**写进日志，而非静默跳过。
这一步同时满足 TEST_QUALITY_SPEC §3.3「不要删除 make check 调用」的精神——
本项目是**引用上游真实状态**并留下证据，不是删测试。

第二步（可运行环境实际运行）：上游无可运行测试，故交付物验证由 `test_package`
两层承担（见下）。第三步（PR 如实回填 N/N′）：PR 描述按实测填写。

## test_package（消费者视角验证，R34 真实调用）

`test_package/` 两层，**均为真实执行**，且第一层是**新增的鸿蒙特有测试**：

1. **`test_ohos_gate.py`（新增鸿蒙特有测试）** — 纯 stdlib ELF64 解析器，
   直接对**打包后的二进制**断言本端适配真实生效（不依赖 readelf 在 PATH 上，
   kio 6.14.0 先例）：
   - 目标为 **AArch64 ELF**（EM_AARCH64 = 183）；
   - **无 `libKF6I18nQml` DT_NEEDED** —— 证明 patch 0001/0002 的
     I18nQml 替换在**产物**上生效（不是只改了源码）；
   - **有 `libKF6I18n.so.6`** —— KLocalizedContext 来自 KF6::I18n；
   - **有 `libsecret-1.so.0`** —— Secret Service 后端确实链接进产物
     （证明 `pkg_check_modules(LIBSECRET)` 打通）；
   - **有 `libQt6Core/Qml/Quick`** —— QML 应用闭包完整。
   
   解析器已与 `readelf -d` **逐条交叉验证一致**（对 libQt6Core.so /
   libKF6I18n.so 实测 DT_NEEDED 完全吻合）。

2. **离屏启动冒烟** — 以 offscreen QPA + 完整 QML 导入闭包启动打包应用。
   keepsecret 无 `--self-test` 参数，故按 klevernotes 先例用退出码契约：
   `timeout` 击杀的 **124**（或 0）表示 QML 引擎成功加载 `Main.qml` 并进入事件
   循环；其他非零码表示启动崩溃或引擎失败（`rootObjects().isEmpty()` → `exit(-1)`）。
   注意：构建机上**没有 Secret Service 提供者**，这是 keepsecret 明确处理的运行
   时路径（`SecretServiceClient` 报 `ServiceConnectionError`，`Main.qml` 显示
   InlineMessage 错误横幅），故缺提供者**不算失败**。

运行时链接处理沿用 accessibility 26.04.3 / klevernotes 先例：scratch CWD + 双向
link farm 解决 KF6 库的构建树相对 DT_NEEDED（E537），并物化跨 conan home 的
绝对 DT_NEEDED；同时显式重建 `LD_LIBRARY_PATH`/`QML2_IMPORT_PATH`
（宿主 shell 的 LD_LIBRARY_PATH 含空格填充项，OHOS 加载器无法解析）。

## 验证记录回填

- `conan create`：**passed**（exit 0，日志 0 条 `^ERROR`）→ `reports/conan-create.log`
- W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）：**pass**，Pass rate 100.0% (1/1)
  —— G0 / G0e / JC(prdiff 17 文件) / L0 / L1 / L4 / L5 全 pass，L2 skip（GUI 无
  `--version`/`--help`，非阻断）→ `reports/w3-local-ci.log`
- `test_results` 各字段（`test_package` / `l0` / `l1` / `l2` / `l4` / `l5` /
  `w3_local_ci` / `conan_create`）已回填至 `manifest.yaml`

## PR

- **#13884** — 【积分赛】feat(keepsecret): 1.1.0 适配 HarmonyOS PC
- https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13884
- 源分支 `feat/keepsecret-1.1.0` → `main`（W2 原子性：仅含 `archives/k/keepsecret/`，17 文件）
