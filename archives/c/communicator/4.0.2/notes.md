# communicator 4.0.2 适配笔记（HarmonyOS PC / aarch64）

## 软件概况

KDE Maui Communicator 4.0.2：联系人管理桌面应用（Qt6/QML，`qt_add_qml_module`
URI `app.maui.communicator`，`NO_PLUGIN`）。**纯可执行程序**，无库产物。
License：GPL-3.0-or-later。

- 官方归档：https://download.kde.org/stable/maui/communicator/4.0.2/maui-communicator-4.0.2.tar.xz
- SHA256：`60bc8b5b5f56d81229fccfe1fa52f256ff0b1326b6dc6eb62544939aa64d31fb`（本地 sha256sum 核验一致）
- 构建：CMake ≥3.16 + ECM（KF 版本坐标 5.240）+ Qt6 ≥6.5.2 + KF6 + MauiKit4

## 依赖闭包（收窄后）

| 依赖 | 角色 | 裁剪/保留结论 |
|---|---|---|
| qtbase/6.11.1 | Core/Gui/Widgets/Concurrent | 保留。**Qt6 Widgets 不可裁**：非 Android 分支 `main.cpp` 直接使用 `QApplication`（QtWidgets），属真实源码级依赖；且 KF6::KIOGui→KF6::JobWidgets 亦传递要求 Widgets |
| qtdeclarative/6.11.1 | Qml/Quick/QuickControls2 | 保留 |
| ki18n/6.14.0 | KF6::I18n | 保留 |
| kcoreaddons/6.14.0 | KF6::CoreAddons | 保留 |
| kservice/6.14.0 | KF6::Service | 保留（上游 CMake 样板要求，源码未直接使用符号） |
| kcontacts/6.14.0 | KF6::Contacts（VCardConverter/Addressee 深度使用） | 保留，不可最小化裁剪。ohpcd 现有 6.14.0/6.18.0（2026-09-26 探测）；选 6.14.0 与 KF6 6.14 家族同轴——ci-run-3 实测 6.18.0 的 kconfig/kcodecs 6.18 精确 pin 与 mauikit/kio 6.14 族同图冲突 |
| kio/6.14.0 | KF6::KIOCore/KIOGui | **移除**（patches/0002，ci-run-2 实测）：源码零 KIO 符号使用（纯 CMake 样板）；且 kio 6.14 家族（kio/kbookmarks/kcompletion/kconfigwidgets/kxmlgui）精确 pin kcodecs/6.14.0，与当时 pin 的 kcontacts/6.18.0（kcodecs/6.18.0）同图冲突（Conan 2 拒绝同包双精确 pin，override 仅对版本范围有效）；该冲突根源后由 kcontacts 对齐 6.14.0 消除，KIO 维持移除（零符号使用） |
| kcodecs | kcontacts/6.14.0 传递依赖 | 无直连 require：消费者 override 对精确 pin 无效（直连 6.18.0/6.14.0 实测均报 Conflict，graph-info-2.txt）；现全 KF6 闭包统一 6.14.0，同图仅剩单一 kcodecs pin |
| kpeople | KF6::People | **已裁剪**（见下） |
| mauikit/4.0.2.1 | MauiKit4 Core（MauiApp/MauiList） | 保留 core。4.0.2 包实测（2026-09-21）仅含 controls 核心组件（无 MauiKitFileBrowsing4Config.cmake、无 filebrowsing QML 模块），上游唯一使用点 main.qml 头像选择对话框由 patches/0002 改用 QtQuick.Dialogs 等价实现（保留 callback(paths) 契约、本地路径字符串）；pin 取 4.0.2.1 重发布版——4.0.2 的 OHOS 构建未进入 UNIX 平台分支、WindowShadow QML 类型缺失（ci-run-11 唯一失败点），修复后按 R37 惯例以 4.0.2.1 合入 main 并发布 ohpcd（2026-09-29 conan list 探测在册） |
| ecm/6.20.0 | tool_requires（KDE cmake 模块） | 保留 |

### KIO / FileBrowsing 裁剪（patches/0002，上游 CMake 样板）

- 源码扫描实证：`grep -rn 'KIO' src --include='*.cpp' --include='*.h'` 零命中；
  FileBrowsing 仅 main.qml 的 import 与一个头像选择对话框组件（C++ 零使用）。
- FileBrowsing 阻塞：已发布 mauikit/4.0.2 包不含 FileBrowsing 组件
  （find_package 必失败）。kcodecs 精确 pin 冲突（ci-run-2/3：Conan 2
  无法在同一图中解析同包双精确 pin，消费者 override 仅对范围生效——直连
  kcodecs/6.18.0 实测仍报 Conflict，见 graph-info-2.txt）最终以 kcontacts
  对齐 6.14.0 根治（ohpcd 已发布 kcontacts/6.14.0），KIO 维持移除。
- 处置：CMake 去掉 KIO 组件与 FileBrowsing 组件及对应链接项；main.qml
  改用 QtQuick.Dialogs（qtdeclarative 自带），保留 callback(paths) 契约
  并剥离 file:// 前缀（KContacts Picture::setUrl 期望本地路径）。
  补丁已验证：对 pristine tar 应用后与预期树逐字节一致。

### KPeople 裁剪（patches/0001，能力探测优于平台名硬编码）

- KPeople 仅在 `src/interfaces/linuxinterface.cpp` 的 `getContacts()` 中使用
  （`KPeople::PersonsModel` + `KPeople::PersonData` 用于枚举 vCard 联系人）。
- 补丁改为能力探测：`find_package(KF6People CONFIG QUIET)`；找到则链接
  `KF6::People` 并定义 `HAVE_KPEOPLE`（原代码路径原样保留在 `#ifdef` 内）；
  未找到则回退为直接扫描共享 vCard 目录（`QDirIterator` 遍历
  `$XDG_DATA_HOME/kpeoplevcard/*.vcf`，与 KPeople vcard 后端同源，且即上游
  `getContacts()` 中被注释掉的原始实现路线）。
- 附带恢复 `vCardData()` 中被上游注释的 `FMH::MODEL_KEY::N`（`adr.name()`），
  使回退路径的联系人模型有名称字段。
- 不改任何测试 oracle：上游无测试（见下节）。

### HarmonyOS 桌面分支与 Qt6 QML 组件解析（ci-run-4/5，patches/0003 + 配方桥接）

- ci-run-4：`find_package(Qt6 COMPONENTS Qml)` 失败——Qt6Config.cmake 解析
  Qml/Quick 组件只搜 qtbase 自身 lib/cmake 前缀。修复：generate() 设
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qtdeclarative 包目录>`（baloo 6.28.0 /
  akonadi 25.12.3 先例）。
- ci-run-5：generate 阶段 `KF6::Contacts` 目标未定义——上游顶层平台分支
  `elseif(UNIX)` 在 OHOS 上不进入：CMake 无 Platform/HarmonyOS 模块，UNIX 变量
  保持未设置，`find_package(KF6 COMPONENTS Contacts)` 与 Widgets 检查被整体跳过
  （REQUIRED-found 列表无 KF6Contacts 可证），而 src/CMakeLists.txt 的非 Android
  链接分支无条件链接 KF6::Contacts。修复：patches/0003 将分支条件改为
  `elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`（知识库 E140/E092：
  不设 CMAKE_SYSTEM_NAME=HarmonyOS 以外，推荐增加 HarmonyOS 匹配分支；不改
  测试 oracle——上游无测试）。
- 设备 `patch`（toybox 0.8.12）对行数/位置不匹配的 hunk 会静默 no-op 或误报，
  本 run 补丁验收一律以 conan 实际使用的 patch_ng 为准。

### MauiKit4 头文件路径与邮件能力（ci-run-6，patches/0004/0005）

- ci-run-6：configure 全过，进入真实编译。两类编译错误：
  1. `'MauiKit4/Core/fmh.h' file not found`——已发布 MauiKit4 导入目标只声明
     `INTERFACE_INCLUDE_DIRECTORIES=<prefix>/include/MauiKit4/Core`，而源码 include
     `<MauiKit4/Core/...>`；此前该 include 根由被裁剪的 FileBrowsing 组件带入。
     修复：patches/0004 显式 `target_include_directories(... ${MauiKit4_INSTALL_PREFIX}/include)`。
  2. `'KEMailClientLauncherJob' file not found`——communicator.cpp 邮件转发用
     KDE PIM pimcommon 的 KEMailClientLauncherJob（0002 的 KIO 扫描未覆盖 PIM 符号）。
     pimcommon 未发布且拖 Akonadi 闭包，不可入图。修复：patches/0005 以
     `__has_include` 能力探测（与 0001 KPeople 同范式）：无 PIM 时回退
     `QDesktopServices::openUrl(mailto:)`——即上游自己的 Android 分支实现与被注释的
     fallback 路线，不新增依赖、不加测试 oracle。

### 可执行包安装门与运行桥（ci-run-7，patches/0003 扩展 + test_package 桥接）

- ci-run-7：conan create 首次全程通过（17/17 缓存命中打包），但包内无
  bin/communicator——顶层 `if(UNIX AND NOT APPLE AND NOT ANDROID)` 的
  install(TARGETS)（与 include(KDEInstallDirs) 门，共两处）在 OHOS 上同样被
  跳过。扩展 patches/0003：两处门均改为 `(UNIX OR CMAKE_SYSTEM_NAME STREQUAL
  "HarmonyOS") AND NOT APPLE AND NOT ANDROID`（与 elseif 分支同一 HAR 技术判
  断，不改 oracle）。
- 产物实测 DT_NEEDED 含斜杠限定绝对路径（~/.conan2/p/<phash>/p/lib/libKF6*.so，
  kio 分支同款发布态）；test_package test() 移植 kio 6.14.0 的 cache-root
  bridge（为烘焙前缀建 symlink，best-effort 不致失败）+ LD_LIBRARY_PATH +
  offscreen + 可写 HOME/XDG_RUNTIME_DIR（kio 先例），使 PR-check worker（conan
  根不同）亦可运行。

### maui-accounts manifest 安装目标（ci-run-8，patches/0003 追加 hunk）

- ci-run-8：bin/communicator 与 .desktop 成功装入包内；install 阶段仅剩
  上游硬编码绝对路径 `DESTINATION /usr/share/maui-accounts/manifests`
  （Nemo/Sailfish 约定）在 conan 沙箱（非 / 根）不可写而失败。追加 hunk：
  改为 `DESTINATION ${KDE_INSTALL_DATADIR}/maui-accounts/manifests`（前缀内
  相对路径，可打包、可重定位；manifest 消费方在 OHOS PC 无 /usr 约定）。

### 运行时冒烟双重根因：test_package QML import path 缺失（边界内）+ 已发布 mauikit/4.0.2 包缺陷（边界外，已由 4.0.2.1 修复重发布解决）

- ci-run-11/12/13：conan create 全过、包内 bin/communicator 就位；offscreen
  冒烟中 Qt6 与 MauiKit C++ 初始化成功（"CREATING INSTANCE OF MAUI APP"），
  但 QML 引擎在 main.qml 第 3 行即失败：`module "QtQuick.Controls" plugin
  "qtquickcontrols2plugin" not found`（rc=255）。该报错既可能源于 import
  路径缺失，也可能是插件加载失败——两个根因在此叠加，逐层剥离后分别取证。
- 根因 A（本 run 边界内，test_package 冒烟环境，已修复）：
  1. conan Qt 各模块独立包前缀：QML 模块在 qtdeclarative 包根 `qml/`
     （qtquickcontrols2plugin.so 位于 qml/QtQuick/Controls/）与 MauiKit 包
     `lib/qml/`；而 QtCore 烧死的 QmlImportsPath 指向 qtbase 包——qtbase
     包内并无 qml/ 目录 → 引擎默认 import 路径找不到任何 QML 模块。
  2. conan `self.run(..., env="conanrun")` 的子进程不会继承
     `Environment().apply()` 写入 os.environ 的变量（ci-run-13 实证：
     env.append 的 QML2_IMPORT_PATH 不生效，失败点与 ci-run-12 完全相同）
     → 改为与 CONAN_BIN_DIRS 同款的命令行显式传参
     `CONAN_QML_IMPORT_PATH=`，由 test.sh 导出为制品内 libQt6Qml.so 实际
     读取的 QML2_IMPORT_PATH / QML_IMPORT_PATH（strings 实证两个变量名
     均在该制品内）。
- 根因 B（边界外，已发布 mauikit/4.0.2 包的平台分支缺陷，与 0003 同根因类；
  由 mauikit run 修复并按 R37 惯例以 mauikit/4.0.2.1 合入 main、发布 ohpcd，
  本 run pin 升级消费之）：
  1. 上游 v4.0.2 `src/CMakeLists.txt`：`if(ANDROID) … elseif(UNIX AND NOT
     APPLE)` 分支才编译 `platforms/linux/shadowhelper/windowshadow.{h,cpp}`
     （`class WindowShadow` 带 `QML_ELEMENT`，即 WindowShadow 类型的唯一来源）。
  2. OHOS 构建时 CMAKE_SYSTEM_NAME=HarmonyOS、UNIX 未设置 → 任何平台分支都未
     进入 → 已发布 4.0.2 包 `MauiKit4.qmltypes` 中 WindowShadow 命中数为 0
     （conan cache 实测），qmldir 亦无该项；而包内 QML
     `private/BaseWindow.qml:52` 无条件引用 `Maui.WindowShadow`
     （communicator main.qml → Maui.ApplicationWindow → BaseWindow 必达）。
  3. 4.0.2.1 包对照实测：qmltypes 含
     `exports: ["org.mauikit.controls/WindowShadow 1.0"]`，
     lib/libMauiKit4.so WindowShadow 命中 121（conan cache 对照，同 package_id
     不同 recipe revision）。
- 收敛（ci-run-14，2026-09-29）：A+B 双修复后权威 CI 全绿——L0/L1/L5 pass、
  conan create + test_package 全过（Build Summary Success 1/1, 100%）、
  offscreen 冒烟进入事件循环（rc=124 → OK，日志出现 "REGISTER MAUIKIT
  TYPES"）。ci-run-12 为 pin 升级后首跑（重建包），ci-run-13 为 import
  path 第一方案（env.apply 不透传）的证伪轮，均留档 run logs/。

### Qt6 Widgets 裁剪评估结论

不可裁。两处证据：`src/main.cpp` 非 Android 分支 `#include <QApplication>` +
`QApplication app(...)`（QtWidgets）；以及即便移除显式依赖，KF6::KIOGui →
KF6::JobWidgets 传递要求 Widgets。qtbase 本就提供 Widgets，裁剪无收益。

## 阻塞与缺口（ci-run-1 结论，2026-09-16 起已解除）

> 2026-09-16 复核：kio/6.14.0 与 mauikit/4.0.2 均已发布到 ohpcd 制品仓
> （kio run、mauikit run 先后入库），ci-run-1 的 L0i 阻塞不再存在。
> mauikit 已发布包是否含 FileBrowsing 组件待 conan create 实测。

1. **mauikit/4.0.2 未发布**（当时）：ohpcd 制品仓无 `mauikit/*`。MauiKit4
   FileBrowsing 是上游硬性
   `find_package(MauiKit4 REQUIRED COMPONENTS FileBrowsing)`。
   本 run 写入边界只覆盖 `archives/c/communicator/**`，无法补前置 recipe。
2. **kio/6.14.0 未发布**（当时）：ohpcd 制品仓 `conan list 'kio/*' -r=ohpcd`
   为空；设备 conan 本地缓存有未入库 recipe
   （`~/.conan2/p/kio1336007621eaf/`，含 14 个补丁，只读参考未改动）。
3. CI L0i（R36 依赖发布检查）按设计拦截以上两项：
   `conan download <ref> -r=ohpcd --only-recipe` 对不存在包返回
   `ERROR: error:system acceleration policy not enabled`（cnb.cool 对缺失
   recipe 的报错形态，不匹配 CI 的 "not found/404" 归类正则，会被计为
   registry unreachable 而非 unpublished——失败效果相同，归因口径需注意）。

## NO_UPSTREAM_TESTS 证据

- 检查入口：tarball 顶层无 `tests/`、`autotests/` 目录；全部 CMakeLists.txt /
  *.cmake 无 `enable_testing` / `add_test` / `ECMAddTests` / `ctest`；
  无 `CMakeConfig.cmake` / `CTestTestfile.cmake` / `CTestConfig.cmake`；
  源码无 `QTEST` / `QSignalSpy`。原始扫描输出：
  `reports/upstream-test-scan.log`。
- 结论：上游 4.0.2 不提供任何测试套件，质量验证以 test_package 的安装产物
  offscreen 冒烟为准（参照 DRAFT-box2d-2.4.1：无 CTest 注册时必须直接执行
  测试可执行文件，禁止以 `ctest` 空套件退出码 0 冒充通过）。

### upstream-test-scan 原始输出（随 PR 交付存档）

原 `reports/upstream-test-scan.log` 按惯例仅存设备、不随 feat 分支交付（C 证据包缺口清单 #7 的证据归属问题）；按其处理选项将全文摘录如下（2026-09-13T12:01:33+08:00 扫描：顶层清单 + 四项检查——tests/autotests 目录、CMake 测试入口、CTest 配置、Messages.sh/源码内测试可执行——均无测试套件命中，与上节结论互证）：

```
# NO_UPSTREAM_TESTS discovery scan — maui-communicator-4.0.2
# date: 2026-09-13T12:01:33+08:00

== top-level entries ==
CMakeLists.txt
LICENSE
Messages.sh
logo.png
org.kde.communicator.appdata.xml
org.kde.communicator.desktop
org.kde.communicator.json
po
src

== tests/autotests dirs ==
(exit 0)

== CMake test entry points ==
(no matches)

== CTest configs ==
(none)

== test executables in Messages.sh/sources ==
(no matches)
```

## 复现要点（依赖补齐后）

- 走权威 CI：`ci/conan/build_and_test.sh`，`CI_PACKAGES=archives/c/communicator/4.0.2`，
  profile `ci/conan/profiles/ohos-aarch64`。
- test_package 以 `QT_QPA_PLATFORM=offscreen` 启动安装的 `communicator`，
  Qt 初始化成功进入事件循环（rc=124 超时）即通过；禁用 `--help/--version`
  之外的强交互假设。
- 注意 CI 的 mirror-fallback/预下载只对 github/gnu/gnome/kernel 等 host 触发，
  `download.kde.org` 不在改写列表；CI 后仍按 E415 核验 conandata.yml 逐字节
  一致。
