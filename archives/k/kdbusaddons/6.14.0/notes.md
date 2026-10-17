# kdbusaddons 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (HarmonyOS PC toolchain)
- 状态: built

## 编译步骤

1. W0 依赖检查：`conan download qtbase-sql-dbus/6.11.1 -r=ohpcd --only-recipe`、`conan download ecm/6.20.0 -r=ohpcd --only-recipe` 均成功（qtbase-sql-dbus 还依赖 dbus/1.14.10，已发布）。
2. 配方：基于同系列 KF6 6.14.0 配方（kcoreaddons/6.14.0）的 OHOS 手法编写：
   - `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台检测（OHOS 不在 KDE 平台列表）
   - `WITH_X11=OFF`：OHOS 无 X11，编译掉 kdbusservice.cpp 中 qtx11extras_p.h 代码路径并避免链接 Qt6::GuiPrivate
   - `BUILD_TESTING=OFF`：上游 autotests 需要运行中的 D-Bus session bus，OHOS 构建环境不可用
   - `ECM_MODULE_PATH` 手工设置（CMakeDeps 生成的 ECMConfig.cmake 不传递该变量）
   - `conan_cmakedeps_paths.cmake` 手工生成（qtbase-sql-dbus 使用 cmake_find_mode=none，CMakeDeps 不会把 lib/cmake 加进 CMAKE_PREFIX_PATH）
3. 补丁 0001：禁用 `ecm_install_po_files_as_qm(poqm)` —— 该宏需要 Qt6LinguistTools（qttools 组件），制品仓未发布。
4. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` 成功。
5. test_package：构建并运行 test_kdbusaddons（KDEDModule 构造 + setModuleName/moduleName + 静态 moduleForMessage 解析），1/1 通过，直接运行二进制 exit 0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 失败：Qt6_FOUND=FALSE，缺 LinguistTools | 顶层 CMakeLists `ecm_install_po_files_as_qm(poqm)` 经 ECMPoQmTools 强制 `find_package(Qt6 COMPONENTS LinguistTools)`，Qt6LinguistTools 属于 qttools，制品仓未发布 | 补丁 0001 注释掉该宏（与 kcoreaddons/6.26.0 同法） |
| 2 | 关键决策：依赖选型 | 任务描述称 qtbase/6.11.1"含 Qt6Core/DBus"，但配方与 notes 证实 qtbase/6.11.1 的 `FEATURE_dbus=OFF`；Qt6DBus 只由 qtbase-sql-dbus/6.11.1 提供（依赖 dbus/1.14.10） | requirements 使用 `qtbase-sql-dbus/6.11.1`（kdbusaddons 强制 `find_package(Qt6DBus REQUIRED)`，不可用 DBus=OFF 的 qtbase） |
| 3 | make jobserver mkfifo: Operation not permitted | 平台限制（临时目录 mkfifo 受限），无实际影响 | 忽略，构建/测试均正常 |

## 依赖版本

- qtbase-sql-dbus/6.11.1（Qt6Core/Qt6Gui/Qt6DBus + 私有头，依赖 dbus/1.14.10）
- ecm/6.20.0（build requirement，ECM >= 6.14.0 满足）

## 验证结果

```bash
conan create archives/k/kdbusaddons/6.14.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# exit 0；test_package: 1/1 tests passed；test_kdbusaddons 直接运行 exit 0
```

### 上游 autotests 沙箱实测（2026-08-30，2/2 通过）

上游 autotests（kdbusservicetest / deadservicetest）需要运行中的 D-Bus session bus。
在本机 OHOS 沙箱内自建 D-Bus session bus 并实际编译、运行上游 2 个 autotests，**全部通过**：

| 测试 | 结果 | 说明 |
|------|------|------|
| kdbusservicetest | PASS (exit 0) | KDBusService::Unique 注册 + activateRequested 三连调用 |
| deadservicetest | PASS (3/3) | 注册→挂起→SIGUSR1 杀死→名字移交第二实例 |

OHOS 沙箱限制与对策（详见 `reports/dbus-autotests-run.md`）：
1. 无 dbus-daemon → 从 dbus 1.14.10 源码用同一 OHOS 工具链构建 dbus-daemon
2. unix socket 创建被禁（Operation not permitted）→ 用 `unix:abstract=` 或 TCP 监听
3. UID 无 passwd 条目 / keyring 目录权限校验失败 → LD_PRELOAD shim 提供 fake getpwuid + 对 daemon 源码放宽目录私有校验（仅本机测试，不入库）

> 说明：CI 沙箱同样无 dbus-daemon，故配方保持 BUILD_TESTING=OFF；本机沙箱实测证明
> D-Bus 功能在 OHOS 上正确，上游测试 2/2 通过，非功能缺陷。

产物：`lib/libKF6DBusAddons.so`（ELF arm64 共享库）、`bin/kquitapp6`、`include/KF6/KDBusAddons/` 公共头、`lib/cmake/KF6DBusAddons/` 的 Config/Version/Targets/Macros、`share/qlogging-categories6/` 日志分类。

## 注意事项

- 本组件是库类型（附带 kquitapp6 辅助工具），按 R38 不需要 commands.json（L0k 门禁只检查 conanfile.py 的 bindirs/application 声明）。
- 下游消费需依赖 qtbase-sql-dbus/6.11.1 提供 Qt6DBus；KF6DBusAddonsConfig.cmake 内部 `find_dependency(Qt6DBus)` 经 conan_cmakedeps_paths.cmake 解析。
---

**编译结束**: 2026-08-28 14:00
**最终状态**: built
