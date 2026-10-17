# ktextwidgets 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake (KF6/ECM)
- 编译日期: 2026-08-29
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built

## 编译步骤
1. `conan create archives/k/ktextwidgets/6.14.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. CMakeToolchain 关键变量：`KF_IGNORE_PLATFORM_CHECK=TRUE`、`KF_SKIP_PO_PROCESSING=ON`、
   `WITH_TEXT_TO_SPEECH=OFF`（Qt6 TextToSpeech 未发布）、`BUILD_DESIGNERPLUGIN=OFF`
   （Qt6UiPlugin 未发布）、`BUILD_TESTING=ON`（跑上游 5 个 ctest）
3. `ECM_MODULE_PATH` 手动指向 tool_requires ecm/6.20.0 的 share/ECM/{modules,find-modules,kde-modules}
4. generate() 手写 `conan_cmakedeps_paths.cmake`：把所有依赖包 lib/cmake 前插 CMAKE_PREFIX_PATH，
   保证 KF6TextWidgetsConfig 的 find_dependency 链能解析
5. build() 在 `_library_runtime_env()`（LD_LIBRARY_PATH=各依赖 lib+build bin、QT_PLUGIN_PATH）下 cmake.build
6. ctest（QT_QPA_PLATFORM=offscreen，HOME/XDG_RUNTIME_DIR 隔离）→ 5/5 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 缺 KF6Sonnet | 上游 REQUIRED find_package(KF6Sonnet 6.14.0)，WIP 配方漏声明 | requires sonnet/6.26.0（find_package 版本范围 [6.14.0,7.0) 接受） |
| 2 | feature_summary 报 Qt6UiPlugin 缺失 | Designer 插件默认开 | `BUILD_DESIGNERPLUGIN=OFF`（同已发布 sonnet 配方） |
| 3 | 测试进程 `Error loading shared library ../../bin/libKF6SonnetCore.so` | **已发布 KF6 二进制包的 DT_NEEDED 含构建树相对路径**（`../../bin/*.so`），musl 按 CWD 解析失败 | `_prepare_ctest_runtime_links()`：在 `<build>/../bin` 建全部依赖 .so 软链接农场（kxmlgui 6.18 同款方案） |
| 4 | 测试进程加载 `.cache/conan2` 绝对路径失败 | 依赖包二进制内嵌 CI worker 的 conan home 绝对路径，本机 home 是 `.conan2` | 本机 `ln -s ~/.conan2 ~/.cache/conan2`（仅本地验证环境；CI worker home 与 RPATH 一致，无需处理） |
| 5 | test_package find_package(KF6Sonnet) 失败 | KF6TextWidgetsConfig 会 find_dependency 全部直接 KF6 依赖 | test_package 显式 requires 全部直接依赖 + 遍历注入各依赖 lib/cmake 前缀（kxmlgui 模式） |
| 6 | test.cpp `'KRichTextEditor' file not found` | WIP 测试代码用了**不存在的类名**（从未编译过未暴露）；真实类是 KRichTextEdit/KTextEdit | 重写 test.cpp：className 断言、setPlainText/toPlainText、insertHtml、setReadOnly、checkSpellingEnabled 开关（sonnet 链路线）、KTextEdit append——9 断言全过 |

## 依赖版本
- kcompletion/6.14.0, kconfig/6.14.0, ki18n/6.14.0, kwidgetsaddons/6.14.0（制品仓 6.14.0 线）
- sonnet/6.26.0（满足 KF6Sonnet ≥6.14）
- qtbase/6.11.1, qtbase-gui/6.11.1
- tool_requires: ecm/6.20.0

## 验证结果
```bash
# conan-verify 8 门禁全过（G0-G4 + L2/L4/L5）
# 上游测试：5/5 ctest PASS（kfindtest/kreplacetest/krichtextedittest/ktextedit_unittest/kpluralhandlingspinboxtest）
# test_package：9/9 断言 PASS（offscreen QWidget 实例化 + sonnet 拼写开关往返）
```

## 注意事项
- 本机跑任何 KF6 依赖链测试前，需保证 `~/.cache/conan2 -> ~/.conan2` 软链存在（见问题 #4）
- `parsetrigrams.py`（Desktop/huawei）已修复为与 parsetrigrams6 输出逐字节一致
  （大端 QDataStream、无版本前缀、UTF-16 字节长度、非锚定 `.{3}\s+`、left(3)=3 码元）——
  sonnet 若将来需要交叉构建可用；本机用不到（sonnet/6.26.0 已发布，直接依赖）
---

**编译结束**: 2026-08-29 01:11
**最终状态**: built

## L5 产物基线（遥测记录，非本配方引入）
- checksec/L5 门禁记录 3 个 SONAME 相关问题（依赖包 DT_SONAME 缺失/绝对路径 DT_NEEDED，
  见上表 #3/#4）；CI 的 L5 为存量整改期遥测 gate，不包 FAILED，未绕过。
  与 kxmlgui 6.18 等 23 个已知同源缺陷一致。
