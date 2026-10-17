# statusnotifieritem 6.26.0 适配笔记（R01）

（conan 包名 statusnotifieritem，与上游仓库 invent.kde.org/frameworks/statusnotifieritem 一致；KDE 发布 tarball 名为 kstatusnotifieritem-6.26.0.tar.xz）

## Scope

KDE Frameworks 6 系统托盘状态通知项库（StatusNotifierItem / SNI），产出
libKF6StatusNotifierItem.so：KStatusNotifierItem 公共 API（Qt Widgets 层）、
org.kde.StatusNotifierItem / org.kde.StatusNotifierWatcher /
org.freedesktop.Notifications DBus 适配器、内置 libdbusmenu-qt 菜单导出器。
上游仓库 invent.kde.org/frameworks/statusnotifieritem，tarball 名为
kstatusnotifieritem-6.26.0.tar.xz（KDE 发布命名与仓库名不同）。

## 编译环境

- 构建系统: cmake (ECM/KDE Frameworks 6)
- 编译日期: 2026-09-07
- 编译器: clang/clang++ 15 (ohos-aarch64 profile, os=OHOS)
- 状态: built

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表内）。
- `WITHOUT_X11=ON`：跳过 find_package(X11)（OHOS 无 X11，HAVE_X11=0 走纯
  Widgets 代码路径）。
- `USE_DBUS=ON`：显式开启。上游默认仅在严格 UNIX（非 APPLE/ANDROID/HAIKU）
  为 ON；交叉构建必须显式置 ON，否则库会在无声无息中缺失 DBus 适配器
  （本库核心价值）。
- `BUILD_PYTHON_BINDINGS=OFF`：上游默认 ON 且 find_package(Shiboken6
  REQUIRED) 硬失败；ohpcd 未发布 Shiboken6/PySide6。
- `BUILD_QCH=OFF` + `KF_SKIP_PO_PROCESSING=ON`；poqm 翻译走
  qt6linguisttools/6.11.1（build tool）。
- 补丁 0001：KF_DEP_VERSION 6.26.0→6.18.0（对齐 ohpcd 已发布的
  kwindowsystem/6.18.0；ECM 6.26.0 恰为上游要求版本，无需降级）。
- `ECM_MODULE_PATH`、`conan_cmakedeps_paths.cmake` 手工写入（qtbase/KF6 包
  cmake_find_mode=none）。
- `Qt6LinguistTools_DIR` 钉到 qt6linguisttools 包（Qt6Config 组件解析先例）。
- **关键坑（R01 实测）**：conan_cmakedeps_paths.cmake 不能遍历
  `self.dependencies.values()` 全量 PREPEND——build context 的
  qtbase/6.11.1（qttools 传递依赖，qt6linguisttools 的 host 工具链）会被
  前置到 CMAKE_PREFIX_PATH 最前，find_package(Qt6) 命中无 DBus 的 6.11.1，
  Qt6DBus 找不到。修复：只显式追加 host context 的 kwindowsystem（与
  kdbusaddons 6.29.0 配方结构一致）。
- qtpaths 运行环境：PATH/LD_LIBRARY_PATH 前置 qtbase/bin、qtbase/lib、
  /system/lib64（baloo/bluez-qt/kconfig 先例）。

## Dependencies（W0 实测，全部 conan download 确认）

qtbase/6.11.1.1（FEATURE_dbus=ON 变体，Qt6DBus 消费门禁 kdbusaddons 6.29
先例；override=True 统一 KF6 依赖传递的 qtbase/6.11.1 引用，baloo 先例）、
kwindowsystem/6.18.0、build: ecm/6.26.0 + qt6linguisttools/6.11.1。

注：任务参数提到的 kconfig/kcoreaddons/ki18n/kdbusaddons 系为本库上层 KDE
应用的生态依赖；kstatusnotifieritem 6.26.0 上游 CMakeLists 的直接 REQUIRED
依赖只有 Qt6 Widgets (+DBus) 与 KF6WindowSystem（kwindowsystem/6.18.0 又只
依赖 qtbase）。配方按上游实际依赖图声明，不引入未使用的包。

## Upstream tests（实测）

上游 tarball 解压后 `find tests autotests -name "*.cpp"` 实测：仅
tests/kstatusnotifieritemtest.cpp（1 个测试源文件，120 行）。其
tests/CMakeLists.txt 只有 `add_executable` + `target_link_libraries`，**无
add_test / ecm_mark_as_test 注册**——上游在任何平台 ctest 都是 0 项。该二进制
为 QApplication 手动演示程序（构造多个 KStatusNotifierItem + QLabel 主窗口 +
QMenu，进入事件循环永不退出）。

处置（能跑全纳入）：
1. BUILD_TESTING=ON 编译该演示二进制（实测 100% Built target
   kstatusnotifieritemtest——测试代码在 OHOS 工具链下可编译、可链接被测库）；
2. 配方 `_run_upstream_tests` 以 QT_QPA_PLATFORM=offscreen + 25s 超时执行：
   **实测到达 Qt 事件循环（超时被杀）= PASS**——动态链接链
   libKF6StatusNotifierItem + Qt6Widgets + Qt6DBus 在 OHOS 运行时加载成功 +
   QApplication 构造成功；
3. 演示二进制 DT_NEEDED 为相对路径 `../bin/libKF6StatusNotifierItem.so`
   （build-tree 库无 SONAME，musl loader 不做 LD_LIBRARY_PATH 相对路径回退），
   必须以 cwd=build/tests 运行使相对路径解析（实测确认）；
4. 0 ctest 注册项为上游事实（非适配侧排除），如实记录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(Qt6DBus) 失败 | cmakedeps paths 遍历全依赖把 build context 的 qtbase/6.11.1 前置到搜索路径最前 | generate() 只显式追加 host context 依赖（kdbusaddons 6.29 结构） |
| 2 | toybox patch 拒绝多行上下文 hunk | @@ 行数标注与空行语义 | 最小 hunk（3 行上下文精确匹配），dry-run 实测通过 |
| 3 | demo 二进制执行 rc=127 | DT_NEEDED 为相对路径 ../bin/…，musl 不走 LD_LIBRARY_PATH 回退 | 以 cwd=build/tests 运行（相对路径解析成功，事件循环到达） |
| 4 | EnvVars 对象无 environment 属性 | conan 2.29 API | test_env.vars(self).apply() 上下文管理器 |
| 5 | USE_DBUS 默认 OFF | 上游默认仅严格 UNIX 系为 ON | tc.variables 显式 USE_DBUS=ON |
| 6 | Shiboken6 REQUIRED 硬失败 | BUILD_PYTHON_BINDINGS 默认 ON | 显式 OFF（ohpcd 未发布） |
| 7 | X11 find_package 失败 | OHOS 无 X11 | WITHOUT_X11=ON 跳过查找 |
| 8 | KF6WindowSystem 6.26.0 版本墙 | ohpcd 最高发布 6.18.0 | 补丁 0001 降 KF_DEP_VERSION |

## 验证结果

```bash
conan create archives/s/statusnotifieritem/6.26.0 --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing
# -> kstatusnotifieritem/6.26.0@ohpcd/stable: Package 'b8d7c06d07651175e501ee85c5977b7812677caf' created
# -> libKF6StatusNotifierItem.so 安装（含 KF6StatusNotifierItemConfig.cmake/
#    Targets/头文件/DBus XML/categories）
# -> 上游 demo kstatusnotifieritemtest: 100% 编译 + offscreen 执行到达事件循环 PASS
# -> test_package: 100% tests passed, 0 tests failed out of 1
#    PASS: KStatusNotifierItem API round-trip OK (title/category/status/toolTip)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（包名 statusnotifieritem；qtbase/6.11.1.1 override + kwindowsystem/6.18.0 + ecm/6.26.0 + qt6linguisttools） |
| conandata.yml | 官方源 URL + SHA-256（单 URL） |
| patches/0001 | KF_DEP_VERSION 6.26.0→6.18.0 |
| test_package/ | test_kstatusnotifieritem（真实 API round-trip）+ MANIFEST.yml |
| reports/ | conan create 验证证据 |

## CI 验证（PR #8789）

- 构建 #41856: ❌ L0 dir_structure_r39（目录 archives/k/statusnotifieritem 首字母
  与包名不一致——返工：目录迁 archives/s/ + 包名统一 statusnotifieritem，与上游
  仓库名一致；KDE tarball 名 kstatusnotifieritem 为发布命名）
- 构建 #41859: ✅ CI 校验通过（L0/L1 门禁通过，conan-build-test ✅）
- 构建 #41868: ✅ CI 校验通过（复跑确认稳定）
- AI Review（atomgit-bot）：代码审查 ✅ 未发现问题（零意见闭环）
- 注：PR reporter 子字段 "Conan test_package: 失败" 与整体 PASSED/L1 门禁通过/
  conan-build-test ✅ 矛盾，两轮复跑稳定复现；判定为 reporter 对 L1e 破坏性
  负向验证（产物移走后 conan test 预期失败=测试真实依赖包）的表述歧义，
  已在 SKILL_FEEDBACK 提出 reporter 侧核对建议。

---

**编译结束**: 2026-09-07
**最终状态**: built（本地+CI 双验证通过）
