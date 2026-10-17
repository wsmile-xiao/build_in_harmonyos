# ki18n5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (KDE Extra CMake Modules)
- 编译日期: 2026-09-17
- 编译器: clang 15 (aarch64-linux-ohos)
- 状态: published

## 编译步骤

conan create archives/k/ki18n5/5.116.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Could NOT find ECM | conan_cmakedeps_paths.cmake 时序：tc.generate() 前 paths 文件不存在，append 分支被跳过 | 改用 tc.variables["ECM_DIR"]（toolchain 变量，无文件时序问题） |
| 2 | Qt5::Core 引用不存在的 mkspecs 路径 | Qt5CoreConfigExtrasMkspecDir.cmake 硬编码 <pkg>/../b/mkspecs/linux-clang | attica-kf5/5.116.0 验证过的 _prepare_qt_mkspec_compat：把包内 mkspecs 拷到预期位置 |
| 3 | Could NOT find Qt5Qml | conan_toolchain find_paths 块为 if/else：paths 文件存在时 else 分支（generators 目录进 PREFIX_PATH/MODULE_PATH）被跳过，而经典 CMakeDeps 从不写该文件；配方 ECM append 又因文件不存在被静默跳过，qtbase 段以 open("w") 创建了只含 qtbase 条目的文件 | generate() 内以 open("w") 一次性创建 paths 文件，写入 generators 目录 + ECM + qtbase 三组条目；qt5-qtdeclarative 依赖恢复，BUILD_WITH_QML=ON |
| 4 | Could NOT find Gettext (msgmerge) | FindGettext 只探测 PATH，conan 环境不暴露 gettext bin | tc.variables 注入 GETTEXT_MSGFMT_EXECUTABLE / GETTEXT_MSGMERGE_EXECUTABLE |
| 5 | test_package applicationDomain 断言失败 | 未 setApplicationDomain 时空 domain 是文档化默认值 | 改为 setApplicationDomain("test_ki18n5") 后回读断言（实质 API 测试，R34） |
| 6 | Qt5Qml-Target-release.cmake 报 Qt5::Gui 未定义 | Qt5Qml 依赖接口引用 Qt5::Gui/Qt5::Network，而上游只 find_package(Qt5 REQUIRED Core) | conandata 补丁 0001：REQUIRED Core Gui Network |
| 7 | kcountry/kcountrysubdivision 测试需 iso-codes 数据 | 测试均 setTestModeEnabled(true)，XDG 数据目录查找失效，走 $HOME/.qttest/share | build() 测试阶段把 iso-codes JSON 与 locale .mo 部署到 test-home/.qttest/share；iso-codes 经 pkg-config 接线（FindIsoCodes 走 pkg_check_modules 读 .pc 的 prefix/domains） |

## 上游测试三步法 (R51) 实测结果

- 清点：autotests/ BUILD_TESTING=ON + BUILD_WITH_QML=ON 实际注册 **10 项 CTest**
  （9 个 QTest 二进制 + ki18n_install），**无排除项**；函数级口径 39
  （38 个 QTest 函数 + ki18n_install 1 项）。
- 数据部署：iso-codes JSON 与 locale .mo 部署到 test-home/.qttest/share
  （kcountry 断言 "Nouvelle-Zélande" 走 LANG=fr_CH 回退 fr 的 .mo 链路；
  ki18ndeclarativetest 靠源串回退通过，无需部署 .po）。
- 实测：`ctest --test-dir <build> --output-on-failure --no-tests=error`
  - 10/10 Passed：ki18n-declarativetest / ki18n-klocalizedstringtest /
    ki18n-klazylocalizedstringtest / ki18n-ktranscripttest /
    ki18n-ktranscriptcleantest / ki18n_install / kcatalogtest / kcountrytest /
    kcountrysubdivisiontest / ktimezonetest
  - 100% tests passed, 0 tests failed out of 10
- 函数级 Totals（各二进制直接运行抓取）：123 passed, 0 failed,
  1 skipped（klocalizedstringtest 上游 Qt 版本守卫 QSKIP）。
  逐项明细见 reports/test-report.md。
- test_package 冒烟：test_ki18n5 3/3 PASS。

## 依赖版本

- qt5-qtbase/5.15.2.2
- qt5-qtdeclarative/5.15.2（QML 支持，BUILD_WITH_QML=ON）
- gettext/0.22.5.1
- iso-codes/4.20.1（ohpcd 已发布，测试数据部署用）
- ecm/6.26.0 (tool_requires)

## 验证结果

conan create PASS；上游 ctest 10/10 通过（100%，无排除项）；
test_package 3/3 通过；本地 CI（build_and_test.sh）L0-L5 全绿，
Pass rate 100.0% (1/1)。

## 编译结束

**编译结束**: 2026-09-17
**最终状态**: published
