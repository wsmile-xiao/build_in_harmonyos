# knewstuff 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake (KF6/ECM)
- 编译日期: 2026-08-29
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built

## 编译步骤
1. `conan create archives/k/knewstuff/6.14.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. 与 ktextwidgets 同款 KF6 六件套（KF_IGNORE_PLATFORM_CHECK / KF_SKIP_PO_PROCESSING /
   BUILD_DESIGNERPLUGIN=OFF / ECM_MODULE_PATH / conan_cmakedeps_paths.cmake / 运行时农场）
3. **新增关键项**：`QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（cache variable，值为所有含
   `lib/cmake/Qt6*` 的依赖包根，`;` 连接）——详见问题 #1
4. 上游 3 个 patch：I18nQml 双守卫 + dialog.cpp `__has_include` 条件编译
5. `test()` 用 cwd=bindir + VirtualRunEnv（详见 #4/#5）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt6 COMPONENTS Qml)` 报 `Could NOT find Qt6Qml (missing: Qt6Qml_DIR)`，CMAKE_PREFIX_PATH 加包根/lib/cmake 都无效 | qtbase 的顶层 `Qt6Config.cmake` 只在**自身目录树**解析组件；Qml/Quick/QuickWidgets 属 qtdeclarative 独立发布包 | Qt6 官方扩展点 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<各含 Qt6 组件的包根>`（最小复现项目实测必需且充分）；主配方+test_package 都要设 |
| 2 | `KF6::I18nQml target not found`（widgets 与 tools 两处 PRIVATE 链接） | 已发布 ki18n（6.14/6.18/6.26 全系）`BUILD_WITH_QML=OFF`（当时 Qt6 Qml 未发布，前提现已过时） | patch 双守卫：widgets 链接 `if(TARGET)`；tools（demo 对话框）子目录同守卫跳过构建；dialog.cpp 用 `__has_include(<KLocalizedQmlContext>)` 条件编译回退 `QQmlContext`（**上游源码零逻辑删改**）。后续独立 PR 发布 ki18n/6.18.0.1（QML add-on）后本包可自动升级（若 ki18n 带 QML，TARGET 存在即走原路径） |
| 3 | 版本冲突 karchive 6.18 vs 6.14 | kpackage 仅发布 6.18.0，其图钉死 kcoreaddons/ki18n/karchive=6.18.0 | KF6 全家统一到 6.18.0 线 + ecm/6.26.0（build context 同版本约束）；knewstuff find_package 区间 [6.14,7.0) 兼容 |
| 4 | test_package 运行 `符号 not found`（QApplication 等） | `Environment.append("LD_LIBRARY_PATH", [list])` 把 Python list 字面量拼进环境变量 | 改 `prepend_path` + `os.pathsep.join`；并声明 `VirtualRunEnv` generators + `env="conanrun"`（与 ktextwidgets 对齐） |
| 5 | 主包安装后 `libKF6NewStuffWidgets.so` 的 NEEDED 是 `../../bin/libKF6NewStuffCore.so` 相对路径 | KF6 目标库无 SONAME 时 lld 把链接入参路径原样记入 NEEDED；musl 对含 `/` 的 NEEDED 按**进程 CWD** 解析 | test() 以 `cwd=self.cpp.build.bindir` 运行（farm 已把 core .so 镜像到 `<build>/../bin` 与 `<build>/../../bin`）；ctest 同理由 farm+正确 cwd 通过 4/4 |
| 6 | 测试断言 `entry.setStatus(Downloadable) → isValid()` 失败 | 臆写断言。真实语义：`isValid()` 只看 uniqueId 非空 | 按源码实测修正断言集（7 断言全过） |

## 源码修改（3 patch，refresh-patch 生成，conandata strip:1 + 元数据）
- `0001-src-CMakeLists.txt.patch`：tools 子目录 `if(TARGET KF6::I18nQml)` 守卫
- `0002-src-widgets-CMakeLists.txt.patch`：widgets 的 I18nQml PRIVATE 链接同守卫
- `0003-src-widgets-dialog.cpp.patch`：KLocalizedQmlContext `__has_include` 条件编译

## 依赖版本
- qtbase/qtbase-gui/qtdeclarative 6.11.1
- karchive/kconfig/kcoreaddons/ki18n/kwidgetsaddons/kpackage/attica 全部 6.18.0
- tool_requires ecm/6.26.0

## 验证结果
```bash
# conan create（干净 CONAN_HOME=~/tmp/ch/home 复刻 CI）：
# 主包编译 ✓  上游 ctest 4/4 PASS（knewstuffentrytest/knewstuffauthortest/
#   knewstuffenginetest/installationtest）
# test_package 7 断言 PASS（Entry 状态机 3 + Button 4，offscreen）
# 输出：PASS: knewstuff consumer test OK
```

## 注意事项
- 本机构建验证一律用 `CONAN_HOME=/storage/Users/currentUser/tmp/ch/home`
  （主缓存 ~/.conan2 被探测污染，出现 os.version Invalid 噪音；勿在主缓存继续验证）
- 软件级 `commands.json` 不创建：knewstuff-dialog6 demo 随 I18nQml 守卫不构建，无 bin 产物（R38 不适用）
- ki18n/6.18.0.1（QML add-on 补全）为独立依赖项任务（feat/ki18n-6.18.0.1 worktree 就绪）
---

**编译结束**: 2026-08-29 15:08
**最终状态**: built
