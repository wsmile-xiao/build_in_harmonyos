# notes — alligator 26.04.0 (HarmonyOS PC；KDE Plasma Mobile 播客/RSS 阅读器)

## 身份与来源

- 上游: https://invent.kde.org/network/alligator（KDE Plasma Mobile）
- 归档: https://download.kde.org/stable/release-service/26.04.0/src/alligator-26.04.0.tar.xz
- SHA256: 9c757421c0c6b10f989dfb60c184e1da08fa36f91d09c6dcd40e78e7dce24edf
  （设备端 sha256sum 实算，与官方 release-service 一致）
- 版本: 26.04.0（KDE Gear 26.04.0），git tag v26.04.0
- license: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
- 平台任务 #975（积分赛，taskBranch=feat/alligator-26.04.0，认领人 j669539）

## 产物

- bin/alligator — 馨鱼 RSS/播客阅读器主程序（QML 内嵌 qrc:/qt/qml/org/kde/alligator，
  Kirigami UI，SQLite 存储，KF6::Syndication 解析订阅）
- share/applications、share/metainfo、share/icons — desktop 元数据（上游安装规则）

## W0 依赖预检（全部 conan download -r=ohpcd 实测在仓）

- qtbase-sql-dbus/6.11.1（Core/Gui/Widgets/Test/Sql/DBus 组件），qtdeclarative/6.11.1
  （Qml/Quick/QuickControls2 + Qt.labs.platform/qmlmodels QML 模块），qtsvg/6.11.1，
  qtshadertools/6.11.1
- KF6：kcoreaddons/ki18n/kconfig/kcolorscheme/kcrash/kitemmodels 6.18.0、
  kirigami/6.18.0、kirigami-addons/1.13.0、syndication/6.26.0（rrev ecaa3dd6，
  注意本地缓存旧 rrev e12d1156 已在远端删除，需 conan remove 后重新 download）
- ecm/6.26.0（tool_requires）
- 依赖图 25 包全解析（含 qtbase/6.11.1 与 qtbase-sql-dbus/6.11.1 双变体共存，
  分别被 KF6 6.18 系与 kirigami 系二进制引用，无冲突）

任务侦察关注的两大风险变量实测结果：
- Syndication：**在仓**（syndication/6.26.0，2026-09-10 发布）
- KirigamiAddons：**在仓**（kirigami-addons/1.13.0，2026-09-09 发布，依赖链完整）
- 结论：无依赖缺口，无需报主任务定夺。

## 适配要点（三个 patch）

1. **0001 QQC2BreezeStyle 禁用**：上游 CMakeLists 在非共享构建时 find_package
   (QQC2BreezeStyle REQUIRED)，qqc2-breeze-style 不在仓。OHOS 共享构建本来就不
   触发该分支，但移除 find_package 防配置失败。
2. **0002 KF6::I18nQml → KF6::I18n（KLocalizedContext）**：
   - 上游 main.cpp 用 KLocalizedQmlContext + KLocalization::setupLocalizedContext()
     （ki18n src/i18n-qml，KF6::I18nQml target），制品仓 ki18n 全版本未构建该组件。
   - 在仓 ki18n/6.18.0 提供 KLocalizedContext（同机制的前代 API，上游仅 6.8 弃用
     改名），kirigami-addons 1.13.0 autotests 同款用法先例
     （engine->rootContext()->setContextObject(new KLocalizedContext(engine))）。
   - 陷阱：KLocalizedContext 头被 `#if KI18N_ENABLE_DEPRECATED_SINCE(6, 8)` 包裹，
     而 alligator 的 ecm_set_disabled_deprecation_versions(KF 6.12.0) 会把
     KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT 定义为 6.12 → 类直接不可见（unknown
     type name）。解法：src/CMakeLists.txt 加
     `target_compile_definitions(alligator PRIVATE KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0)`
     （命令行宏优先于 ki18n_export.h 头内的条件默认值）。
   - 同时把链接的 KF6::I18nQml 从 target_link_libraries 移除。
3. **0003 org.kde.coreaddons AboutData → Kirigami.AboutPage + JSON**：
   - Main.qml `import org.kde.coreaddons`（AboutData 单例）+ `aboutData: AboutData`。
     org.kde.coreaddons QML 模块不在仓（kcoreaddons 配方 KCOREADDONS_USE_QML=OFF，
     上游 src/qml/kcoreaddonsplugin 只注册 AboutData/KTextToHTML 两个单例）。
   - kirigami-addons FormCard.AboutPage **自身**也无条件 import org.kde.coreaddons
     （AboutPage.qml:12 "import org.kde.coreaddons as Core"，qmldir depends 声明），
     引用即触发 "module not installed" 编译期失败。
   - 解法：改用 kirigami 自带的 Kirigami.AboutPage（org.kde.kirigami 模块内，
     无 coreaddons 依赖），aboutData 用其官方支持的 JSON 对象形式
     （与 KAboutData 同 shape，值取自 main.cpp 的 KAboutData 字段）。
4. **0002 内同时包含 QQuickStyle 样式回退**：main.cpp 非 Android 分支
   `QQuickStyle::setStyle("org.kde.desktop")`（qqc2-desktop-style 不在仓）→
   改为 "Basic"（qtdeclarative 内建样式），同时保留
   QT_QUICK_CONTROLS_STYLE 环境变量覆盖能力。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | syndication 二进制 Missing prebuilt package | 本地缓存残留旧 rrev e12d1156（远端已删），conan 图解析到旧 rev 的 package_id 无二进制 | `conan remove syndication/6.26.0 -c` 后重新 download，图即用最新 rrev ecaa3dd6（pkgid 5c5cd9f3 匹配） |
| 2 | conan create 早期 "patch stream is incomplete" | 手写 patch 文件尾部缺统一 diff 的尾部上下文/换行 | 全部 patch 改为 orig/work 目录 diff -u 生成，写入前 patch -p1 --dry-run 验证 |
| 3 | 编译 error: unknown type name 'KLocalizedContext' | KI18N_ENABLE_DEPRECATED_SINCE(6,8) 条件编译 + ecm_set_disabled_deprecation_versions(KF 6.12) | CMake target_compile_definitions KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0 |
| 4 | self-test: Error loading ../../bin/libKF6ConfigCore.so | E537：kconfig 二进制携带 build-tree 相对 DT_NEEDED，OHOS loader 按 CWD 解析 | 配方 _make_link_farm()：在 build 树根 bin/ 镜像全部依赖 .so（accessibility 26.04.3 先例）；test_package 则在 scratch 临时目录建 farm 作为运行 CWD |
| 5 | QML: module "org.kde.desktop" is not installed | QQuickStyle::setStyle("org.kde.desktop") 指向不在仓的 qqc2-desktop-style | 0002 内改 setStyle("Basic") |
| 6 | QML: FormCard.AboutPage → org.kde.coreaddons not installed | kirigami-addons formcard 模块 import org.kde.coreaddons | 0003 改用 Kirigami.AboutPage + JSON aboutData |
| 7 | test_package --self-test 挂起/失败 | 宿主 shell LD_LIBRARY_PATH 空格污染条目（"...chipset-pub-sdk:         /system/lib64"，kirigami-addons notes 问题1 同款）+ conanrun 聚合 QML2_IMPORT_PATH 不含 qtdeclarative qml/ 树 + QT_PLUGIN_PATH 缺失致 offscreen 插件找不到 | test_package test() 显式 env.define 重建完整 LD_LIBRARY_PATH/QML2_IMPORT_PATH/QT_PLUGIN_PATH（不继承污染值，不用 env="conanrun"），CWD 置于 scratch 目录使相对 DT_NEEDED 解析到 link farm |
| 8 | conan 缓存 550 条 b/ 悬空目录导致所有操作 FileNotFoundError | 历史本地构建的 build folder 目录被磁盘清理，cache.sqlite3 残留行 | 清理 cache.sqlite3 中 path LIKE 'b/%' 且目录不存在的行（523 条），install/create 恢复正常 |

## 测试说明（N 申报）

上游构建系统注册的 CTest add_test 数：**1**（autotests/CMakeLists.txt 的
alligator-self-test：alligator --self-test，250ms 自退出定时器）。
**已构建并在配方内真跑**（BUILD_TESTING=ON + _test_env：
QT_QPA_PLATFORM=offscreen + QML2_IMPORT_PATH 三级注入 + LD_LIBRARY_PATH
双布局收集 + link farm）：**1/1 PASS（0.92s）**——QML 引擎完整加载 Main.qml、
Kirigami ApplicationWindow、EntryListPage（数据库迁移 v3 输出正常），
事件循环 250ms 定时退出。

消费者侧：test_package 直跑 packaged binary `alligator --self-test`
（R34：真实执行，非空壳）——同样完整加载 QML UI 后干净退出（exit 0）。
离屏运行时 kirigami 打印三条预期内的环境警告（Basic 样式无 Kirigami platform
plugin → default Basic theme；Qt 无内嵌字体目录），不影响判定。

上游测试修改说明：无（上游 autotest 原样真跑）。补丁只影响 About 页呈现
（Kirigami.AboutPage 等价替换 FormCard.AboutPage）与样式回退（Basic 替代
org.kde.desktop，OHOS 无 KDE 桌面样式栈），核心阅读功能（订阅抓取/解析/存储/
UI）零改动。

## 验证结果

OHOS `conan create` verification（2026-09-11，clang 15.0.4 aarch64-linux-ohos）:
- 25 包依赖图全解析（全 Cache，无源码编译依赖）
- 主包构建+打包成功（含 OHOS ELF 签名 1 个：bin/alligator）
- 上游测试 1/1 PASS：alligator-self-test 0.92s
- test_package: 1/1 PASS（bin/alligator --self-test 完整 QML 加载 + 干净退出）
- 最终 conan create exit 0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（kirigami-addons 1.13.0 应用包打法：ECM/KF6 手工 cmake 路径 + OHOS ELF 签名 + link farm） |
| conandata.yml | 官方 tarball URL + SHA256 + 3 补丁清单 |
| patches/0001-CMakeLists-disable-qqc2breezestyle-for-ohos.patch | QQC2BreezeStyle 禁用 |
| patches/0002-main.cpp-use-KLocalizedContext-for-ohos.patch | KLocalizedContext 等价替换 + Basic 样式回退 + 弃用宏解除 + I18nQml 链接移除 |
| patches/0003-Main.qml-replace-coreaddons-AboutData-with-JSON.patch | Kirigami.AboutPage + JSON aboutData |
| test_package/ | conanfile.py（--self-test 真跑）+ test_app.sh（手动复现脚本）+ MANIFEST.yml |
| ../README.md ../commands.json ../26.04.0/manifest.yaml | 软件级/版本级元数据 |

---

**编译结束**: 2026-09-11 15:05
**最终状态**: built
