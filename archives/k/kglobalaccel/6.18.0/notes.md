# kglobalaccel 6.18.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (LLVM 15, aarch64-linux-ohos)
- 状态: published

## 编译步骤

基于已验证的本地配方 `/storage/Users/currentUser/localkf/kglobalaccel/6.18.0/conanfile.py`
（该配方已在 OHOS aarch64 + clang 上编译验证成功，作为 alligator/kirigami-addons 的依赖）。

模式 B 手动验证（BUILD_TESTING=ON，cmake）：
```bash
cmake <src> -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain> \
  -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=<paths.cmake> \
  -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON \
  -DWITH_X11=OFF -DKF_IGNORE_PLATFORM_CHECK=TRUE \
  -DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD_REQUIRED=ON \
  -DCMAKE_BUILD_TYPE=Release
ninja
ctest   # → No tests were found (exit 0)
```

正式配方经 `conan create`（conan-verify G2）验证，8 道门禁全过。

## 上游测试（R51 三步法）

### 1. 清点
- tests/ 目录：1 个测试源文件 `tests/kglobalacceltest.cpp`（+ `kglobalacceltest.qml`）
- **ctest 注册数：0**
  - `tests/CMakeLists.txt` 只用 `add_executable(kglobalacceltest ...)`，
    **没有调用 `ecm_add_test` / `add_test`**，上游本身未将其注册到 ctest。
  - `ctest -N` 输出 `Total Tests: 0`；`ctest --show-only` 同样 0 项。

### 2. 实际运行
- BUILD_TESTING=ON 下 **成功编译** `kglobalacceltest` 可执行文件
  （需要 Qt6Qml ← qtdeclarative build_requires；测试目标链接 KF6::GlobalAccel + Qt6::Qml + Qt6::Test）。
- `ctest` 运行：`No tests were found!!!`，**exit 0**（空套件通过，通过率 100%）。
- 尝试直接运行 `kglobalacceltest`（QT_QPA_PLATFORM=offscreen）：
  ```
  QQmlApplicationEngine failed to load component
  file://.../tests/kglobalacceltest.qml:11:1: module "org.kde.kquickcontrols" is not installed
  ```
  失败点定位：`tests/kglobalacceltest.qml:11` `import org.kde.kquickcontrols 2.0`
  （KeySequenceItem 来自 kiconthemes 的 QML 插件；已发布的 kiconthemes conan 包
  `KICONTHEMES_USE_QTQUICK=OFF` 不产出该 QML 模块）。即使有该模块，测试还需要
  运行中的 D-Bus session bus + kglobalacceld 守护进程 + 图形显示（QApplication +
  ApplicationWindow），在 OHOS 无头构建环境中不可运行。

### 3. 回填
- 上游测试：**0/0 ctest 注册，通过率 100%**（空套件）；`kglobalacceltest` 编译通过，
  运行时需要 kquickcontrols QML 模块 + DBus session + 显示（见 reports/upstream-tests.md）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | 源码无 configure 脚本特征时检测回退 | 手工覆盖为 cmake 配方（localkf 已验证） |
| 2 | 手动 ninja 构建时 lconvert/lrelease 报 "symbol not found" | qttools 宿主工具运行缺少正确 LD_LIBRARY_PATH | `source conanbuild.sh` 后重跑（conan 环境注入依赖 lib 路径） |
| 3 | conan-verify G1 缺 export_sources()/apply_conandata_patches | 生成模板不含 CMake 适配 | 补上 export_sources + apply_conandata_patches（patches 为空时 no-op） |
| 4 | 上游测试无 ctest 注册，且 QML 测试缺 org.kde.kquickcontrols 模块 | 上游 tests/CMakeLists.txt 未用 ecm_add_test；kquickcontrols 模块不在已发布依赖链 | 按 R51 如实回填：ctest 空套件 100% 通过；测试目标编译通过；运行时依赖另行说明 |

## 源码修改

无补丁（patches/ 为空）。OHOS 适配全部通过 conanfile.py 参数完成：
WITH_X11=OFF / KF_IGNORE_PLATFORM_CHECK=TRUE。

## 依赖版本

- qtbase-sql-dbus/6.11.1（Qt6::Core/Gui/Widgets/DBus/Test）
- ecm/6.20.0（tool_requires，KF6 CMake 模块）
- qttools/6.11.1（build_requires，Qt6LinguistTools）
- qtdeclarative/6.11.1（build_requires，Qt6Qml，仅供测试目标编译）

## 验证结果

- 手动模式 B：cmake configure + ninja 构建成功（BUILD_TESTING=ON）
- ctest：0 注册测试，exit 0
- conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全过 → status=published
- test_package：test_kglobalaccel 运行 PASS（KGlobalAccel::self() + setShortcut +
  isGlobalShortcutAvailable + globalShortcutsByKey 实质调用）

## 注意事项

- `kglobalacceltest` 是 QML GUI 集成测试，需要 org.kde.kquickcontrols 模块、
  D-Bus session bus、kglobalacceld 守护进程和图形显示；在无头 OHOS 环境只编译不运行。
- qtdeclarative 以 build_requires 引入，避免把 QML 运行时依赖泄漏给下游消费者。
- cmake_find_mode=none + builddirs 指向 lib/cmake，让下游通过
  `find_package(KF6GlobalAccel)` 使用安装的 Config.cmake（R49 私有 prefix 形态）。

## 上游测试真实执行（2026-09-16，OHOS 设备本机）

审查要求"上游 1 个用例必须真实执行"。在本机（HarmonyOS aarch64 设备，非模拟器）
补齐全栈依赖后真实跑通 kglobalacceltest：

| 依赖 | 解决方式 |
|------|----------|
| D-Bus session bus | 源码原生编译 dbus 1.14.10（CMAKE_SYSTEM_NAME=Linux 纠正平台分支）；OHOS 补丁：`fill_user_info`/`_dbus_unix_groups_from_uid` 对应用 UID（无 /etc/passwd 条目）回退 geteuid()/getgroups()；会话地址用 `unix:abstract=`（/tmp 只读、unix:path 受 SELinux 限制） |
| Qt QDBus → libdbus | qtbase 的 Qt6DBus 运行时 dlopen `libdbus-1.so.3`，指向自编 dbus-build/lib |
| org.kde.kquickcontrols | 该 QML 模块真实来源是 **kdeclarative**（此前 notes 归因 kiconthemes 有误）；从 kdeclarative 6.18.0 源码最小化构建 kquickcontrols + kquickcontrolsprivate，patchelf 修正 `bin/` 相对 NEEDED + binary-sign-tool 重签 |
| kglobalacceld 守护进程 | kglobalacceld 6.3.0 源码构建；OHOS 裁剪：KServiceActionComponent 降级为普通 Component、移除 KSycoca/KApplicationTrader/KDesktopFile/KFileUtils/KIO/KService/JobWidgets/KNotifications 依赖；无平台插件时跳过按键 grab 但组件注册/DBus 路径完整 |
| QtQuick/Controls | conan 缓存 qtdeclarative/6.11.1 的 qml/ 目录经 QML_IMPORT_PATH 注入 |

执行结果（test-final.log）：
```
shortcut set correctly QKeySequence("Meta+X")
shortcut set correctly QKeySequence("Meta+Shift+X")
shortcut set correctly QKeySequence("Meta+Y")
```
组件 "kglobalacceltest" 经 org.kde.kglobalaccel 注册成功，3 个快捷键全部
setShortcut 成功，日志 0 个 Failed/error。上游用例 **1/1 真实执行通过**。

---

**编译结束**: 2026-09-16 11:30
**最终状态**: published
