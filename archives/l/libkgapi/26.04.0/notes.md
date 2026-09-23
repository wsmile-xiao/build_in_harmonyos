# libkgapi 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE ECM，KPim6GAPI 自带 Config.cmake）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS aarch64 工具链，ohos-aarch64 profile）
- 状态: built（W3 本地 conan create 通过，exit_code=0，log_sha256=cb437de2…）

## 编译步骤

conan create（模式 B 探索后固化为配方）：
1. `generate()`：CMakeToolchain 注入 `KF_IGNORE_PLATFORM_CHECK=TRUE`（绕过 KDE 平台白名单，OHOS 不在列表）、`BUILD_TESTING=ON`、`BUILD_QCH=OFF`、`BUILD_SASL_PLUGIN=OFF`（cyrus-sasl 插件面本平台不用）、`CMAKE_BUILD_RPATH=$ORIGIN`；
2. qtbase/kwallet/kcalendarcore/kcontacts 均为 `cmake_find_mode=none`（项目自带 Config.cmake），CMakeDeps 不自动注入其 lib/cmake → `_write_cmake_paths()` 生成 `conan_cmakedeps_paths.cmake`，手工拼接 CMAKE_PREFIX_PATH / LIBRARY_PATH / INCLUDE_PATH（沿 kcalendarcore 6.26.0 先例）；
3. `build()`：OHOS 下 `apply_conandata_patches` → CMake.configure/build → `_run_upstream_tests()` 在真机原生执行 ctest。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KF_MIN_VERSION 6.22.0 高于制品仓已发布 KF6 栈（kwallet/kcontacts 6.18.0） | 上游要求 ≥6.22.0，ohpcd 无对应版本 | 补丁 0001 将 KF_MIN_VERSION 降至 6.18.0 |
| 2 | po/qm 翻译文件生成依赖宿主 gettext 工具链 | CI/真机无 msgfmt 完整环境 | 补丁 0002 跳过 poqm 翻译生成（运行时无影响，Qt 回退英文） |
| 3 | ctest 运行期 musl 相对 soname 解析失败（`./libical.so`、`../../bin/libKF6I18n.so` 等 DT_NEEDED 从 CWD 解析） | musl 对含路径 DT_NEEDED 的解析路径与 glibc 不同 | `_prepare_ctest_runtime_links` 将全图依赖库拷入 `<build>/autotests`、`<build>`、`<build>/../bin` 三个解析点 |
| 4 | OHOS 无 /usr/share/zoneinfo，`QTimeZone("Europe/Prague")` 退化 | tzdata 缺失 | 测试环境 `TZDIR` 指向 qtbase 包自带 zoneinfo |
| 5 | calendar 套件 RRULE 序列化断言失败 | libical 4.0.1 `icalrecurrencetype_as_string` 保留输入顺序（round-trip 实测），上游 CI 的 libical 3.x 归一化为 RFC 固定顺序；RFC 5545 规定 RRULE 部件顺序无语义 | 补丁 0003 对齐两个期望 fixture（非测试豁免，语义等价） |

## 源码修改

- patches/0001-lower-kf-min-version-to-6.18.patch：KF_MIN_VERSION 6.22.0 → 6.18.0
- patches/0002-skip-poqm-translation-generation.patch：跳过 poqm 翻译生成
- patches/0003-fix-rrule-part-order-for-libical4.patch：RRULE 期望 fixture 部件顺序对齐 libical 4（RFC 5545 顺序无语义）

## 依赖版本

- qtbase/6.11.1.2（force 对齐全图；传递 kconfig/kwallet 要求 6.11.1，remote 无 binary）
- kwallet/6.18.0、kcalendarcore/6.26.0、kcontacts/6.18.0
- tool_requires: ecm/6.26.0
- （传递）kcoreaddons/kconfig/ki18n 6.18.0.x 栈、libical、cyrus-sasl 等

## 验证结果

- 上游测试：`ctest --output-on-failure --no-tests=error` → **100% tests passed, 0 failed out of 49**（fake:1 / core:4 / calendar:9 / tasks:10 / drive:16 / people:9，全部离线 fake network access manager）
- test_package 冒烟：链接 KPim6::GAPICore/GAPICalendar，`KGAPI2::Calendar` 与 `KGAPI2::Account` API 往返校验 → `PASS: KPim6GAPI API ohpc-smoke ohpc-test-account`
- W3 本地 CI 模拟 PASS；verify-build G1-G4 PASS
- packaging：libkgapi-26.04.0-ohos-aarch64.tar.gz（8 个 .so 已 OHOS ELF 签名）

## 注意事项

- 上游 KAccounts6 后端未启用（kaccounts-integration 未发布）；libkgapi 本体不依赖它，kio-gdrive 适配时可走 Qt6Keychain 后端（qtkeychain/0.14.2 已发布）
- 下游引用必须精确 `libkgapi/26.04.0`（R37）
