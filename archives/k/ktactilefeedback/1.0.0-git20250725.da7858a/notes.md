# ktactilefeedback 1.0.0-git20250725.da7858a 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++（OHOS SDK，profile: ci/conan/profiles/ohos-aarch64）
- 状态: published（conan-verify G0-G4 PASS + W3 本地 CI 100% 通过）

## 编译步骤

```bash
# 1. 依赖发布检查（W0，R35 用 conan download 不用 conan list）
conan download qtbase/6.11.1 -r=ohpcd --only-recipe        # ✅ 已发布
conan download qtdeclarative/6.11.1 -r=ohpcd --only-recipe  # ✅ 已发布
conan download qtmultimedia/6.11.1 -r=ohpcd --only-recipe  # ✅ 已发布
conan download qtbase-sql-dbus/6.11.1 -r=ohpcd --only-recipe # ✅ 已发布
conan download extra-cmake-modules/6.29.0 -r=ohpcd --only-recipe # ✅ 已发布

# 2. 配方验证（conan-verify，8 道门禁 G0-G4 + L2/L4/L5）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify ktactilefeedback 1.0.0-git20250725.da7858a
# → G0-G4 全 PASS，可标 published

# 3. 收尾（finish 内含 W2 结构检查 + R36 依赖检查 + W3 conan create 编译验证）
python3 $SKILL_ROOT/scripts/ohc-run.py finish ktactilefeedback 1.0.0-git20250725.da7858a published
```

上游 CMake 由 conan create 驱动：`conan create <配方目录> -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`。
配方内 CMake 配置要点（generate() 注入）：`BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、
`KF_IGNORE_PLATFORM_CHECK=TRUE`、`CMAKE_CXX_STANDARD=17`、手动 `conan_cmakedeps_paths.cmake`
（qtbase 是 cmake_find_mode=none）、Qt6Qml/Qt6Multimedia/Qt6DBus 的 DIR CACHE 项、
`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`（OHOS 平台模块未定义 soname 标志）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 FAIL：`Error relocating .../libapp_context.z.so: _ZTVSt12length_error: symbol not found` | OHOS SDK lld 链接平台库时需要 SDK llvm/lib（含 libc++_shared.so 等）在 LD_LIBRARY_PATH（知识 E501） | build() 探测 SDK lib 目录（`cc_dir/../lib/aarch64-linux-ohos`、`cc_dir/../ohos-sdk.org/*/...`、`cc_dir/../lib`），将命中目录 prepend 到 LD_LIBRARY_PATH 再 configure/build |
| 2 | 上游测试 `qdeclarativefeedback` 失败：`module "org.kde.tactilefeedback" is not installed` | qmldir 声明模块 URI `org.kde.tactilefeedback`，但源码树 qmldir 位于 `src/imports/feedback/`；QML 引擎按 `<import-path>/org/kde/tactilefeedback/qmldir` 查找，测试运行于 package() 之前模块尚未组装 | `_run_upstream_tests()` 中构建 staging 目录 `<build>/qml-imports/org/kde/tactilefeedback/`，拷入 qmldir、plugins.qmltypes 与编译产物 libdeclarative_feedback.so，QML2_IMPORT_PATH/QML_IMPORT_PATH 指向该 staging 根 |
| 3 | test_package configure 失败：找不到 Qt6CoreConfig.cmake | qtbase/6.11.1 为 cmake_find_mode=none，CMakeDeps 不生成 Qt6 组件 config；KTactileFeedbackConfig.cmake 内部 `find_dependency(Qt6Core)` 需要 Qt6_DIR/Qt6Core_DIR/CMAKE_PREFIX_PATH | test_package build() 显式传 `Qt6_DIR`、`Qt6Core_DIR`、`CMAKE_PREFIX_PATH`（指向 qtbase package 的 lib/cmake）给 cmake.configure() |
| 4 | test_package 编译失败：`QFeedbackActuator` 头找不到 | 上游将 forwarding 头安装到 `include/KTactileFeedback/`（`QFeedbackActuator` 转发 `qfeedbackactuator.h`），但导出 target 未附 INTERFACE_INCLUDE_DIRECTORIES（KDE 消费者从 `TactileFeedback_INSTALL_PREFIX` 自行推导） | test_package CMakeLists 按 KDE 惯例 `target_include_directories(... PRIVATE "${TactileFeedback_INSTALL_PREFIX}/include/KTactileFeedback")` |
| 5 | test_package 编译失败：`staticMetaObject` 指针/值、QVariant 不完整 | Qt6 中 `staticMetaObject` 是 `const QMetaObject` 值而非指针；缺 `<QVariant>` include | test.cpp 改用 `const QMetaObject &mo = ...::staticMetaObject` 并补 `#include <QVariant>` |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-hfd-service-find-qt6dbus.patch | hfd-service/CMakeLists.txt 增加 `find_package(Qt6 COMPONENTS DBus)`，使 qt_add_dbus_interface 宏在干净构建中可用（Qt6DBus 由 qtbase-sql-dbus/6.11.1 提供） |

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓 |
|------|------|------|--------|
| qtbase | 6.11.1 | runtime/lib | ✅ 已发布 |
| qtdeclarative | 6.11.1 | runtime/lib | ✅ 已发布 |
| qtmultimedia | 6.11.1 | runtime/lib | ✅ 已发布 |
| qtbase-sql-dbus | 6.11.1 | runtime/lib（提供 Qt6DBus 组件） | ✅ 已发布 |
| extra-cmake-modules | 6.29.0 | tool | ✅ 已发布 |
| dbus / expat / qtshadertools | 传递依赖 | runtime | ✅ 已发布（Cache） |

版本冲突处理：qtdeclarative/qtmultimedia pin qtbase/6.11.1，故配方 require `qtbase/6.11.1`（非 6.11.1.x 变体）；
Qt6DBus 组件不在 qtbase 精简二进制中，需同时 require `qtbase-sql-dbus/6.11.1`（同源 Qt 6.11.1，+Sql/+DBus）。

## 验证结果（R51 上游测试三步法）

**清点**：上游 autotests/ 共 5 个子目录（qfeedbackactuator / qfeedbackhapticseffect / qdeclarativefeedback /
qfeedbackmmk / qfeedbackplugin），其中 **4 个注册进 CTest**（CMakeLists.txt 中 add_subdirectory 四个，
qfeedbackplugin 目录未注册）：

| 测试 | 注册 | 实测结果（conan create 内 ctest） | 说明 |
|------|------|------|------|
| qfeedbackactuator | ✅ | ✅ Passed（4/4 用例） | 枚举/setEnabled |
| qfeedbackhapticseffect | ✅ | ✅ Passed（envelope TEST1/TEST2/TEST3/TEST period 等全过） | 包络属性 |
| qdeclarativefeedback | ✅ | ✅ Passed（hapticsEffect/fileEffect/actuator/themeEffect 全过） | QML import 实测 |
| qfeedbackmmk | ✅ | ⏭️ SKIP（No audio devices available → Test Passed） | MMK 后端需音频硬件，offscreen 无设备，上游自带 skip 逻辑 |
| qfeedbackplugin | ❌ 未注册 | N/A | 上游未纳入 CTest |

**实测命令**（conan create 内 build() 自动执行）：
```bash
ctest --test-dir <build/Release> --output-on-failure --no-tests=error --timeout 120
# 结果: 4 tests, 3 Passed + 1 (mmk SKIP 计 Passed), 0 Failed
```

**test_package 实质验证（R34）**：test.cpp 构造 QFeedbackEffect/QFeedbackActuator，校验
meta-object 类名、Effect 枚举、actuator property 系统，ctest `test_ktactilefeedback` Passed（1/1）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Qt6 多组件 + E501/E092 处理） |
| conandata.yml | 官方 invent.kde.org 源码 + sha256 + 补丁声明 |
| test_package/ | R34 实质测试（conanfile.py + CMakeLists.txt + test.cpp + MANIFEST.yml） |
| patches/0001-hfd-service-find-qt6dbus.patch | hfd-service Qt6DBus 补丁 |
| manifest.yaml | 版本级元数据 |
| reports/conan-verify-report.md | 验证报告（verdict=PASS） |

## 注意事项

- R38：ktactilefeedback 是纯库（.so），无 CLI 可执行产物，不需要 commands.json。
- R26：无系统同名库（KTactileFeedback 非系统库名），动态链接由 Conan 管理依赖链。
- E501 的 LD_LIBRARY_PATH 注入仅限本地构建期 subprocess（os.environ 修改在 build() 内，
  通过 CMake/ctest 子进程生效），不注入 /usr/local 系统前缀（R49 合规）。
- qfeedbackmmk 测试在无音频设备环境 SKIP 属上游预期行为（initTestCase 显式 skip），非适配缺陷。

## 对话记录

### 对话 #1 (2026-09-27) — 续接编译验证
- 盘点上一子任务遗留产物：conanfile.py（含 E501 修复）/ conandata.yml / test_package/ /
  patches/0001-hfd-service-find-qt6dbus.patch / manifest.yaml / notes.md（模板）/ reports。
- W1 同步 main → 创建 feat/ktactilefeedback-1.0.0-git20250725.da7858a 分支；备份产物到
  /storage/Users/currentUser/tmp/ktactilefeedback-backup/。
- W0 依赖发布检查：qtbase/qtdeclarative/qtmultimedia/qtbase-sql-dbus/extra-cmake-modules
  全部已发布（conan download --only-recipe 验证）。
- conan-verify 首次验证：E501（OHOS SDK lld 需 SDK llvm/lib 在 LD_LIBRARY_PATH）已由
  conanfile.py 修复；暴露 4 个上游 autotest 中 qdeclarativefeedback 失败
  （module "org.kde.tactilefeedback" is not installed）。
- 修复 1：_run_upstream_tests() 增加 QML staging（qml-imports/org/kde/tactilefeedback/，
  拷入 qmldir/plugins.qmltypes/libdeclarative_feedback.so），QML2_IMPORT_PATH/QML_IMPORT_PATH
  指向 staging → qdeclarativefeedback 6 用例全 PASS。
- 修复 2：test_package configure 找不到 Qt6CoreConfig（qtbase cmake_find_mode=none），
  build() 显式传 Qt6_DIR/Qt6Core_DIR/CMAKE_PREFIX_PATH。
- 修复 3：test_package 编译找不到 QFeedbackActuator 头（上游导出 target 无 include 路径），
  CMakeLists 按 KDE 惯例加 ${TactileFeedback_INSTALL_PREFIX}/include/KTactileFeedback；
  test.cpp 修正 Qt6 staticMetaObject 值语义 + 补 QVariant。
- conan-verify G0-G4 全 PASS。
- finish W3 本地 CI：predl 误匹配 conandata.yml 注释中的裸 https:// URL 导致 source()
  NotADirectoryError → 注释去掉 https:// 前缀 + 清理 conan 缓存后 W3 Success 1/1。
- 产出：conan-verify-report.md（PASS）、test-report.md、packaging tar.gz、.ci-result.json（exit_code=0）。

---

**编译结束**: 2026-09-27 18:46
**最终状态**: published
