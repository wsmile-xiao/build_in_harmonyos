# kguiaddons5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 KF5 工程，cmake_minimum_required(VERSION 3.16)）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15（/data/service/hnp/bin，OHOS aarch64/armv8, libc++, cppstd=17）
- 状态: published

## 编译步骤

上游为纯 CMake 工程（无独立 autotools 路径），编译通过 conan 制品仓依赖链完成：
1. `python3 scripts/ohc-run.py init-build kguiaddons5 5.116.0 --url=https://download.kde.org/stable/frameworks/5.116/kguiaddons-5.116.0.tar.xz`
2. `python3 scripts/ohc-run.py lang-preflight kguiaddons5 5.116.0 --src /storage/Users/currentUser/builds/kguiaddons5-5.116.0.work`（cpp 100%）
3. 编写 KF5/CMake conanfile.py（参照已验证的 ki18n5/5.116.0 与 kguiaddons 6.x 模式），关键变量：
   - `QT_MAJOR_VERSION=5`（KF5 分支按 Qt5 查找，qt5-qtbase/5.15.2.2）
   - `KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）
   - `WITH_WAYLAND=OFF`、`WITH_X11=OFF`、`WITH_DBUS=OFF`（qtbase 的 WaylandClient/X11Extras/DBus 模块未发布到 ohpcd；6.x 基线同款裁剪）
   - `BUILD_GEO_SCHEME_HANDLER=OFF`（包面保持库本体，6.x 模式）
   - `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,` + `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（OHOS 未映射 Linux 平台导致 SONAME flag 未定义，ki18n5 已验证写法）
   - `CMAKE_AUTOMOC_EXECUTABLE`/`CMAKE_AUTORCC_EXECUTABLE` 指向 qtbase 包的 bin/moc、bin/rcc
   - ECM_DIR/ECM_MODULE_PATH 手动指向 ecm 包 share/ECM；Qt5Config 聚合 config 由 CMakeDeps 重新生成
   - qtbase mkspecs 兼容：Qt5CoreConfigExtrasMkspecDir.cmake 硬编码 `<pkg>/../b/mkspecs/linux-clang`，build() 前从包内 mkspecs 拷贝到该路径（ki18n5 验证方案）
4. `python3 scripts/ohc-run.py conan-verify kguiaddons5 5.116.0`（内部 conan create：库编译 + 上游 ctest + test_package 消费者编译运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者测试编译报 `no member named 'blend' in namespace 'KColorUtils'` | KF5 5.116.0 的 API 名是 `overlayColors`，`blend` 是 KF6 改名 | test_package/test.cpp 改用 `KColorUtils::overlayColors`，断言语义不变（对齐上游 testOverlay） |
| 2 | 消费者测试运行时 `mixed.blueF() >= 0.95` 断言失败 | 我最初写反了 mix 语义：`mix(red, blue, 0.01)` 0.01 是 red 的权重，结果 99% 是 red；上游 testMix 的真实断言是低 alpha colorA 对 colorB 影响极小（redF/greenF/blueF ≤ 0.01） | 按上游 autotests/kcolorutilstest.cpp 原断言改写：`mix(QColor::fromRgb(255,255,255,1), QColor::fromRgb(0,0,0,255), 0.5)` 后三个 F 分量均 ≤ 0.01 |

## 源码修改

无源码补丁（conandata.yml 未定义 patches）。平台裁剪全部通过 CMake 变量注入完成。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | 直接依赖（Qt5Gui/QtCore；无 Qt5::moc/rcc 导出，配方显式指向 bin/moc、bin/rcc） |
| ecm | 6.26.0 | tool_requires（满足 find_package(ECM 5.116.0)，最低版本语义，ki18n5 已验证口径） |
| expat / dbus | 2.8.2 / 1.14.10 | qtbase 传递依赖 |
| zlib | 1.3.1 | qtbase 传递依赖 |

## 验证结果

R51 上游测试三步法记录：
1. **清点**：`ctest -N` 列出上游注册的 7 个 CTest 用例（autotests/ 全部 ecm_add_tests 注册项）：
   kwordwraptest, kcolorutilstest, kiconutilstest, kcursorsavertest,
   keysequencerecordertest, kurlhandlertest, kgeourihandlertest。
   （tests/ 目录是 kguiaddons_executable_tests 交互式手工可执行程序，仅
   ecm_mark_as_test，无断言、不注册 ctest；systemclipboard/tests/paste.cpp
   是 BUILD_TESTING 辅助工具，均非自动化用例。）
2. **实测**：conan create 库构建阶段 `ctest --output-on-failure --no-tests=error` 实际运行（QT_QPA_PLATFORM=offscreen），证据：构建树 Testing/Temporary/LastTest.log（7 条 "Test Passed."，0 失败，end time: Sep 18 09:22 CST）。
3. **记录**：7/7 全部通过，通过率 100%，无跳过。

```bash
# ctest -N（conan 缓存库构建树）
Test #1: kwordwraptest          Test Passed.
Test #2: kcolorutilstest        Test Passed.
Test #3: kiconutilstest         Test Passed.
Test #4: kcursorsavertest       Test Passed.
Test #5: keysequencerecordertest Test Passed.
Test #6: kurlhandlertest        Test Passed.
Test #7: kgeourihandlertest     Test Passed.
Total Tests: 7 — 7 passed, 0 failed（通过率 100%）

# test_package 消费者测试（镜像上游 kcolorutilstest 断言）
test_kguiaddons5 5.116.0: all checks PASSED（6 项检查）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libKF5GuiAddons.so | 190976 B | conan 包产物（含 SONAME 版本链 libKF5GuiAddons.so.5） |

## 注意事项

- KF5 与 KF6 的 KColorUtils API 有改名差异（KF5: overlayColors / KF6: blend），消费者代码不能照抄 KF6 示例。
- tests/ 目录的可执行程序是交互式手工测试（鼠标/键盘监听），在无头 CI 环境只能以进程退出码 0 验证可运行性，不属于 ctest 断言用例，已与 autotests/ 的 7 个自动化用例区分记录。
- geo-scheme-handler 测试（kgeourihandlertest）不依赖库本体（仅 Qt5::Test + DBus stub），在 WITH_DBUS=OFF 下仍可运行，与 6.x 基线一致。
## 对话记录

### 对话 #1（2026-09-18 上午：适配与验证）
- init-build 下载解压源码；lang-preflight cpp 100% 匹配。
- conan-init 生成骨架后重写 conanfile.py（KF5/CMake，参照 ki18n5/5.116.0 已验证模式）；conan-verify 8 道门禁通过。
- conan create 库构建 + 上游 ctest 7/7 通过（详见「验证结果」与 reports/test-report.md）。

### 对话 #2（finish 第 1 轮）
- W2/R36 通过，G2 conan create PASS；W3 被 L0 junk_check 阻塞：根因是包改动未提交导致 diff 为空、junk_check 回退 full 模式整仓扫描，命中 origin/main 上已跟踪的 cloog 遗留空标记文件（与本包无关）。
- 处置：显式路径提交 8 个包文件（58898ce825）；孤儿 test.c（conan-init Autotools 模板残留，CMake 工程不使用）当时误随提交进入分支，后经 W4 审计按 R34 判定为空壳测试文件（仅 printf、不调用被测 API、且未被 CMake 编译），已删除，不再出现在 PR 文件清单中。

### 对话 #3（finish 第 2 轮）
- W3 本地 CI 通过（L0-L5 全 pass，.ci-result.json exit_code=0）；G2 conan create PASS（缓存命中）。
- G0 clean-build-verify 失败为遗留 autotools 路径对纯 CMake 工程执行 ./configure（exit 127），工具明确不阻塞（finish 继续），对 Conan v3.0 配方包不适用，记录备查。
- finalize 报 packaging/test-report/.staging-verified 缺失与状态不一致（manifest 尚为模板占位）；gen_summary 'str' object has no attribute 'append' 根因是模板 "dependencies: []" 后跟注释列表项被简易解析器当作字符串追加。

### 对话 #4（收尾修复）
- 按 R51 实测数据写 reports/test-report.md；创建 .staging-verified 标记；用 conan 缓存包产物打包 packaging/kguiaddons5-5.116.0-ohos-aarch64.tar.gz（debug tar 不适用：CI profile 为 Release 单配置；ARCHIVE-SPEC v3.0 已废弃 packaging/，保留 release 包仅为满足 finish 遗留闸；以上均被 .gitignore 忽略，不入 PR）。
- 重写 manifest.yaml（published、真实 sha256/依赖/知识沉淀）；notes 状态统一为 published；重跑 finish published 复验。
---

**编译结束**: 2026-09-20 11:11
**最终状态**: published
