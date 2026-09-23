# syndication 6.26.0 notes（R01）

## Scope

Syndication 是 KDE Frameworks 6 的 RSS/Atom/RDF feed 解析库（Tier 2 functional，
libKF6Syndication.so），暴露格式无关的 `Syndication::ParserCollection` /
`Syndication::parse()` API，覆盖三种格式后端（RSS 2.0 / RDF-RSS 1.0 / Atom），
每种自带 parser 与映射层（将格式特定文档投影到通用 Feed/Item/Person/Image/
Enclosure 接口）。下游消费者（alligator 等 feed 阅读器）直接
`find_package(KF6Syndication)` + `KF6::Syndication`。

本版本为 KF6 第一波（6.26 系）适配，配方以 syndication/6.14.0（已审）为底稿
移植，叠加 knewstuff 6.26.0 / baloo 6.28.0 的 KF6 手法加固。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表内）。
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成（基线包无 lconvert）。
- `BUILD_TESTING=ON` + ctest 上游测试；`QT_QPA_PLATFORM=offscreen` 无头运行。
- `BUILD_QCH=OFF`（Qt Assistant 文档工具链不在基线）。
- 补丁 0001：KF_DEP_VERSION 6.26.0→6.18.0（kcodecs 制品仓封顶 6.18.0；
  ECM 6.26.0 已发布无需降级——与 knewstuff 6.26.0 补丁 0001 同型）。
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname,"` 显式注入：CMake 无
  Platform/HarmonyOS 模块，该 flag 缺省为空 → libKF6Syndication.so 无
  DT_SONAME（kfilemetadata/baloo 先例）。
- C++20 经 `CMAKE_CXX_FLAGS` 强制：KDEFrameworkCompilerSettings 期望 C++20，
  profile cppstd=17，且 KDECompilerSettings 用 variable_watch 覆盖
  CMAKE_CXX_STANDARD（kcoreaddons/kfilemetadata 先例）。
- `ECM_MODULE_PATH`、`conan_cmakedeps_paths.cmake` 手工写入（cmake_find_mode=none
  的 qtbase/kcodecs 不被 CMakeDeps 自动加搜索路径，R49）。
- `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（分号分隔）使 Qt6Xml/Qt6Test/Qt6Network
  模块配置在 qtbase 包内可被发现。
- qtpaths 沙箱守卫：KDEInstallDirs configure 期跑 qtbase qtpaths，沙箱
  LD_LIBRARY_PATH 的 libc++_shared.so 不兼容 → prepend /system/lib64 +
  qtbase/lib（bluez-qt 6.28.0 / kconfig 6.26.0 / baloo 6.28.0 先例）。
- ctest 沙箱：HOME/XDG_RUNTIME_DIR/XDG_*_HOME 重定向到 build_folder 下临时目录。

## Dependencies（对齐制品仓，全部实测存在 2026-09-07）

qtbase/6.11.1、kcodecs/6.18.0、build: ecm/6.26.0。
（kconfig/kcoreaddons/ki18n 6.26.0 已发布但 syndication 仅依赖 KF6Codecs，
不进入本包依赖集。）

## Upstream tests（实测）

上游 tarball 解压后逐目录统计（find autotests tests -name "*.cpp"）：
- autotests/：6 个 .cpp —— testpersonimpl.cpp、syndicationtest.cpp、
  loaderutiltest.cpp（以上 3 个有 add_test 注册）+ testlibsyndication.cpp、
  benchmark.cpp（手动工具，无 add_test）+ fetchFeeds.rb 等脚本不算
- tests/：1 个 .cpp —— testloader.cpp（手动网络工具，无 add_test）

ctest 注册 3 个，全部纳入运行：
- testpersonimpl：personFromString 14 组输入断言（email/name/uri 解析）
- syndicationtest：数据驱动 71 个 feed 文件（atom 28 + rdf 9 + rss2 34），
  逐个 debugInfo 与 .expected 期望文件比对
- loaderutiltest：LoaderUtil::parseFeed 3 组（bug-383381 / test-gentoo-url /
  bug-484615）

未注册 ctest 的 3 个 .cpp 逐条说明（非测试，上游即不注册）：
- testlibsyndication.cpp：命令行 feed 解析打印工具（无断言）
- benchmark.cpp：手动基准工具（读 feed 打印耗时，无断言）
- tests/testloader.cpp：QNetworkAccessManager 在线拉取工具（需真实网络，
  无断言，上游 tests/ 目录本就无 add_test）

## 验证结果

- 本地 conan create（ohos-aarch64 profile）：RC=0
- 上游 ctest 3/3 通过
- test_package 1/1 通过（ParserCollection RSS 2.0 解析 + title/items/
  debugInfo 断言，conanrun 环境执行）

## 注意事项

- 仅库类型包（libKF6Syndication.so），无命令行产物，不需要 commands.json（R38）。
- 补丁仅 OHOS 应用（settings.os == "OHOS" 守卫）。
- 下游 KF6 消费者直接 find_package(KF6Syndication)，包自带
  KF6SyndicationConfig.cmake 且 find_dependency 跟踪 KF6Codecs/Qt6Xml。
---

**编译结束**: 2026-09-07 18:08
**最终状态**: built
