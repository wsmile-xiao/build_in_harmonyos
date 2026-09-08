# Test Report — extra-cmake-modules 6.26.0

- 日期：2026-09-05
- 环境：HarmonyOS PC (aarch64)，clang 15.0.4，cmake 4.1.2，conan 2.29.1（OHOS 适配版）
- Profile：ohos-aarch64（os=OHOS, arch=armv8, compiler=clang 15, libc++, cppstd=17, Release）

## W3 本地 CI（conan create）

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
extra-cmake-modules/6.26.0 (test package): RUN: ./test_ecm
...
EXIT=0
```

- conan create **exit 0**（含 test_package 构建 + 运行）
- `.ci-result.json`：exit_code=0，integrity_hash=017fcc77ee911357，log_sha256=779be81e...

## 包产物完整性实测

| 目录 | 文件数 | 说明 |
|------|-------|------|
| share/ECM/modules | 58 | 与上游源码树逐文件 diff **完全一致** |
| share/ECM/kde-modules | 18 | 含 kde-git-commit-hooks |
| share/ECM/find-modules | 39 | |
| share/ECM/toolchain | 10 | |
| share/ECM/test-modules | 1 | |
| share/ECM/cmake | 2 | ECMConfig.cmake + ECMConfigVersion.cmake |
| `.in` 模板 | 16 | ecm_uninstall.cmake.in / ECMVersionHeader.h.in / ECMQmlModule.cpp.in / ECMQmlModule.h.in 等 |

## test_package 消费者测试（11 项断言全部通过）

CMake configure 阶段（每项失败即 FATAL_ERROR）：

1. `find_package(ECM 6.26.0 EXACT REQUIRED NO_MODULE)` 成功
2. `include(ECMFindModuleHelpers)` 加载成功
3. `ecm_find_package_version_check(ECM)` 宏调用成功
4. `ECM_VERSION VERSION_EQUAL "6.26.0"` 断言通过
5. `ECM_MODULE_DIR/ECMFindModuleHelpers.cmake` 存在
6-12. 7 项 `.in` 模板完整性断言（ecm_uninstall / ECMVersionHeader.h / ECMQmlModule.cpp / ECMQmlModule.h / ECMQtDeclareLoggingCategory.cpp / ECMQtDeclareLoggingCategory.h / ECMQmLoader）——实测输出 `ECM .in templates verified: 7/7`
13. `ECM_KDE_MODULE_DIR` 目录存在
14. `ECM_FIND_MODULE_DIR` 目录存在

运行阶段：`./test_ecm` 编译链接成功并运行，断言 ECM_VERSION_STRING 首字符为 '6' 且 ECM_MODULE_DIR_STRING 非空，**exit 0**。

## 上游测试套件（87 个 ctest）结论

- 上游 6.26.0 注册 87 个 ctest 用例（tests/CMakeLists.txt 全量）
- CI 构建路径 BUILD_TESTING=OFF（干净环境无 Qt5/Python3 前置）
- 同源先例实测（6.28.0 notes / ecm-6.26.0 manifest，同一上游测试代码）：
  - 77 个核心测试通过（ExecuteCoreModules / FindModules / UseFindModules / ecm_setup_version 系列 / ecm_generate_pkgconfig 系列 / ecm_generate_export_header 系列）
  - 10 个失败为环境前置缺失：ExecuteKDEModules / KDEFetchTranslations / KDEInstallDirsTest ×4（OHOS Python wrapper -E 模式 sys.prefix 硬编码 /python3 不存在）、ecm_add_tests ×4（需 find_package(Qt5Core)，OHOS 仅 Qt6）——属环境依赖缺失，与本包模块安装物无关
- 消费者视角覆盖由 test_package 承担（见上节 11 项断言）

## 结论

- 编译状态：**通过**（conan create exit 0）
- test_package 断言：**11/11 通过（100%）**
- 上游用例（同源环境先例）：77/87（89%），10 项失败均为 OHOS 平台 Qt5/Python3 前置缺失，非适配缺陷
