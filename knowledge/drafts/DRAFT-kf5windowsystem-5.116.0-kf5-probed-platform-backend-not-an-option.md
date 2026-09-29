# KF5 的窗口系统后端是「探测」出来的，不是选项：OHOS 用 `CMAKE_DISABLE_FIND_PACKAGE_X11` 关断，并据此重算上游用例数口径

> **来源 PR**：!13567（`archives/k/kf5windowsystem/5.116.0`，KDE Frameworks 5 / Qt5）
> **适用对象**：KF5 分支（5.x）里用 `find_package(X11)` 探测而非 `option()` 决定平台后端的框架
> **状态**：草稿（待审核 promote）

## 错误特征

同一上游仓库（invent.kde.org/frameworks/kwindowsystem）在两条分支上用了两套机制，
照抄 KF6 配方到 KF5 上时，症状是**「没有选项可关」**，而不是某个具体的报错：

- `grep -n "option(" CMakeLists.txt | grep -i -E "x11|wayland"` → **无输出**
  （KF6 才有 `KWINDOWSYSTEM_X11` / `KWINDOWSYSTEM_WAYLAND`）。
- 顶层第 69 行是推导而非选项：`set(KWINDOWSYSTEM_HAVE_X11 ${X11_FOUND})`。
- `autotests/CMakeLists.txt` 里有**第二处** `find_package(X11)`，以及一处
  **无条件**的 `find_package(XCB COMPONENTS XCB ICCCM KEYSYMS)`。
- 若放任探测自然失败，`autotests/` 的 `kwindowsystem_unit_tests()` 会把
  `XCB::ICCCM` / `XCB::KEYSYMS` 塞进 `ecm_add_test(... LINK_LIBRARIES ...)`，
  而这两个 imported target 在 `X11_FOUND` 为假时不存在 →
  `CMake Error: Target ... links to: XCB::ICCCM but the target was not found`。
- 配置侥幸通过后，如果只盯着 `ctest -N`，会看到注册集只有 1 条，容易把
  「上游用例数」写成 1（真实源码层面目标上限是 22）。

## 触发条件

三条同时成立，即为本条（缺一不可）：

1. 顶层 CMakeLists.txt 有 `find_package(X11)`（或 Wayland\*），但**没有**对应 `option(...)`；
2. 存在 `set(<PREFIX>_HAVE_X11 ${X11_FOUND})` 这类推导；
3. 后端源码目录（如 `src/platforms/xcb`）被 `if(X11_FOUND)` 包着，且另有一个
   **不被门控包住**的 dummy / fallback 实现（本例 `src/kwindoweffects_dummy.cpp`
   + `KWindowSystemPrivateDummy`）。

三条齐备 → 目标平台没有 X11 栈时，正确的关断点是 CMake 内建变量，而不是配方选项。

## 根因分析

KF5 与 KF6 在**同一个上游仓库**里对平台后端用了两套机制：

| | KF6（6.14.0 起） | KF5（5.116.0） |
|---|---|---|
| 后端开关 | `KWINDOWSYSTEM_X11` / `KWINDOWSYSTEM_WAYLAND` 选项 | **无选项** |
| 决定方式 | 读选项 | `find_package(X11)` → `KWINDOWSYSTEM_HAVE_X11 = ${X11_FOUND}` |
| OHOS 关法 | `-DXXX_X11=OFF -DXXX_WAYLAND=OFF` | `CMAKE_DISABLE_FIND_PACKAGE_X11=TRUE` |
| 关掉后 | dummy 后端 | dummy 后端（**同一份**上游代码） |

`CMAKE_DISABLE_FIND_PACKAGE_X11` 之所以是最小改动面：它是 CMake 内建变量，
让**所有**同名 `find_package(X11)` 直接以 not-found 返回（不报错）。
两处探测（顶层 + `autotests/`）一次覆盖，`X11_FOUND` 同时为假，
于是 `src/platforms/xcb` 不编译、`if(X11_FOUND)` 门控的目标不配置，
库退回到始终参与编译的 dummy 后端——与 KF6 配方把两个后端全关掉后的
最终状态一致。

顺带确认一个**不需要**做的动作：`autotests/` 里那句无条件的
`find_package(XCB COMPONENTS XCB ICCCM KEYSYMS)` 不会 FATAL_ERROR ——
ECM 的 `find-modules/FindXCB.cmake` 只用 `find_package_handle_standard_args`，
找不到就是静默 not-found。因此 **不需要** 再设
`CMAKE_DISABLE_FIND_PACKAGE_XCB`（设了也无害，但多一个变量就多一处要解释）。

### 同一处探测还决定「上游用例数」

`X11_FOUND` 门控与 `ecm_mark_as_test()` 的语义叠加，使上游测试面在 OHOS 上收缩到
几乎为空，而**源码里声明的目标数远大于 CTest 注册数**：

| 目标类别 | 个数 | OHOS 上为什么不跑 |
|---|---|---|
| `autotests/` 两个 `kwindowsystem_unit_tests(...)` 块 | 12 | 全在 `if(X11_FOUND)` 内 → 不配置 |
| `autotests/` 的 `kwindowsystem_executable_tests(...)` | 3 | 同上（fixx11h_test / fixx11h_test2 / dontcrashmapviewport）|
| `tests/` 受 `KWINDOWSYSTEM_HAVE_X11` 门控 | 3 | `= ${X11_FOUND} = 假` → 不构建 |
| `tests/` 两个无条件交互式演示 | 2 | `add_executable` + **`ecm_mark_as_test`**：只设 `EXCLUDE_FROM_ALL`，**不注册 CTest**；且 `main()` 只有 `QApplication`+`show()`+`exec()`，`grep -c "QVERIFY\|QCOMPARE\|QTest::"` 为 0（无判定 oracle）|
| `autotests/helper` 辅助进程 | 1 | wayland 平台测试拉起的子进程，`ecm_mark_as_test` 打标，不是用例 |
| **源码层面目标上限** | **22** | |
| 其中 **CTest 实际注册** | **1** | 只剩无条件的 `ecm_add_test(kwindowsystem_platform_wayland_test.cpp …)` |
| 朴素文本扫描口径 | 6 | `grep -rE "add_executable\(\|ecm_mark_as_test\("` |

所以报数必须分三档、声明值取**最大**的一档（22），并逐类说明未执行的目标
属于「门控不配置」还是「无判定 oracle 的交互式演示」。只写 1 会被判少报。

## 解决方案

在配方的 `generate()` 里设 CMake 内建变量：

```python
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = "TRUE"
```

配套要点：

1. **不要**改上游 CMakeLists、**不要**伪造 X11 头/`.pc`、**不要**把
   `X11_FOUND` / `KWINDOWSYSTEM_HAVE_X11` 硬写成 TRUE。
2. 关掉探测后，凡是 `if(X11_FOUND)` / `if(<PREFIX>_HAVE_X11)` 包住的目标
   自然消失，**不需要**逐个裁剪。
3. 库的公开符号由上游**自带的** dummy 实现提供（不是本地 stub），所以
   test_package 里断言的是「dummy 后端的可观测默认值」，例如
   `platform() == Platform::Unknown`、`isPlatformX11()` / `isPlatformWayland()`
   为 false、`showingDesktop()` / `allowedActionsSupported()` 为 false、
   `KWindowEffects::isEffectAvailable()` 对 BlurBehind / BackgroundContrast 为 false，
   以及 `setShowingDesktop(true)` 是空操作。
4. 区分 `ecm_add_test()`（**会**注册 CTest）与 `ecm_mark_as_test()`（**只**设
   `EXCLUDE_FROM_ALL`，**不**注册）——判断某目标会不会被 `ctest` 跑到，看的是用的哪个宏。
5. 断言制品形态时补上 `DT_SONAME`：HarmonyOS 未映射到 Linux CMake 平台，
   `CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG` 未定义会让 `.so` 缺 `DT_SONAME`
   （CI L5 门禁），需要显式设 soname flag + `CMAKE_PLATFORM_NO_VERSIONED_SONAME`。

### 备选方案（fallback）

仅当上游别处还硬引用 X11 符号、关掉探测就编不过时，才打补丁把
`if(X11_FOUND)` 改成显式 `option(<PREFIX>_X11 "" OFF)`（与 KF6 写法对齐）。
代价：补丁落在上游 CMakeLists 上，补丁面扩大、与同族 KF5 配方不一致、
升级 5.x 时行号还会漂移。

## 验证命令

```bash
# 1) 确认「没有后端选项、只有探测推导」（本条与 KF6 的分界）
grep -n "option(" CMakeLists.txt | grep -i -E "x11|wayland"        # 期望：无输出
grep -n "find_package(X11)\|KWINDOWSYSTEM_HAVE_X11" CMakeLists.txt autotests/CMakeLists.txt
# → CMakeLists.txt:69         set(KWINDOWSYSTEM_HAVE_X11 ${X11_FOUND})
# → autotests/CMakeLists.txt:14  find_package(X11)          ← 第二处探测

# 2) 关闭探测后正常构建（OHOS aarch64）
conan create archives/k/kf5windowsystem/5.116.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → 配置期不再出现 XCB::ICCCM / XCB::KEYSYMS not found
# → 1/1 Test #1: kwindowsystem-platform-kwindowsystemplatformwaylandtest ... Passed

# 3) 上游用例数三档口径
grep -rcE "add_executable\(|ecm_mark_as_test\(" --include=*.txt .   # 朴素扫描
ctest --test-dir build -N                                           # CTest 实际注册
grep -rn "if(X11_FOUND)\|if(KWINDOWSYSTEM_HAVE_X11)" autotests/CMakeLists.txt tests/CMakeLists.txt

# 4) 上游 find_package(XCB ...) 是否需要一并关掉？——不需要
curl -sL https://invent.kde.org/frameworks/extra-cmake-modules/-/raw/master/find-modules/FindXCB.cmake \
  | grep -n "FATAL_ERROR\|find_package_handle_standard_args"
# → 只有 find_package_handle_standard_args ⇒ 静默 not-found
```

## 禁止策略

1. **禁止伪造 X11 制品**：`touch`/`echo`/`cp` 出 X11 头、`X11.pc`，或
   `-DX11_FOUND=TRUE` / `set(X11_FOUND TRUE)` 之类硬写成真。症状会从
   「配置期干净失败」后移成「编译期找不到头 / 链接期 undefined symbol」。
2. **禁止 sed 上游 CMakeLists 的探测与门控**：改源码 = 不必要的改动面扩大，
   且与同族 KF5 配方（直接用 `CMAKE_DISABLE_FIND_PACKAGE_*`）不一致。
3. **禁止为了让注册集非空而关 `BUILD_TESTING`，或摘掉 `--no-tests=error`**：
   门控导致注册集收缩是上游本态，应如实分档声明，而不是把测试关掉。

## 关联

- **同仓互补**：`DRAFT-E5xx-qt5-conan-split-cmake-bridge` —— 那条讲 Qt5 按模块
  拆包后伞形 `find_package(Qt5 COMPONENTS ...)` / `Qt5::Gui` 目标怎么桥接
  （Qt 依赖解析层）；本条讲 KF5 与 KF6 在后端开关上的差异（上游 CMake 探测层）。
- **同族**：`DRAFT-kio-kwallet-6.28.0-kwallettest-zero-ctest-display-guard` ——
  `ecm_mark_as_test()` 不打 `add_test` ⇒ `ctest -N` 为 0 是上游本态；本条把该事实
  并入门控收缩后「上游用例数」的三档口径。
- **同族**：`DRAFT-cmakedeps-interface-defines-lost`（CMake 生成物与上游假设错位）。
- 同仓库已上架的 KF6 配方：`archives/k/kwindowsystem/6.14.0|6.18.0|6.26.0`
  （对照项：它们用的是 `KWINDOWSYSTEM_X11=OFF` 选项路线）。

## 上游可提交性

本条是**适配侧的方法论**，不是上游缺陷：KF5 已进入维护尾声（5.116.0 是最后一个
功能版本），把「探测」重构成「选项」属于破坏性改动，上游不会接受。
可提交的只有一句文档补充——在 KF5 的 build 说明里提示交叉编译时可用
`CMAKE_DISABLE_FIND_PACKAGE_X11` 关断后端；价值低，建议不投上游。
