# kweathercore 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM >= 6.3.0，QT_NO_DEFAULT_AUTOGENERATION 无关）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（OHOS SDK，clang 15，profile ohos-aarch64）
- conan: 2.29.1（OHOS 适配版），remote ohpcd
- 状态: published

## 真实依赖（kweathercore-26.04.0/CMakeLists.txt）
- ECM >= 6.3.0（NO_MODULE，build-time，tool_requires ecm/6.26.0）
- Qt6 >= 6.5.0 CONFIG REQUIRED: Core Network Positioning Qml
  → qtbase/6.11.1、qtpositioning/6.11.1、qtdeclarative/6.11.1
- KF6 >= 6.3.0 REQUIRED COMPONENTS: I18n, Holidays
  → ki18n/6.26.0、kholidays/6.28.0

## 编译步骤

1. `conan create archives/k/kweathercore/26.04.0 --build=missing -pr:h ohos-aarch64 -pr:b default`
   - `source()`: conan `get()` 下载 kweathercore-26.04.0.tar.xz（南京 KDE 镜像，download.kde.org 当前网络被拒）
   - `generate()`: CMakeToolchain + 手工 CMAKE_PREFIX_PATH 注入文件（CMAKE_PROJECT_TOP_LEVEL_INCLUDES 双管齐下，kdeclarative 先例）
   - `build()`: cmake.configure + build（LD_LIBRARY_PATH 注入 host 工具依赖）
   - `package()`: cmake.install() + 补 include/kweathercore 小写符号链接

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++20 特性（std::ranges::any_of，capalertinfo.cpp:159）在 OHOS libc++ 下被禁用 | OHOS SDK libc++（clang 15）未定义 _LIBCPP_ENABLE_EXPERIMENTAL 时在 __config 定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES（最小探针实测复现） | CMakeToolchain 在 CMAKE_CXX_FLAGS 追加 -D_LIBCPP_ENABLE_EXPERIMENTAL + tools.build:compiler_cppstd=20 + CMAKE_CXX_STANDARD=20 |
| 2 | 上游 CMakeLists 强制 CMAKE_CXX_STANDARD 20，host profile 默认 cppstd=17 被 ConanToolchain 覆盖回 17 | ConanToolchain 写死 cppstd 变量 | tc.variables["CMAKE_CXX_STANDARD"]/"CMAKE_CXX_STANDARD_REQUIRED" 显式 20 |
| 3 | find_package(Qt6 ... Qml/Positioning) 失败：分包发布的 qtdeclarative/qtpositioning 不在 qtbase 前缀下 | Qt6 组件查找以 qtbase 前缀为根 | QT_ADDITIONAL_PACKAGES_PREFIX_PATH 补入 qtdeclarative/qtpositioning 包前缀（kdeclarative 6.26.0 先例） |
| 4 | ECM_QmlModule 在 include 阶段即要 Qt6::Qml，普通 CMAKE_PREFIX_PATH 注入太晚 | 上游顶层 include( ECMQmlModule ) 早于常规 configure 注入点 | 注入文件经 CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 project() 时加载 |
| 5 | OHOS 不在 KDE 平台列表，ECM 平台检查报错 | ECM 平台白名单 | -DKF_IGNORE_PLATFORM_CHECK=TRUE（ki18n 先例同款） |
| 6 | 公共头内 #include <kweathercore/kweathercore_export.h> 小写裸前缀，ECM 安装布局只有 include/KWeatherCore/KWeatherCore/（驼峰） | 上游 GenerateExportHeader 前缀固定小写，安装布局按 INCLUDE_INSTALL_DIR 驼峰 | package() 补相对符号链接 include/kweathercore -> KWeatherCore/KWeatherCore，头文件原样可解析 |
| 7 | 链接报 ld.lld: unable to find -lKF6KWeatherCore | 上游产出的库名是 libKWeatherCore.so（KDE 库名规则未按 KF6 前缀） | package_info.libs 与 test_package 链接均用 -lKWeatherCore |
| 8 | host 工具（qmltyperegistrar 等）musl 下 dlopen Qt 依赖库失败 | 交叉 SDK 工具链依赖库不在 loader 默认路径 | _cmake_build_env() 前置全部依赖包 lib/bin + SDK llvm lib + /system/lib64 到 LD_LIBRARY_PATH（kdeclarative 先例同款） |
| 9 | ECMConfig.cmake 不传播 ECM_MODULE_PATH | CMakeDeps 对 ECM 模块路径无内置传播 | generate() 手工 set ECM_MODULE_PATH（modules/find-modules/kde-modules 三段） |

## 上游测试（R51 口径）
- 上游 autotests/ 共 8 个 QTest 套件（autotests/CMakeLists.txt 两次 ecm_add_tests 注册：
  capparsertest/metnoparsertest/hourlyweatherforecasttest/dailyweatherforecasttest/
  weatherforecasttest/locationquerytest/pendingweatherforecasttest 共 7 个，
  另有 geotimezonetest 单独注册；均需 Qt6::Test，capparsertest/metnoparsertest 另需
  capdata/、met.no/ 数据目录，geotimezonetest 另需 Qt6::Network）。
- conan 构建 BUILD_TESTING=OFF 跳过；test_package 以消费者视角复刻核心值对象
  LocationQueryResult 的构造/访问器 + 版本宏断言（4 项断言：版本宏 1 + 访问器 3）。
- 明细见 test_package/MANIFEST.yml 与 reports/test-report.md。

- 验证口径：`conan create archives/k/kweathercore/26.04.0 --build=missing -pr:h ohos-aarch64 -pr:b default` 端到端通过，test_package 实机运行 `all 4 checks passed`。
- 未发布到 ohpcd remote（`conan list "kweathercore/*" -r=ohpcd` → 0 matching）；上游适配 PR 合并后由 CI/维护者发布。
---

**编译结束**: 2026-09-27 14:26
**最终状态**: published
