# kwindowsystem5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake（KF5 标准 CMake 工程）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（profile: ci/conan/profiles/ohos-aarch64，os=OHOS 6.0 / armv8 / cppstd=17 Release）
- 状态: built（conan-verify 通过，未 upload；upload 在 PR 合并 main 后由 CI 执行）

## 依赖
- `qt/5.15.19`（全量 OHOS Qt5，提供 Qt5Widgets/Qt5Gui/Qt5Core/Qt5Test）+ `ecm/6.26.0`（tool_requires）
- **不使用 `qt5-qtbase/5.15.2`**：其 OHOS 预编译包只含 QtCore/QtGui/QtTest，**不含 Qt5Widgets**；而 kwindowsystem PUBLIC 链接 Qt5::Widgets。故改用发布的全量 `qt/5.15.19`（cmake_find_mode=none，自带按模块的 Qt5{Core,Gui,Widgets,Test}Config.cmake）。

## 编译步骤
```bash
conan create archives/k/kwindowsystem5/5.116.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build=missing --user=ohpcd --channel=stable
```
配方要点：
- `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、`BUILD_TESTING=ON`、`BUILD_SHARED_LIBS=ON`
- `ECM_DIR` / `ECM_MODULE_PATH` 显式指向 ecm package 的 `share/ECM/{cmake,modules,find-modules,kde-modules}`（ecm 为 build-context tool_requires，不会自动接入 host config 路径；工程里 `find_package(ECM 5.116.0 NO_MODULE)`+`feature_summary(FATAL_ON_MISSING_REQUIRED_PACKAGES)`，ECM_DIR 缺失会直接 abort）
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`：HarmonyOS 未映射到 Linux CMake 平台，SONAME flag 未定义，缺此修复产出的 .so 无 ELF DT_SONAME（L5 soname 门禁失败）；保持 SONAME 但跳过版本化软链
- 运行时注入私有 prefix（build_folder），不污染 /usr/local（R49）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 `KeyError: '5.116.0'` | source() 用 `self.conan_data["sources"][version]`，但 conandata.yml 的 sources 是扁平 {url,sha256} 结构 | 改用 `get(self, **self.conan_data["sources"], strip_root=True)` |
| 2 | patch 不匹配源码行号 | 手写 hunk 行号偏移（ecm_install_po_files_as_qm 实际在第 83 行附近，非 48） | 按实际源码修正 hunk 上下文 |
| 3 | G2 configure 失败 `Could NOT find Qt5Gui` | **qt5-qtbase/5.15.2 无 Qt5Widgets**，且 CMakeDeps 只生成聚合 Qt5Config.cmake，工程里 per-module `find_package(Qt5Gui/Qt5Widgets/Qt5Test)` 找不到 Qt5GuiConfig.cmake | 依赖改用 `qt/5.15.19`（cmake_find_mode=none，自带 per-module config，直接解析） |
| 4 | G2 configure 失败 `Could NOT find ECM (missing: ECM_DIR)` | ecm 是 tool_requires，其 `share/ECM/cmake/ECMConfig.cmake` 未接入 host config 搜索路径；`conan_cmakedeps_paths.cmake` 未生成导致原 append 方案失效 | 在 generate() 显式 `tc.variables["ECM_DIR"]` + `ECM_MODULE_PATH` 指向 ecm package |
| 5 | test_package 编译失败 | test.cpp 误调不存在的 `KWindowSystem::numberOfScreens()` / `windowManagerName()` | 改用真实 KF5 API：`KWindowSystem::self()`、`numberOfDesktops()`、`KWindowInfo(0, NET::WMState)` |
| 6 | test_package 运行时共享库解析（E298） | 消费者链接共享 libKF5WindowSystem + Qt5 | test() 用 VirtualRunEnv + `self.run(env="conanrun")` 显式运行，保证 LD_LIBRARY_PATH 指向 package 目录 |
| 7 | poqm 翻译模块需要 Qt5LinguistTools/lrelease | 打包的 Qt5 不含 lrelease | patch `0001-poqm-disable` 注释掉 `ecm_install_po_files_as_qm(poqm)`（.ts 非 OHOS 运行时必需） |

## 源码修改
- `patches/0001-poqm-disable.patch`：注释顶层 CMakeLists.txt 的 `ecm_install_po_files_as_qm(poqm)`（Qt5LinguistTools 缺失）

## 上游测试（R51 三步法）
### 第一步：上游测试清点
- `autotests/`：共 **16 个** QtTest 程序源文件，经 ECM `ecm_add_test` 注册为 ctest 用例。其中 **15 个在 `if(X11_FOUND)` 内**（gated by X11/XCB/WM），仅 **1 个**（`kwindowsystem_platform_wayland_test.cpp` → `kwindowsystemplatformwaylandtest`）无条件注册。
- X11 门内 15 个：`kmanagerselectiontest` `kstartupinfo_unittest` `kxmessages_unittest` `kkeyserver_x11_unittest` `kwindoweffectstest` `kwindowinfox11test` `kwindowsystemx11test` `kwindowsystem_threadtest` `netrootinfotestwm` `netwininfotestclient` `netwininfotestwm` `compositingenabled_test` + 3 个可执行测试（`fixx11h_test`/`fixx11h_test2`/`dontcrashmapviewport`）。
- `tests/`：5 个交互/演示程序（`icontest` `setmainwindowtest` `blurbehindtest` `backgroundcontrasttest` `createpixmapfromhandletest`），同样 `if(X11_FOUND)` 门控，需真实 WM + Mock 图标。

### 第二步：可运行环境实测
- OHOS 交叉构建环境**无 X11/XCB 头库、无窗口管理器**，`X11_FOUND=0` → 15 个 X11 门内测试与 `tests/` 演示程序**不参与编译**（非"跳过但可运行"，是"结构上不可构建"）。
- 唯一非门控用例 `kwindowsystemplatformwaylandtest`：`initTestCase` 探测 `weston`，未安装则 `QSKIP("Weston could not be started")` → 记为 skip，退出码 0，ctest 视为通过（G2 conan create 的 `ctest --no-tests=error` 因此绿色）。

### 第三步：PR 回填
- 上游注册用例 N′：仅 1（wayland），实测**通过（skip）1/1**。
- 因无 X11/WM 导致不可构建的 15 个：在无可运行环境，未伪造运行结果，据实说明。

## 验证结果
```bash
conan-verify: G0-G4 全 PASS；L2/L4/L5 跳过（无 cache 路径）
conan create 成功, test_package 消费者测试通过:
  KWindowSystem::self() OK
  KWindowSystem::numberOfDesktops() = 0
  KWindowInfo(0).valid() = false
  OK: kwindowsystem5 consumer compiled and linked
```

## 交付物
- `libKF5WindowSystem.so`（含 ELF DT_SONAME，无版本化软链）
- 装配 `KF5WindowSystemConfig.cmake`（builddirs=lib/cmake）

## 注意事项
- 运行时 libKF5WindowSystem 需要 `LD_LIBRARY_PATH` 指到 Qt5/lib（QPA 插件路径由运行时注入私有 prefix）
- 非 GUILESS 用法（如 `setMainWindow`) 需要 QGuiApplication，与上游一致
- **R40 深度适配范围说明**：kwindowsystem 属窗口系统抽象库，OHOS 无 X11，`find_package(X11)` 得 `KWINDOWSYSTEM_HAVE_X11=0`，编译上游 **dummy 后端**。交付的 `KWindowSystem/KWindowInfo/KWindowEffects` 查询类 API 在无 WM 场景返回 fallback 值（test_package 已验证链接+调用，numberOfDesktops()=0、KWindowInfo(0).valid()=false）。**未验证真实窗口系统/WM 行为，适配完整性需人工确认**；后续若需 X11/Wayland 后端支持需另行适配
---

**编译结束**: 2026-09-18 15:11
**最终状态**: built
