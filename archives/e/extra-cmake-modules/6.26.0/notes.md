# 适配笔记 — extra-cmake-modules 6.26.0

## 任务
- 平台任务：积分赛-依赖 #6319（KF6 链第 2 层最优先）
- 认领人：j669539
- 分支：feat/extra-cmake-modules-6.26.0
- worktree：/storage/Users/currentUser/huawei/wt-ecm（独立 worktree，主仓库只读）

## 一、软件简介

ECM（Extra CMake Modules）是 KDE 提供的扩展 CMake 模块集合，为项目构建系统提供额外的
CMake 宏、工具链文件和 `find_package` 查找模块。纯 CMake 模块包（无编译二进制），
安装 .cmake/.py/.in 脚本到 share/ECM/。

## 二、源码信息（核验）

- 软件名称：extra-cmake-modules
- 适配版本：6.26.0
- 官方来源：https://download.kde.org/stable/frameworks/6.26/extra-cmake-modules-6.26.0.tar.xz
- SHA-256（本轮实际下载计算）：`f4e10d9d45aafb5273e996196040f4e420f0bc4071c208282aae94d9ad8e1743`
  （与已发布别名包 ecm/6.26.0 的 conandata 记录一致——同一上游 tarball）
- 上游 tag：v6.26.0（invent.kde.org/frameworks/extra-cmake-modules）
- 上游 cmake_minimum_required(VERSION 3.29)；本机 /data/service/hnp/bin/cmake 4.1.2 满足
- 许可证：BSD-3-Clause

## 三、依赖与消费者

- 强制依赖：无（纯 CMake 模块包，project LANGUAGES NONE）
- 可选（测试/文档）：Qt5/Qt6、Python3、Sphinx —— 非适配阻塞（BUILD_TESTING=OFF）
- registry 发布状态：extra-cmake-modules 系列已发布 6.19.0/6.28.0/6.29.0；别名系列
  ecm/6.20.0、6.26.0、7.0.7 已发布。本包补齐 extra-cmake-modules 包名系列缺失的 6.26.0。
- 消费者：KF6 链 6.26.0 批次（kitemviews / kcodecs / kconfig / kpackage 等）通过
  find_package(ECM) + tool_requires 消费。

## 四、适配方案（对齐 6.29.0 已验证模式）

1. `package_type = "build-scripts"`（纯 CMake 模块包），`package_id()` 用
   `self.info.clear()` 统一包 ID（无编译产物，da39a3ee... 空哈希包 ID）。
2. `generate()`：`CMAKE_C/CXX_COMPILER_WORKS=1` 跳过编译器检查（LANGUAGES NONE 项目
   在 OHOS 交叉环境下的防御性设置，对齐 6.28.0）；`BUILD_TESTING=OFF` /
   `BUILD_DOCUMENTATION=OFF`（上游测试静态库需 C++ 编译器 + Qt 前置）。
3. `package()` 用 `cmake.install()`：上游 6.26.0 CMakeLists.txt 的 install() 规则完整
   覆盖 share/ECM/{modules,kde-modules,find-modules,toolchain,test-modules,cmake}
   （含全部 16 个 .in 模板与 ECMConfig.cmake/ECMConfigVersion.cmake）。
   实测产物：modules 58（与上游目录逐文件 diff 一致）、kde-modules 18、find-modules 39、
   toolchain 10、test-modules 1、cmake 2、.in 模板 16。
4. `package_info()`：cmake_file_name=ECM / cmake_target_name=ECM::ECM /
   builddirs=share/ECM/cmake，下游 find_package(ECM) 直接可用。
5. test_package：find_package(ECM 6.26.0 EXACT) + include(ECMFindModuleHelpers) +
   ecm_find_package_version_check(ECM) + 版本/模块目录断言 + **7 个 .in 模板完整性断言**
   （6.28.0 曾因 .in 模板缺失导致下游 bluez-qt configure 失败，此断言为防回归加固）+
   编译运行 test_ecm 二进制（R34 实质测试）。

## 五、编译与测试结果

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（OHOS aarch64 clang 15,
  libc++）**exit 0**，test_package `./test_ecm` 运行通过。
- ECM .in templates verified: 7/7；kde-modules/find-modules 目录断言通过。
- 上游 87 个 ctest 测试中核心模块测试（ExecuteCoreModules/FindModules/ecm_setup_version/
  ecm_generate_pkgconfig/ecm_generate_export_header 等约 77 个）在 6.28.0/6.29.0 同源
  环境验证通过（见先例 notes）；约 10 个需 Qt5/Qt6/Python3 前置（ExecuteKDEModules/
  KDEFetchTranslations/KDEInstallDirsTest ×4/ecm_add_tests ×4），属环境依赖缺失，
  与模块安装物无关（参考 ecm/6.26.0 与 6.28.0/6.29.0 同结论）。
- 本包构建路径 BUILD_TESTING=OFF（CI 干净环境无 Qt5），测试覆盖由 test_package
  消费者测试承担（find_package + 宏调用 + 模板完整性 + 运行时断言）。

## 六、本地环境备注（非 CI 问题）

- 本机桌面会话的 LD_LIBRARY_PATH 含畸形条目（`/system/lib64/chipset-pub-sdk: /system/lib64`
  冒号后带空格），会导致 test 二进制运行时 libc++_shared.so 解析失败（exit 127）；
  置空后正常（exit 0）。CI 环境（build_and_test.sh）不受影响，ecm/6.26.0、
  extra-cmake-modules/6.29.0 同模式 test_package 已过 CI 验证。
- 首次 conan create 曾出现产物截断（modules 44、.in 0），删除缓存重建后产物完整
  （58/16，与上游逐文件 diff 一致）且可复现；判断为 HMDFS 环境偶发。
  test_package 的 7 项 .in 模板断言即为防此类问题流入下游的硬闸。

## 七、路径 B 自查

- ECM 本身为纯 CMake 模块包，适配方案完全复用仓库内已验证模式（6.28.0/6.29.0/
  ecm/6.26.0），无新错误模式、无平台差异诊断、无构建系统组合创新——**B 素材判定：
  不够格**（正常结论）。
- 链级素材（KF6 6.26.0 批次的 ECM 消费模式：tool_requires + cmake_file_name=ECM +
  builddirs 注入）由链任务统一评估，本包作为链起点数据点已在本 notes 留档。
---

**编译结束**: 2026-09-05 21:47
**最终状态**: built
